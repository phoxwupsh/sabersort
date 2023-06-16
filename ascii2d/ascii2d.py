from __future__ import annotations
from dataclasses import dataclass
from urllib.parse import urlparse
from aiohttp import ClientSession
from hashlib import md5
from enum import Enum
from io import BytesIO, BufferedReader
from typing import Any
from pathlib import Path
from bs4 import BeautifulSoup, Tag
from PicImageSearch.ascii2d import Ascii2D as PISAscii2d
import asyncio_atexit

class Ascii2d():
    def __init__(self, config: Ascii2dConfig) -> None:
        self.config = config
        self.session = None
        self.__internal = PISAscii2dExtend()
    
    async def search(self, img_path:str) -> list[Ascii2dResult]:
        hash = None
        result = None
        with open(img_path, "rb") as img:
            hash = get_md5(img)
        
        resp_text_md5, _ = await self.__internal.search_md5_raw(hash)
        result = self.__parse_ascii2d_resp(resp_text_md5)
        if len(result) > 0:
            self.__sort_result(result)
            return result
        else:
            resp_text, _ = await self.__internal.search_raw(file=img_path)
            result = self.__parse_ascii2d_resp(resp_text)
        self.__sort_result(result)
        return result

    async def __get_session(self) -> ClientSession:
        if self.session is None:
            self.session = ClientSession()
            if not self.config.user_agent is None:
                self.session.headers.update({'user-agent':self.config.user_agent})
        asyncio_atexit.register(self.__cleanup)
        return self.session

    def __sort_result(self, results: list[Ascii2dResult]):
        match self.config.sort_order:
            case SortOrder.No:
                return
            case SortOrder.FileSize:
                results.sort(key=lambda r: r.file_size, reverse=True)
            case SortOrder.ImageSize:
                results.sort(key=lambda r: r.image_size, reverse=True)
    
    def __parse_ascii2d_resp(self, resp_text: str) -> list[Ascii2dResult]:
        soup = BeautifulSoup(resp_text, "lxml")
        rs = soup.find_all(attrs={'class':'item-box'})
        results = list[Ascii2dResult]()
        for r in rs:
            parsed = parse_ascii2d_result(r)
            if not parsed.origin == None:
                results.append(parsed)
        if len(results) > self.config.first and self.config.first > 0:
            results = results[:self.config.first]
        self.__sort_result(results)
        return results
    
    def get_prefered_results(self, results: list[Ascii2dResult]) -> tuple[list[Ascii2dResult], list[Ascii2dResult]]:
        pref = [r for r in results if r.origin == self.config.prefered]
        non_pref = [r for r in results if not r.origin == self.config.prefered]
        return pref, non_pref
    
    async def fetch_thumbnail(self, target: Ascii2dResult) -> BytesIO:
        session = await self.__get_session()
        async with session.get(target.thumbnail_link) as res:
            buf = await res.content.read()
            return BytesIO(buf)
            
    async def __cleanup(self):
        if not self.session is None:
            await self.session.close()
        

def get_md5(file: BufferedReader, chunk_size: int = 1024) -> str:
    h = md5()
    c = file.read(chunk_size)
    while c:
        h.update(c)
        c = file.read(chunk_size)
    return h.hexdigest()

def parse_ascii2d_result(item_box:Tag) -> Ascii2dResult:
    md5_e = item_box.find_next(attrs={'class': 'hash'})
    info  = md5_e.find_next('small').decode_contents().split(' ')
    size = info[0]
    detail_box = item_box.find_next(attrs={'class': 'detail-box'})
    link = detail_box.find_next('a')
    origin = parse_origin(detail_box.find_next('img').get(key='alt'))
    author_e = link.find_next('a')

    thumbnail_link = f"https://ascii2d.net{item_box.find_next(attrs={'class': 'image-box'}).find_next('img').get(key='src')}"
    md5_hash = md5_e.decode_contents()
    width = int(size.split('x')[0])
    height = int(size.split('x')[1])
    extension = info[1].lower()
    if extension == 'jpeg':
        extension = 'jpg'
    file_size = float(info[2].split('KB')[0])
    image_size = width*height

    orig_link = link['href']
    title = link.decode_contents()
    author = author_e.decode_contents()
    author_link = author_e['href']
    id = urlparse(str(orig_link)).path.split('/')[-1]
    return Ascii2dResult(thumbnail_link,md5_hash,width,height,extension,file_size,image_size,origin,orig_link,title,author,author_link,None,id)

def parse_origin(origin: str) -> OriginType:
    match origin.lower():
        case "twitter":
            return OriginType.Twitter
        case "pixiv":
            return OriginType.Pixiv
        case "niconico":
            return OriginType.Niconico
        case "fanbox":
            return OriginType.Fanbox

class PISAscii2dExtend(PISAscii2d):
    def __init__(self, **request_kwargs: Any):
        super().__init__(**request_kwargs)
    
    async def search_md5_raw(self, hash: str) -> tuple[str, str]:
        resp_text, resp_url, _ = await self.get(f"https://ascii2d.net/search/color/{hash}")
        return resp_text, resp_url

    async def search_raw(self, url: str | None = None, file: str | bytes | Path | None = None) -> tuple[str, str]:
        if url:
            ascii2d_url = "https://ascii2d.net/search/uri"
            resp_text, resp_url, _ = await self.post(ascii2d_url, data={"uri": url})
        elif file:
            ascii2d_url = "https://ascii2d.net/search/file"
            files: dict[str, Any] = {"file": file if isinstance(file, bytes) else open(file, "rb")}
            resp_text, resp_url, _ = await self.post(ascii2d_url, files=files)
        else:
            raise ValueError("url or file is required")

        if self.bovw:
            resp_text, resp_url, _ = await self.get(resp_url.replace("/color/", "/bovw/"))

        return resp_text, resp_url


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
    

