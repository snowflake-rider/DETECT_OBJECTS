"""End-to-end tests for coordinator, client, and pull worker."""

from threading import Thread
import time
import unittest

from detect_objects.distributed.client import ClusterClient, ClusterHTTPError
from detect_objects.distributed.coordinator import CoordinatorServer
from detect_objects.distributed.model_handlers import EchoHandler
from detect_objects.distributed.scheduler import Scheduler
from detect_objects.distributed.worker import ClusterWorker


class ClusterHTTPTests(unittest.TestCase):
    def setUp(self) -> None:
        self.server = CoordinatorServer(
            ("127.0.0.1", 0),
            scheduler=Scheduler(lease_seconds=2, worker_ttl_seconds=2),
            token="test-token",
        )
        self.server_thread = Thread(target=self.server.serve_forever, daemon=True)
        self.server_thread.start()
        host, port = self.server.server_address[:2]
        address = f"http://{host}:{port}"
        self.client = ClusterClient(address, token="test-token")
        self.unauthorized_client = ClusterClient(address, token="wrong")

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.server_thread.join(timeout=1)

    def test_rejects_an_invalid_shared_token(self) -> None:
        with self.assertRaises(ClusterHTTPError) as raised:
            self.unauthorized_client.list_workers()

        self.assertEqual(raised.exception.status, 401)

    def test_runs_job_through_real_pull_worker(self) -> None:
        worker = ClusterWorker(
            coordinator=self.client.coordinator,
            token="test-token",
            name="test-mac",
            handlers={"system:echo": EchoHandler()},
        )
        worker_thread = Thread(target=worker.run, daemon=True)
        worker_thread.start()
        self._wait_for_worker()

        job_id = self.client.submit("system:echo", {"message": "안녕"})
        job = self.client.wait(job_id, timeout_seconds=3, poll_seconds=0.02)

        self.assertEqual(job["status"], "succeeded")
        self.assertEqual(job["result"], {"echo": {"message": "안녕"}})
        worker.stop_event.set()
        worker_thread.join(timeout=3)
        self.assertFalse(worker_thread.is_alive())

    def _wait_for_worker(self) -> None:
        for _ in range(100):
            if self.client.list_workers():
                return
            time.sleep(0.01)
        self.fail("worker did not register")


if __name__ == "__main__":
    unittest.main()
