"""Client interface for submitting work to the ODIA model cluster."""

from __future__ import annotations

import argparse
import json
import os
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class ClusterConnectionError(RuntimeError):
    """Raised when the coordinator cannot be reached."""


class ClusterHTTPError(RuntimeError):
    """Raised when the coordinator rejects a request."""

    def __init__(self, status: int, message: str) -> None:
        self.status = status
        super().__init__(message)


class ClusterClient:
    """Submit jobs and retrieve their eventual results."""

    def __init__(
        self,
        coordinator: str,
        *,
        token: str | None,
        timeout_seconds: float = 35.0,
    ) -> None:
        if not coordinator.strip():
            raise ValueError("coordinator address cannot be empty")
        self.coordinator = coordinator.rstrip("/")
        self.token = token
        self.timeout_seconds = timeout_seconds

    def submit(
        self,
        capability: str,
        payload: dict[str, Any],
        *,
        max_attempts: int = 3,
    ) -> str:
        response = self.request(
            "POST",
            "/v1/jobs",
            {
                "capability": capability,
                "payload": payload,
                "max_attempts": max_attempts,
            },
        )
        return response["id"]

    def get_job(self, job_id: str) -> dict[str, Any]:
        return self.request("GET", f"/v1/jobs/{job_id}")

    def wait(
        self,
        job_id: str,
        *,
        timeout_seconds: float = 300.0,
        poll_seconds: float = 0.2,
    ) -> dict[str, Any]:
        """Wait for a terminal result while keeping submission asynchronous."""
        deadline = time.monotonic() + timeout_seconds
        while True:
            job = self.get_job(job_id)
            if job["status"] in {"succeeded", "failed"}:
                return job
            if time.monotonic() >= deadline:
                raise TimeoutError(f"job did not finish within {timeout_seconds}s")
            time.sleep(poll_seconds)

    def list_workers(self) -> list[dict[str, Any]]:
        response = self.request("GET", "/v1/workers")
        return response["workers"]

    def request(
        self,
        method: str,
        path: str,
        body: dict[str, Any] | None = None,
    ) -> Any:
        encoded = None
        headers = {"Accept": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        if body is not None:
            encoded = json.dumps(body, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json"

        request = Request(
            f"{self.coordinator}{path}",
            data=encoded,
            headers=headers,
            method=method,
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                response_body = response.read()
        except HTTPError as error:
            response_body = error.read()
            message = self._error_message(response_body, error.reason)
            status = error.code
            error.close()
            raise ClusterHTTPError(status, message) from None
        except (URLError, TimeoutError, OSError) as error:
            raise ClusterConnectionError(
                f"unable to reach coordinator at {self.coordinator}: {error}"
            ) from error

        if not response_body:
            return None
        return json.loads(response_body)

    @staticmethod
    def _error_message(response_body: bytes, fallback: str) -> str:
        try:
            value = json.loads(response_body)
        except (UnicodeDecodeError, json.JSONDecodeError):
            return str(fallback)
        if isinstance(value, dict) and isinstance(value.get("error"), str):
            return value["error"]
        return str(fallback)


def main(argv: list[str] | None = None) -> int:
    """Submit, inspect, and wait for jobs from a terminal."""
    parser = argparse.ArgumentParser(description="Use the ODIA model cluster.")
    parser.add_argument("--coordinator", required=True)
    parser.add_argument("--token", default=os.environ.get("ODIA_CLUSTER_TOKEN"))
    subparsers = parser.add_subparsers(dest="command", required=True)

    submit_parser = subparsers.add_parser("submit")
    submit_parser.add_argument("--capability", required=True)
    submit_parser.add_argument("--payload", default="{}")
    submit_parser.add_argument("--wait", action="store_true")
    submit_parser.add_argument("--timeout", type=float, default=300.0)

    status_parser = subparsers.add_parser("status")
    status_parser.add_argument("job_id")

    wait_parser = subparsers.add_parser("wait")
    wait_parser.add_argument("job_id")
    wait_parser.add_argument("--timeout", type=float, default=300.0)

    subparsers.add_parser("workers")
    args = parser.parse_args(argv)
    client = ClusterClient(args.coordinator, token=args.token)

    try:
        if args.command == "submit":
            payload = json.loads(args.payload)
            if not isinstance(payload, dict):
                parser.error("--payload must be a JSON object")
            job_id = client.submit(args.capability, payload)
            result = (
                client.wait(job_id, timeout_seconds=args.timeout)
                if args.wait
                else {"id": job_id, "status": "queued"}
            )
        elif args.command == "status":
            result = client.get_job(args.job_id)
        elif args.command == "wait":
            result = client.wait(args.job_id, timeout_seconds=args.timeout)
        else:
            result = {"workers": client.list_workers()}
    except (ClusterConnectionError, ClusterHTTPError, TimeoutError) as error:
        parser.exit(1, f"error: {error}\n")

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
