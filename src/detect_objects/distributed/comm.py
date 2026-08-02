"""Communication shared by the YOLO and Whisper machines."""

from collections.abc import Callable
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Event
from urllib.request import Request, urlopen


def send_classes(yolo_address: str, class_names: list[str]) -> None:
    """Send classes to an address such as http://192.168.1.10:8000."""
    if not yolo_address.strip():
        raise ValueError("YOLO address cannot be empty")

    # Add /classes to the YOLO machine's address.
    endpoint = f"{yolo_address.rstrip('/')}/classes"
    body = json.dumps({"classes": class_names}).encode("utf-8")
    request = Request(
        endpoint,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    # Send the request and read the reply.
    with urlopen(request, timeout=5) as response:
        response.read()


def receive_classes(
    host: str,
    port: int,
    on_classes_received: Callable[[list[str]], None],
    shutdown_event: Event | None = None,
) -> None:
    """Receive class names and pass them to the camera application."""

    # This class is inside because only this function uses it.
    class ClassRequestHandler(BaseHTTPRequestHandler):
        # HTTPServer requires the name do_POST.
        def do_POST(self) -> None:
            # self.path is "/classes" in this request.
            if self.path != "/classes":
                self.send_error(404, "Endpoint not found")
                return

            try:
                # Content-Length is the number of message bytes.
                content_length = int(self.headers.get("Content-Length", "0"))

                # rfile is the message body. json.loads makes it a dictionary.
                message = json.loads(self.rfile.read(content_length))

                # Example: ["person", "backpack"]
                class_names = message["classes"]
            except (ValueError, KeyError, TypeError, json.JSONDecodeError):
                self.send_error(400, "Invalid JSON message")
                return

            # Check that every class is a non-empty string.
            if not isinstance(class_names, list) or not all(
                isinstance(name, str) and name for name in class_names
            ):
                self.send_error(400, "Classes must be a list of names")
                return

            # Give the classes to the YOLO node.
            on_classes_received(class_names)

            # Tell Whisper that the classes arrived.
            self.send_response(204)
            self.end_headers()

        def log_message(self, format: str, *args) -> None:
            # Keep normal class updates quiet.
            return

    # Listen for requests on this host and port.
    with HTTPServer((host, port), ClassRequestHandler) as server:
        # Check for shutdown every 0.2 seconds.
        server.timeout = 0.2

        # Keep receiving until another thread requests shutdown.
        while shutdown_event is None or not shutdown_event.is_set():
            server.handle_request()
