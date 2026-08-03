"""Run ODIA models on separate machines.

The model cluster uses a coordinator and pull-based workers.  The older direct
Whisper-to-YOLO nodes remain available for simple two-machine deployments.
Networking stays outside the local model manager classes.
"""
