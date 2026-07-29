import cv2
import platform
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT))

from models.yolo_world_module import YOLO_World_Manager

class Camera_Manager:
    def __init__(self):
        self__backend = self._select_backend()
        self.__manager_obj = cv2.VideoCapture(0,self__backend)
        self.__classes=[
            "smartphone",
            "wristwatch",
            "keyboard",
            "person",
        ]
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
        try:
            yolo_manager= YOLO_World_Manager(confidence=0.35)
            yolo_manager.load()
            yolo_manager.set_classes(self.__classes)
        except Exception as e:
            print(e)
            self._gc_resource()
            return 
        while True:
            is_success, frame = self.__manager_obj.read()
            if not is_success:
                print("cannot read frame")
                break
            frame_height, frame_width = frame.shape[:2]      
            boxes,names = yolo_manager.predict(frame=frame)      

            for box in boxes:
                x1,y1,x2,y2 = box.xyxyn[0].tolist()
                x1=int(x1*frame_width)
                y1=int(y1*frame_height)
                x2=int(x2*frame_width)
                y2=int(y2*frame_height)
                confidence = float(box.conf)
                class_id = int(box.cls[0].item())
                class_name = names[class_id]
                cv2.rectangle(
                    frame,
                    (x1,y1),
                    (x2,y2),
                    (0, 255, 0),
                    2,
                )
                confidence = float(box.conf[0].item())
                label = f"confidence:{confidence} , name: {class_name}"
                cv2.putText(
                    frame,
                    label,
                    (x1, y1 + 30),
                    cv2.FONT_HERSHEY_PLAIN,
                    2,
                    (0, 0, 255),
                    2,
                )

            cv2.imshow("Camera",frame)
            if cv2.waitKey(1)&0xFF==ord("q"):
                break
        yolo_manager.close()
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