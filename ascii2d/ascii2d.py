from __future__ import annotations
from dataclasses import dataclass
from urllib.parse import urlparse
from aiohttp import ClientSession
from hashlib import md5
from enum import Enum
from io import BytesIO

from PicImageSearch.model import Ascii2DResponse, Ascii2DItem
from PicImageSearch.ascii2d import Ascii2D as PISAscii2d

class Ascii2d():
    def __init__(self, config: Ascii2dConfig) -> None:
        self.config = config
        self.session = None
        self.__internal = PISAscii2d()
    
    async def search(self, img_path:str) -> list[Ascii2dResult]:
        resp = await self.__internal.search(file=img_path)
        result = parse_ascii2d_response(resp)
        self.__sort_result(result)
        return result

    async def get_session(self) -> ClientSession:
        if self.session is None:
            self.session = ClientSession()
            if not self.config.user_agent is None:
                self.session.headers.update({'user-agent':self.config.user_agent})
        return self.session

    def __sort_result(self, results: list[Ascii2dResult]):
        match self.config.sort_order:
            case SortOrder.No:
                return
            case SortOrder.FileSize:
                results.sort(key=lambda r: r.file_size, reverse=True)
            case SortOrder.ImageSize:
                results.sort(key=lambda r: r.image_size, reverse=True)
    
    def get_prefered_results(self, results: list[Ascii2dResult]) -> tuple[list[Ascii2dResult], list[Ascii2dResult]]:
        pref = [r for r in results if r.origin == self.config.prefered]
        non_pref = [r for r in results if not r.origin == self.config.prefered]
        return pref, non_pref
    
    async def fetch_thumbnail(self, target: Ascii2dResult) -> BytesIO:
        session = await self.get_session()
        async with session.get(target.thumbnail_link) as res:
            buf = await res.content.read()
            return BytesIO(buf)
            
    
    # def __cleanup(self):
    #     for driver in self.drivers.values():
    #         driver.quit()
        

def get_md5(img_path: str, chunk_size: int = 1024) -> str:
    with open(img_path, 'rb') as img:
        h = md5()
        c = img.read(chunk_size)
        while c:
            h.update(c)
            c = img.read(chunk_size)
        return h.hexdigest()

def parse_ascii2d_response(resp: Ascii2DResponse) -> list[Ascii2dResult]:
    res = list[Ascii2dResult]()
    for r in resp.raw:
        res.append(parse_ascii2d_item(r))
    return res

def parse_ascii2d_item(item: Ascii2DItem) -> Ascii2dResult:
    info_split = item.detail.split(" ")
    size = info_split[0].split("x")
    width = int(size[0])
    height = int(size[1])
    image_size = width * height
    extension = info_split[1].lower()
    if extension == "jpeg":
        extension = "jpg"
    file_size = float(info_split[2].split("KB")[0])
    origin = None
    if item.url.startswith("https://twitter"):
        origin = OriginType.Twitter
    elif item.url.startswith("https://www.pixiv"):
        origin = OriginType.Pixiv
    elif item.url.startswith("https://seiga"):
        origin = OriginType.Niconico
    else:
        origin = OriginType.Fanbox
    id = urlparse(item.url).path.split('/')[-1]
    return Ascii2dResult(item.thumbnail, item.hash, width, height, extension, file_size, image_size, origin, item.url, item.title, item.author, item.author_url, None, id)

class OriginType(Enum):
    Twitter = 'twitter'
    Pixiv = 'pixiv'
    Niconico = 'niconico'
    Fanbox = 'fanbox'

class SortOrder(Enum):
    No = 0
    ImageSize = 1
    FileSize =2

class Ascii2dConfig:
    def __init__(self, user_agent: str = None, sort_order: SortOrder = SortOrder.No, first: int = 0, prefered: OriginType = OriginType.Pixiv) -> None:
        self.user_agent = user_agent
        self.sort_order = sort_order
        self.first = first
        self.prefered = prefered


@dataclass
class Ascii2dResult:
    thumbnail_link:str
    md5:str
    width:int
    height:int
    extension:str
    file_size:float
    image_size:int
    origin:OriginType
    orig_link:str
    title:str
    author:str
    author_link:str
    index: int
    id: str

if __name__ == "__main__":
    pass
    

