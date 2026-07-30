import json
from pathlib import Path
from dataclasses import dataclass
from typing import Self

@dataclass(frozen=True)
class DetectedClass:
    korean_word:str
    index:int
    yolo_class:str

class Text_Manager:
    def __init__(self):
        self.__dictionary:dict=None
        self.__keys:list=None
        self.__dictionary_list:list=None

    def _normalize(self,text:str)->str:
        if not isinstance(text,str):
            raise RuntimeError("string 이 아닌 데이터")
        return text.lower().replace(" ","").strip()

    def _load_class_dictionary(self):
        parent_dir = str(Path(__file__).resolve().parent)
        class_names_json_file=f"{parent_dir}/korean_class_names.json"
        print(f"json file : {class_names_json_file}")
        try:
            with open(class_names_json_file,"r",encoding="UTF-8") as f:
                dic = json.load(f)
            if not isinstance(dic,dict):
                raise RuntimeError("Not a Dictionary type")
            self.__dictionary=dic
            self.__keys = dic.keys()
            self.__dictionary_list = sorted(
                self.__dictionary.items(),
                key=lambda item : len(self._normalize(item[0])),
                reverse=True
            )
        except Exception as e:
            print(e)
            raise RuntimeError("error occurred")
    def __enter__(self)->Self:
        try:
            self._load_class_dictionary()
        except Exception as e:
            print("failed to load data")
            raise RuntimeError(e)
        return self
    
    def __exit__(self, exc_type, exc, tb):
        pass

    def extract(self,text:str)->list:
        print("extract\n")
        print(f"text : {text}")
        normalized_text = self._normalize(text)
        if (self.__dictionary) is None or len(self.__dictionary)==0 or not isinstance(self.__dictionary,dict):
            raise ValueError("invalid dictionary")
        found_yolo_classes:set[str] = set()
        detected_classes = []
        for key,data in self.__dictionary_list:
            class_name,class_id = data.items()
            if key not in normalized_text:
                continue
            if class_name in found_yolo_classes:
                continue
            detected_classes.append(DetectedClass(korean_word=key,yolo_class=class_name,index=class_id))
            found_yolo_classes.add(class_name)
        
        return detected_classes
if __name__ == "__main__":
    try:
        with Text_Manager() as manager:
            class_list=manager.extract("백팩을 맨 사람")
            print(class_list)
    except Exception as e:
        print(e)