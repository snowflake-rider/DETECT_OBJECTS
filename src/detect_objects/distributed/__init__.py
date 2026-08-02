"""Run ODIA models on separate machines.

The distributed version has two roles:

- The YOLO machine owns the camera and receives class names.
- The Whisper machine owns the microphone and sends class names.

Networking is intentionally kept outside the model manager classes.
"""
