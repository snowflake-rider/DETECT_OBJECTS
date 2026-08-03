"""Thread-safe in-memory scheduler for ODIA inference workers."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
import threading
import time
import uuid
from typing import Any, Literal

JobStatus = Literal["queued", "leased", "succeeded", "failed"]
JsonObject = dict[str, Any]


class SchedulerError(RuntimeError):
    """Base class for coordinator state errors."""


class UnknownWorkerError(SchedulerError):
    """Raised when a worker ID is no longer registered."""


class UnknownJobError(SchedulerError):
    """Raised when a job ID does not exist."""


class JobOwnershipError(SchedulerError):
    """Raised when a worker tries to finish another worker's job."""


@dataclass
class WorkerRecord:
    """One registered machine and the model slots it exposes."""

    id: str
    name: str
    platform: str
    capabilities: dict[str, int]
    metadata: JsonObject
    registered_at: float
    last_seen_at: float
    active_job_ids: set[str] = field(default_factory=set)

    def as_dict(self, now: float) -> JsonObject:
        return {
            "id": self.id,
            "name": self.name,
            "platform": self.platform,
            "capabilities": dict(self.capabilities),
            "metadata": dict(self.metadata),
            "active_jobs": len(self.active_job_ids),
            "last_seen_seconds_ago": max(0.0, now - self.last_seen_at),
        }


@dataclass
class JobRecord:
    """One inference request as it moves through the cluster."""

    id: str
    capability: str
    payload: JsonObject
    max_attempts: int
    status: JobStatus
    created_at: float
    updated_at: float
    attempts: int = 0
    worker_id: str | None = None
    lease_expires_at: float | None = None
    result: Any = None
    error: str | None = None

    def as_dict(self, *, include_payload: bool = False) -> JsonObject:
        value: JsonObject = {
            "id": self.id,
            "capability": self.capability,
            "status": self.status,
            "attempts": self.attempts,
            "max_attempts": self.max_attempts,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "worker_id": self.worker_id,
            "result": self.result,
            "error": self.error,
        }
        if include_payload:
            value["payload"] = self.payload
        return value


