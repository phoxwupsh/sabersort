from imagehash import ImageHash
from ascii2d import Ascii2dResult

class SaberContext:
    def __init__(self, src_path: str, hash: ImageHash, md5: str) -> None:
        self.src_path: str = src_path
        self.hash: ImageHash = hash
        self.target: Ascii2dResult = None
        self.results: list[Ascii2dResult] = None
        self.dest_url: str = None
        self.dest_path: str = None
        self.md5: str = md5
        self.__found = False
        self.__deleted = False
    
    def is_found(self) -> bool:
        return self.__found
    
    def found(self, target: Ascii2dResult):
        self.target = target
        self.__found = True
    
    def is_deleted(self) -> bool:
        return self.__deleted

    def deleted(self):
        self.__deleted = True