"""HTTP coordinator that schedules inference across macOS and Windows workers."""

from __future__ import annotations

import argparse
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from typing import Any
from urllib.parse import parse_qs, urlparse

from .scheduler import (
    JobOwnershipError,
    Scheduler,
    SchedulerError,
    UnknownJobError,
    UnknownWorkerError,
)

DEFAULT_PORT = 8765
DEFAULT_MAX_BODY_BYTES = 32 * 1024 * 1024


class CoordinatorServer(ThreadingHTTPServer):
    """HTTP server carrying coordinator state and authentication settings."""

    daemon_threads = True
    allow_reuse_address = True

    def __init__(
        self,
        address: tuple[str, int],
        *,
        scheduler: Scheduler | None = None,
        token: str | None,
        max_body_bytes: int = DEFAULT_MAX_BODY_BYTES,
    ) -> None:
        if token is not None and not token:
            raise ValueError("token cannot be empty")
        if max_body_bytes <= 0:
            raise ValueError("max_body_bytes must be positive")
        self.scheduler = scheduler or Scheduler()
        self.token = token
        self.max_body_bytes = max_body_bytes
        super().__init__(address, CoordinatorRequestHandler)


class CoordinatorRequestHandler(BaseHTTPRequestHandler):
    """Expose the scheduler through a small versioned JSON interface."""

    server: CoordinatorServer
    server_version = "ODIACoordinator/1"

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/health":
            self._send_json(200, {"status": "ok"})
            return
        if not self._authenticated():
            return

        if path == "/v1/workers":
            self._send_json(200, {"workers": self.server.scheduler.list_workers()})
            return
        if path.startswith("/v1/jobs/"):
            job_id = path.removeprefix("/v1/jobs/")
            if not job_id or "/" in job_id:
                self._send_error_json(404, "endpoint not found")
                return
            try:
                job = self.server.scheduler.get_job(job_id)
            except UnknownJobError as error:
                self._send_error_json(404, str(error))
                return
            self._send_json(200, job.as_dict())
            return

        self._send_error_json(404, "endpoint not found")

    def do_POST(self) -> None:
        if not self._authenticated():
            return
        path = urlparse(self.path).path
        try:
            body = self._read_json_object()
            if path == "/v1/workers/register":
                self._register_worker(body)
            elif path == "/v1/jobs":
                self._submit_job(body)
            elif path.startswith("/v1/workers/"):
                self._worker_action(path, body)
            elif path.startswith("/v1/jobs/") and path.endswith("/complete"):
                self._complete_job(path, body)
            else:
                self._send_error_json(404, "endpoint not found")
        except ValueError as error:
            self._send_error_json(400, str(error))
        except UnknownWorkerError as error:
            self._send_error_json(404, str(error))
        except UnknownJobError as error:
            self._send_error_json(404, str(error))
        except JobOwnershipError as error:
            self._send_error_json(409, str(error))
        except SchedulerError as error:
            self._send_error_json(409, str(error))

    def _register_worker(self, body: dict[str, Any]) -> None:
        worker = self.server.scheduler.register_worker(
            name=self._required_string(body, "name"),
            platform=self._required_string(body, "platform"),
            capabilities=body.get("capabilities"),
            metadata=self._optional_object(body, "metadata"),
        )
        self._send_json(
            201,
            {
                "worker_id": worker.id,
                "heartbeat_interval_seconds": min(
                    10.0,
                    self.server.scheduler.worker_ttl_seconds / 3,
                ),
            },
        )

    def _worker_action(self, path: str, body: dict[str, Any]) -> None:
        parts = path.strip("/").split("/")
        if len(parts) != 4 or parts[:2] != ["v1", "workers"]:
            self._send_error_json(404, "endpoint not found")
            return
        worker_id, action = parts[2], parts[3]

        if action == "heartbeat":
            active_job_ids = body.get("active_job_ids", [])
            if not isinstance(active_job_ids, list) or not all(
                isinstance(item, str) for item in active_job_ids
            ):
                raise ValueError("active_job_ids must be a list of strings")
            self.server.scheduler.heartbeat(worker_id, active_job_ids)
            self._send_empty(204)
            return

        if action == "claim":
            capability = self._required_string(body, "capability")
            parsed_query = parse_qs(urlparse(self.path).query)
            try:
                wait_seconds = float(parsed_query.get("wait", ["0"])[0])
            except ValueError as error:
                raise ValueError("wait must be a number") from error
            job = self.server.scheduler.claim(
                worker_id,
                capability,
                wait_seconds=wait_seconds,
            )
            if job is None:
                self._send_empty(204)
            else:
                self._send_json(200, job.as_dict(include_payload=True))
            return

        if action == "unregister":
            self.server.scheduler.unregister_worker(worker_id)
            self._send_empty(204)
            return

        self._send_error_json(404, "endpoint not found")

    def _submit_job(self, body: dict[str, Any]) -> None:
        job = self.server.scheduler.submit(
            capability=self._required_string(body, "capability"),
            payload=self._required_object(body, "payload"),
            max_attempts=body.get("max_attempts", 3),
        )
        self._send_json(202, job.as_dict())

    def _complete_job(self, path: str, body: dict[str, Any]) -> None:
        parts = path.strip("/").split("/")
        if len(parts) != 4 or parts[:2] != ["v1", "jobs"]:
            self._send_error_json(404, "endpoint not found")
            return
        job = self.server.scheduler.complete(
            job_id=parts[2],
            worker_id=self._required_string(body, "worker_id"),
            succeeded=self._required_bool(body, "succeeded"),
            result=body.get("result"),
            error=body.get("error"),
            retryable=body.get("retryable", False),
        )
        self._send_json(200, job.as_dict())

    def _authenticated(self) -> bool:
        expected = self.server.token
        if expected is None:
            return True
        authorization = self.headers.get("Authorization", "")
        prefix = "Bearer "
        supplied = authorization[len(prefix) :] if authorization.startswith(prefix) else ""
        if hmac.compare_digest(supplied, expected):
            return True
        self._send_error_json(401, "missing or invalid bearer token")
        return False

    def _read_json_object(self) -> dict[str, Any]:
        content_type = self.headers.get("Content-Type", "")
        if "application/json" not in content_type.lower():
            raise ValueError("Content-Type must be application/json")
        try:
            content_length = int(self.headers.get("Content-Length", "0"))
        except ValueError as error:
            raise ValueError("invalid Content-Length") from error
        if content_length <= 0:
            raise ValueError("request body cannot be empty")
        if content_length > self.server.max_body_bytes:
            raise ValueError("request body is too large")
        try:
            value = json.loads(self.rfile.read(content_length))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError("request body must be valid JSON") from error
        if not isinstance(value, dict):
            raise ValueError("request body must be a JSON object")
        return value

    @staticmethod
    def _required_string(body: dict[str, Any], key: str) -> str:
        value = body.get(key)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{key} must be a non-empty string")
        return value

    @staticmethod
    def _required_object(body: dict[str, Any], key: str) -> dict[str, Any]:
        value = body.get(key)
        if not isinstance(value, dict):
            raise ValueError(f"{key} must be a JSON object")
        return value

    @classmethod
    def _optional_object(cls, body: dict[str, Any], key: str) -> dict[str, Any]:
        value = body.get(key, {})
        if not isinstance(value, dict):
            raise ValueError(f"{key} must be a JSON object")
        return value

    @staticmethod
    def _required_bool(body: dict[str, Any], key: str) -> bool:
        value = body.get(key)
        if not isinstance(value, bool):
            raise ValueError(f"{key} must be a boolean")
        return value

    def _send_json(self, status: int, value: Any) -> None:
        encoded = json.dumps(value, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def _send_error_json(self, status: int, message: str) -> None:
        self._send_json(status, {"error": message})

    def _send_empty(self, status: int) -> None:
        self.send_response(status)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def log_message(self, format: str, *args: Any) -> None:
        return


def main(argv: list[str] | None = None) -> int:
    """Start the coordinator on one stable machine."""
    parser = argparse.ArgumentParser(
        description="Route ODIA inference jobs to registered model workers."
    )
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument(
        "--token",
        default=os.environ.get("ODIA_CLUSTER_TOKEN"),
        help="Shared token; defaults to ODIA_CLUSTER_TOKEN.",
    )
    parser.add_argument(
        "--insecure",
        action="store_true",
        help="Allow unauthenticated LAN requests (development only).",
    )
    parser.add_argument("--lease-seconds", type=float, default=300.0)
    parser.add_argument("--worker-ttl-seconds", type=float, default=30.0)
    parser.add_argument("--max-body-mb", type=int, default=32)
    args = parser.parse_args(argv)

    if not args.token and not args.insecure:
        parser.error("set ODIA_CLUSTER_TOKEN/--token or explicitly use --insecure")
    if args.token and args.insecure:
        parser.error("--token and --insecure cannot be used together")

    scheduler = Scheduler(
        lease_seconds=args.lease_seconds,
        worker_ttl_seconds=args.worker_ttl_seconds,
    )
    with CoordinatorServer(
        (args.host, args.port),
        scheduler=scheduler,
        token=args.token,
        max_body_bytes=args.max_body_mb * 1024 * 1024,
    ) as server:
        host, port = server.server_address[:2]
        auth_mode = "token" if args.token else "INSECURE"
        print(f"ODIA coordinator listening on http://{host}:{port} ({auth_mode})")
        try:
            server.serve_forever(poll_interval=0.2)
        except KeyboardInterrupt:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