class Scheduler:
    """Route jobs to matching worker slots and recover expired leases."""

    def __init__(
        self,
        *,
        lease_seconds: float = 300.0,
        worker_ttl_seconds: float = 30.0,
        clock: Callable[[], float] = time.time,
    ) -> None:
        if lease_seconds <= 0:
            raise ValueError("lease_seconds must be positive")
        if worker_ttl_seconds <= 0:
            raise ValueError("worker_ttl_seconds must be positive")

        self.lease_seconds = lease_seconds
        self.worker_ttl_seconds = worker_ttl_seconds
        self._clock = clock
        self._workers: dict[str, WorkerRecord] = {}
        self._jobs: dict[str, JobRecord] = {}
        self._queued_job_ids: list[str] = []
        self._condition = threading.Condition(threading.RLock())

    def register_worker(
        self,
        *,
        name: str,
        platform: str,
        capabilities: Mapping[str, int],
        metadata: Mapping[str, Any] | None = None,
    ) -> WorkerRecord:
        normalized_name = name.strip()
        if not normalized_name:
            raise ValueError("worker name cannot be empty")
        normalized_capabilities = self._validate_capabilities(capabilities)
        now = self._clock()
        worker = WorkerRecord(
            id=uuid.uuid4().hex,
            name=normalized_name,
            platform=platform.strip() or "unknown",
            capabilities=normalized_capabilities,
            metadata=dict(metadata or {}),
            registered_at=now,
            last_seen_at=now,
        )
        with self._condition:
            self._workers[worker.id] = worker
            self._condition.notify_all()
        return worker

    def heartbeat(self, worker_id: str, active_job_ids: list[str]) -> None:
        """Mark a worker alive and renew leases it is still processing."""
        now = self._clock()
        with self._condition:
            self._reap_expired_locked(now)
            worker = self._require_worker_locked(worker_id)
            worker.last_seen_at = now
            reported = set(active_job_ids)
            for job_id in reported:
                job = self._jobs.get(job_id)
                if (
                    job is not None
                    and job.status == "leased"
                    and job.worker_id == worker_id
                ):
                    job.lease_expires_at = now + self.lease_seconds
            worker.active_job_ids.intersection_update(reported)

    def unregister_worker(self, worker_id: str) -> None:
        """Remove a worker and immediately return its leased work to the queue."""
        with self._condition:
            worker = self._workers.pop(worker_id, None)
            if worker is None:
                return
            now = self._clock()
            for job_id in tuple(worker.active_job_ids):
                job = self._jobs.get(job_id)
                if job is not None and job.status == "leased":
                    self._retry_or_fail_locked(job, now, "worker unregistered")
            self._condition.notify_all()

    def submit(
        self,
        *,
        capability: str,
        payload: Mapping[str, Any],
        max_attempts: int = 3,
    ) -> JobRecord:
        normalized_capability = capability.strip()
        if not normalized_capability:
            raise ValueError("capability cannot be empty")
        if not isinstance(payload, Mapping):
            raise ValueError("payload must be a JSON object")
        if isinstance(max_attempts, bool) or not 1 <= max_attempts <= 20:
            raise ValueError("max_attempts must be between 1 and 20")

        now = self._clock()
        job = JobRecord(
            id=uuid.uuid4().hex,
            capability=normalized_capability,
            payload=dict(payload),
            max_attempts=max_attempts,
            status="queued",
            created_at=now,
            updated_at=now,
        )
        with self._condition:
            self._jobs[job.id] = job
            self._queued_job_ids.append(job.id)
            self._condition.notify_all()
        return job

    def claim(
        self,
        worker_id: str,
        capability: str,
        *,
        wait_seconds: float = 0.0,
    ) -> JobRecord | None:
        """Lease the oldest matching job to one worker capability slot."""
        if wait_seconds < 0 or wait_seconds > 30:
            raise ValueError("wait_seconds must be between 0 and 30")
        deadline = time.monotonic() + wait_seconds

        with self._condition:
            while True:
                now = self._clock()
                self._reap_expired_locked(now)
                worker = self._require_worker_locked(worker_id)
                worker.last_seen_at = now
                capacity = worker.capabilities.get(capability)
                if capacity is None:
                    raise ValueError(
                        f"worker does not advertise capability: {capability}"
                    )
                active_for_capability = sum(
                    self._jobs[job_id].capability == capability
                    for job_id in worker.active_job_ids
                    if job_id in self._jobs
                )
                if active_for_capability < capacity:
                    job = self._pop_queued_locked(capability)
                    if job is not None:
                        job.status = "leased"
                        job.worker_id = worker_id
                        job.attempts += 1
                        job.updated_at = now
                        job.lease_expires_at = now + self.lease_seconds
                        worker.active_job_ids.add(job.id)
                        return job

                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return None
                self._condition.wait(timeout=min(remaining, 1.0))

    def complete(
        self,
        *,
        job_id: str,
        worker_id: str,
        succeeded: bool,
        result: Any = None,
        error: str | None = None,
        retryable: bool = False,
    ) -> JobRecord:
        now = self._clock()
        with self._condition:
            job = self._require_job_locked(job_id)
            if job.status != "leased" or job.worker_id != worker_id:
                raise JobOwnershipError("job is not leased by this worker")

            worker = self._workers.get(worker_id)
            if worker is not None:
                worker.active_job_ids.discard(job_id)

            if succeeded:
                job.status = "succeeded"
                job.result = result
                job.error = None
                job.worker_id = worker_id
                job.lease_expires_at = None
                job.updated_at = now
            elif retryable:
                self._retry_or_fail_locked(job, now, error or "worker failed")
            else:
                job.status = "failed"
                job.error = error or "worker failed"
                job.result = None
                job.lease_expires_at = None
                job.updated_at = now

            self._condition.notify_all()
            return job

    def get_job(self, job_id: str) -> JobRecord:
        with self._condition:
            self._reap_expired_locked(self._clock())
            return self._require_job_locked(job_id)

    def list_workers(self) -> list[JsonObject]:
        with self._condition:
            now = self._clock()
            self._reap_expired_locked(now)
            return [
                worker.as_dict(now)
                for worker in sorted(self._workers.values(), key=lambda item: item.name)
            ]

    def _pop_queued_locked(self, capability: str) -> JobRecord | None:
        for index, job_id in enumerate(self._queued_job_ids):
            job = self._jobs[job_id]
            if job.status == "queued" and job.capability == capability:
                self._queued_job_ids.pop(index)
                return job
        return None

    def _reap_expired_locked(self, now: float) -> None:
        expired_worker_ids = [
            worker_id
            for worker_id, worker in self._workers.items()
            if now - worker.last_seen_at > self.worker_ttl_seconds
        ]
        for worker_id in expired_worker_ids:
            worker = self._workers.pop(worker_id)
            for job_id in tuple(worker.active_job_ids):
                job = self._jobs.get(job_id)
                if job is not None and job.status == "leased":
                    self._retry_or_fail_locked(job, now, "worker heartbeat expired")

        for job in self._jobs.values():
            if (
                job.status == "leased"
                and job.lease_expires_at is not None
                and job.lease_expires_at <= now
            ):
                worker = self._workers.get(job.worker_id or "")
                if worker is not None:
                    worker.active_job_ids.discard(job.id)
                self._retry_or_fail_locked(job, now, "job lease expired")

    def _retry_or_fail_locked(self, job: JobRecord, now: float, error: str) -> None:
        job.result = None
        job.worker_id = None
        job.lease_expires_at = None
        job.updated_at = now
        if job.attempts < job.max_attempts:
            job.status = "queued"
            job.error = None
            if job.id not in self._queued_job_ids:
                self._queued_job_ids.append(job.id)
        else:
            job.status = "failed"
            job.error = error

    def _require_worker_locked(self, worker_id: str) -> WorkerRecord:
        try:
            return self._workers[worker_id]
        except KeyError as error:
            raise UnknownWorkerError(f"unknown worker: {worker_id}") from error

    def _require_job_locked(self, job_id: str) -> JobRecord:
        try:
            return self._jobs[job_id]
        except KeyError as error:
            raise UnknownJobError(f"unknown job: {job_id}") from error

    @staticmethod
    def _validate_capabilities(capabilities: Mapping[str, int]) -> dict[str, int]:
        if not isinstance(capabilities, Mapping) or not capabilities:
            raise ValueError("capabilities must be a non-empty JSON object")
        normalized: dict[str, int] = {}
        for capability, capacity in capabilities.items():
            name = capability.strip() if isinstance(capability, str) else ""
            if not name:
                raise ValueError("capability names cannot be empty")
            if isinstance(capacity, bool) or not isinstance(capacity, int):
                raise ValueError("capability capacity must be an integer")
            if not 1 <= capacity <= 32:
                raise ValueError("capability capacity must be between 1 and 32")
            normalized[name] = capacity
        return normalized
