import threading
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT))

from camera_cv.camera import Camera_Manager

stop_event = threading.Event()
initialize_barrier = threading.Barrier(parties=2,action=(lambda : print("loading finished")))

def detecting_objects():
    try:
        camera_manager = Camera_Manager(camera_index=1,thread_event=stop_event)
        camera_manager.load_model()

        print("camera manager setting finished. Waiting for barrier to be ended...\n")
        initialize_barrier.wait()
    except threading.BrokenBarrierError:
        print("barrier wass destructed..\n")
        return
    except Exception as e:
        print(e)
        initialize_barrier.abort()
        return 
    try:
        camera_manager.start_record()
    except Exception as e:
        print(e)

def temp_worker():
    try:
        print("temp worker waiting..\n")
        initialize_barrier.wait()
    except threading.BrokenBarrierError as e:
        print(e)
        print("barrier was destructed..\n")
        return 

if __name__ == "__main__":
    temp_thread = threading.Thread(target=temp_worker)
    temp_thread.start()
    detecting_objects()
    temp_thread.join()
   
