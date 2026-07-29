import cv2
import platform
# import sys
# from pathlib import Path

# ROOT = Path(__file__).resolve().parent.parent
# sys.path.append(str(ROOT))

from ..models.yolo_world_module import YOLO_World_Manager

class Camera_Manager:
    def __init__(self):
        self__backend = self._select_backend()
        self.__manager_obj = cv2.VideoCapture(0,self__backend)
    def _select_backend(self)->int:
        os_name = platform.system()
        print(f"os name : {os_name}")
        backend_map = {
            "Darwin": cv2.CAP_AVFOUNDATION,  # macOS
            "Linux": cv2.CAP_V4L2,           # Linux
            "Windows": cv2.CAP_MSMF,         # Windows 10/11
        }
        return backend_map.get(os_name,cv2.CAP_ANY)
    def start_record(self):

        if self.__manager_obj is None or not self.__manager_obj.isOpened():
            self.gc_resource()
            raise RuntimeError("camera unavilable!")
        yolo_manager= YOLO_World_Manager(confidence=0.35)
        while True:
            is_success, frame = self.__manager_obj.read()
            if not is_success:
                print("cannot read frame")
                break

            cv2.imshow("Camera",frame)
            if cv2.waitKey(1)&0xFF==ord("q"):
                break
        self._gc_resource()
    def _gc_resource(self):
        if self.__manager_obj is not None:
            self.__manager_obj.release()
        cv2.destroyAllWindows()

if __name__=="__main__":
    try:
        camera_manager = Camera_Manager()
        camera_manager.start_record()
    except RuntimeError as e:
        print(e)