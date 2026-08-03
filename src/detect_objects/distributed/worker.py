"""Pull-based model worker for the ODIA inference cluster."""

from __future__ import annotations

import argparse
import os
import platform
import socket
import sys
import threading
import time
from typing import Any

from .client import ClusterClient, ClusterConnectionError, ClusterHTTPError
from .model_handlers import BUILTIN_CAPABILITIES, ModelHandler, create_model_handler


class ClusterWorker:
    """Own loaded model handlers and execute matching coordinator jobs."""

    def __init__(
        self,
        *,
        coordinator: str,
        token: str | None,
        name: str,
        handlers: dict[str, ModelHandler],
    ) -> None:
        if not handlers:
            raise ValueError("a worker needs at least one model handler")
        self.client = ClusterClient(coordinator, token=token)
        self.name = name
        self.handlers = handlers
        self.stop_event = threading.Event()
        self._registration_lock = threading.Lock()
        self._worker_id: str | None = None
        self._heartbeat_interval = 5.0
        self._active_job_ids: set[str] = set()
        self._active_lock = threading.Lock()

    def run(self) -> None:
        """Register once models are loaded, then run one slot per model."""
        self._ensure_registered()
        threads = [
            threading.Thread(
                target=self._claim_loop,
                args=(capability, handler),
                name=f"ModelSlot-{capability}",
                daemon=True,
            )
            for capability, handler in self.handlers.items()
        ]
        threads.append(
            threading.Thread(
                target=self._heartbeat_loop,
                name="CoordinatorHeartbeat",
                daemon=True,
            )
        )
        for thread in threads:
            thread.start()

        try:
            while all(thread.is_alive() for thread in threads):
                time.sleep(0.5)
        except KeyboardInterrupt:
            pass
        finally:
            self.stop_event.set()
            self._unregister()
            for thread in threads:
                thread.join(timeout=2)

    def _claim_loop(self, capability: str, handler: ModelHandler) -> None:
        while not self.stop_event.is_set():
            try:
                worker_id = self._ensure_registered()
                job = self.client.request(
                    "POST",
                    f"/v1/workers/{worker_id}/claim?wait=10",
                    {"capability": capability},
                )
                if job is None:
                    continue
            except ClusterHTTPError as error:
                if error.status == 404:
                    self._forget_registration()
                self.stop_event.wait(1)
                continue
            except ClusterConnectionError:
                self.stop_event.wait(2)
                continue

            job_id = job["id"]
            with self._active_lock:
                self._active_job_ids.add(job_id)
            try:
                result = handler(job["payload"])
                completion = {
                    "worker_id": worker_id,
                    "succeeded": True,
                    "result": result,
                }
            except Exception as error:
                completion = {
                    "worker_id": worker_id,
                    "succeeded": False,
                    "error": f"{type(error).__name__}: {error}",
                    "retryable": False,
                }

            try:
                self.client.request(
                    "POST",
                    f"/v1/jobs/{job_id}/complete",
                    completion,
                )
            except ClusterHTTPError as error:
                if error.status == 404:
                    self._forget_registration()
            except ClusterConnectionError:
                # The lease will expire and another worker can safely retry it.
                pass
            finally:
                with self._active_lock:
                    self._active_job_ids.discard(job_id)

    def _heartbeat_loop(self) -> None:
        while not self.stop_event.wait(self._heartbeat_interval):
            worker_id = self._current_worker_id()
            if worker_id is None:
                continue
            with self._active_lock:
                active_job_ids = sorted(self._active_job_ids)
            try:
                self.client.request(
                    "POST",
                    f"/v1/workers/{worker_id}/heartbeat",
                    {"active_job_ids": active_job_ids},
                )
            except ClusterHTTPError as error:
                if error.status == 404:
                    self._forget_registration()
            except ClusterConnectionError:
                pass

    def _ensure_registered(self) -> str:
        with self._registration_lock:
            if self._worker_id is not None:
                return self._worker_id
            while not self.stop_event.is_set():
                try:
                    response = self.client.request(
                        "POST",
                        "/v1/workers/register",
                        {
                            "name": self.name,
                            "platform": platform.platform(),
                            "capabilities": {
                                capability: 1 for capability in self.handlers
                            },
                            "metadata": {
                                "hostname": socket.gethostname(),
                                "machine": platform.machine(),
                                "python": platform.python_version(),
                            },
                        },
                    )
                except (ClusterConnectionError, ClusterHTTPError) as error:
                    print(f"Coordinator registration failed: {error}", file=sys.stderr)
                    self.stop_event.wait(2)
                    continue
                self._worker_id = response["worker_id"]
                self._heartbeat_interval = float(
                    response["heartbeat_interval_seconds"]
                )
                capabilities = ", ".join(self.handlers)
                print(
                    f"Worker {self.name} registered as {self._worker_id} "
                    f"with {capabilities}"
                )
                return self._worker_id
        raise RuntimeError("worker stopped before it could register")

    def _forget_registration(self) -> None:
        with self._registration_lock:
            self._worker_id = None

    def _current_worker_id(self) -> str | None:
        with self._registration_lock:
            return self._worker_id

    def _unregister(self) -> None:
        worker_id = self._current_worker_id()
        if worker_id is None:
            return
        try:
            self.client.request(
                "POST",
                f"/v1/workers/{worker_id}/unregister",
                {},
            )
        except (ClusterConnectionError, ClusterHTTPError):
            pass


def main(argv: list[str] | None = None) -> int:
    """Load selected models and expose them as worker capabilities."""
    parser = argparse.ArgumentParser(
        description="Load one or more models and join an ODIA coordinator."
    )
    parser.add_argument("--coordinator", required=True)
    parser.add_argument("--token", default=os.environ.get("ODIA_CLUSTER_TOKEN"))
    parser.add_argument("--name", default=socket.gethostname())
    parser.add_argument(
        "--model",
        action="append",
        required=True,
        choices=BUILTIN_CAPABILITIES,
        help="Repeat to load multiple models; usually assign one heavy model per machine.",
    )
    args = parser.parse_args(argv)

    capabilities = tuple(dict.fromkeys(args.model))
    handlers: dict[str, ModelHandler] = {}
    try:
        for capability in capabilities:
            print(f"Loading {capability} before worker registration...")
            handlers[capability] = create_model_handler(capability)
        worker = ClusterWorker(
            coordinator=args.coordinator,
            token=args.token,
            name=args.name,
            handlers=handlers,
        )
        worker.run()
    finally:
        for handler in handlers.values():
            try:
                handler.close()
            except Exception as error:
                print(f"Handler cleanup failed: {error}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
