"""Tests for worker matching and failed-worker recovery."""

import unittest

from detect_objects.distributed.scheduler import (
    JobOwnershipError,
    Scheduler,
)


class FakeClock:
    def __init__(self) -> None:
        self.now = 100.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


class SchedulerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.clock = FakeClock()
        self.scheduler = Scheduler(
            lease_seconds=10,
            worker_ttl_seconds=30,
            clock=self.clock,
        )

    def register(self, name: str, *capabilities: str):
        return self.scheduler.register_worker(
            name=name,
            platform="test",
            capabilities={capability: 1 for capability in capabilities},
        )

    def test_routes_only_to_matching_model_capability(self) -> None:
        vision_worker = self.register("vision", "vision:yolo")
        voice_worker = self.register("voice", "voice:whisper")
        job = self.scheduler.submit(
            capability="voice:whisper",
            payload={"audio": "bytes"},
        )

        self.assertIsNone(
            self.scheduler.claim(vision_worker.id, "vision:yolo")
        )
        claimed = self.scheduler.claim(voice_worker.id, "voice:whisper")

        self.assertEqual(claimed.id, job.id)
        self.assertEqual(claimed.worker_id, voice_worker.id)

    def test_enforces_each_advertised_model_slot_capacity(self) -> None:
        worker = self.register("vision", "vision:yolo")
        first = self.scheduler.submit(capability="vision:yolo", payload={})
        second = self.scheduler.submit(capability="vision:yolo", payload={})

        claimed = self.scheduler.claim(worker.id, "vision:yolo")

        self.assertEqual(claimed.id, first.id)
        self.assertIsNone(self.scheduler.claim(worker.id, "vision:yolo"))
        self.scheduler.complete(
            job_id=first.id,
            worker_id=worker.id,
            succeeded=True,
            result={"detections": []},
        )
        self.assertEqual(
            self.scheduler.claim(worker.id, "vision:yolo").id,
            second.id,
        )

    def test_requeues_work_after_lease_expires(self) -> None:
        first_worker = self.register("mac-1", "voice:whisper")
        second_worker = self.register("win-1", "voice:whisper")
        job = self.scheduler.submit(
            capability="voice:whisper",
            payload={},
            max_attempts=2,
        )
        self.scheduler.claim(first_worker.id, "voice:whisper")

        self.clock.advance(11)
        recovered = self.scheduler.claim(second_worker.id, "voice:whisper")

        self.assertEqual(recovered.id, job.id)
        self.assertEqual(recovered.attempts, 2)
        self.assertEqual(recovered.worker_id, second_worker.id)

    def test_heartbeat_renews_active_job_lease(self) -> None:
        worker = self.register("mac-1", "voice:whisper")
        job = self.scheduler.submit(capability="voice:whisper", payload={})
        self.scheduler.claim(worker.id, "voice:whisper")
        self.clock.advance(8)

        self.scheduler.heartbeat(worker.id, [job.id])
        self.clock.advance(5)

        self.assertEqual(self.scheduler.get_job(job.id).status, "leased")

    def test_rejects_completion_from_a_different_worker(self) -> None:
        owner = self.register("owner", "system:echo")
        stranger = self.register("stranger", "system:echo")
        job = self.scheduler.submit(capability="system:echo", payload={})
        self.scheduler.claim(owner.id, "system:echo")

        with self.assertRaises(JobOwnershipError):
            self.scheduler.complete(
                job_id=job.id,
                worker_id=stranger.id,
                succeeded=True,
                result={},
            )


if __name__ == "__main__":
    unittest.main()
