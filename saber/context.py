from imagehash import ImageHash, ImageMultiHash

from ascii2d import Ascii2dResult


class SaberContext:
    def __init__(self, src_path: str, hash: ImageHash | ImageMultiHash, md5: str) -> None:
        self.src_path: str = src_path
        self.hash: ImageHash | ImageMultiHash = hash
        self.target: Ascii2dResult = None
        self.results: list[Ascii2dResult] = None
        self.dest_url: str = None
        self.dest_path: str = None
        self.md5: str = md5