from pathlib import Path
from ultralytics import YOLOWorld
import sys
import json 
PATH_NOW = Path(__file__).parent
print(PATH_NOW)
ROOT = PATH_NOW.resolve().parent
sys.path.append(str(ROOT))
print(f"path now : {ROOT}")

from models.yolo_world_module import YOLO_World_Manager

if __name__=="__main__":

    try:
        with YOLO_World_Manager() as manager:
            model=manager._model
            names = model.names
            file_path = Path(f"{str(PATH_NOW)}/class_names.json")
            last_json = {}
            for idx,data in enumerate(names.items()):
                class_id,class_name = data
                dictionary_dat={}
                dictionary_dat["class_id"] = class_id
                dictionary_dat["class_name"] = class_name
                last_json[idx]=dictionary_dat
            with open(str(file_path),"w",encoding="UTF-8") as f:
                json.dump(last_json,f,ensure_ascii=False,indent=4)
    except RuntimeError as e:
        print("failed")