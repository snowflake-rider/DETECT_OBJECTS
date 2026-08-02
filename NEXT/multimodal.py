"""Simple distributed multimodal-video plan.

Goal
----
Play short, clear videos such as cats meowing, dogs barking, and an F1
car driving. Combine vision and audio observations into a short summary.

Live pipeline
-------------

Player / coordinator
├── video frames → vision worker → YOLO + tracking
├── video audio  → audio worker  → sound classifier
└── every 5 seconds:
    ├── save one representative screenshot
    ├── save the matching audio chunk
    ├── collect object and sound results for that time window
    └── send the completed window to a background queue

Pixeltable worker
├── store screenshots, audio chunks, timestamps, and model results
├── create a summary for each five-second window
└── create the final summary when the video ends

The tracker processes frames continuously. Screenshots are only saved as
evidence; they are not the only frames used for detection.

Distributed AI system
---------------------

Each worker owns one model and may run on a separate machine:

* vision machine: YOLO + object tracking
* audio machine: sound classification
* data machine: Pixeltable storage and summarization

The player communicates with the workers through a small queue or API. Every
message includes ``video_id``, ``start_seconds``, and ``end_seconds`` so that
vision and audio results can be combined correctly. Background processing must
never pause video playback.

Multiple machines can reduce competition for CPU, GPU, and memory, but they are
not automatically faster because sending data over the network also has a cost.
The same worker boundaries can first be tested on one machine and distributed
later without changing the overall design.

Observation saved for each window
---------------------------------

* video ID and time range
* screenshot path
* audio-chunk path
* tracked objects and confidence scores
* classified sounds and confidence scores
* combined window summary

Example summaries
-----------------

* "A cat is visible, and meowing is audible."
* "A dog is visible, and barking is audible."
* "A racing car is visible, and engine noise is audible."

The wording keeps the two observations separate. Detecting a visible cat and
hearing a meow does not prove that the visible cat produced the sound.

Pixeltable documentation: https://docs.pixeltable.com/
"""
