from __future__ import annotations
from dataclasses import dataclass
from urllib.parse import urlparse
from requests import session
from requests_toolbelt import MultipartEncoder
from hashlib import md5
from bs4 import BeautifulSoup
from bs4.element import Tag
from enum import Enum
from os.path import basename, splitext

class Ascii2d():
    def __init__(self, config: Ascii2dConfig) -> None:
        self.config = config
        self.session = session()
        if not self.config.user_agent is None:
            self.session.headers.update({'user-agent':self.config.user_agent})
    
    def search(self, img_path:str) -> list[Ascii2dResult]:
        result_md5 = self.search_md5(img_path)
        if len(result_md5) > 0:
            return result_md5
        return self.search_file(img_path)

    def search_md5(self, img_path:str) -> list[Ascii2dResult]:
        with self.session.get(f'https://ascii2d.net/search/color/{get_md5(img_path)}') as r:
            soup = BeautifulSoup(r.text, 'lxml')
            results = self.__parse_asii2d_soup(soup)
            return results
    
    def search_file(self, img_path:str) -> list[Ascii2dResult]:
        base = BeautifulSoup(self.session.get('https://ascii2d.net/').text, 'html.parser')
        token = base.find(attrs={'name': 'authenticity_token'})['value']
        post_data = {'utf8': (None, '\U00002713', 'text/html'), 'authenticity_token': (None, token, 'text/html'), 'file': (basename(img_path), open(img_path,'rb'), f'image/{splitext(img_path)}')}
        multipart = MultipartEncoder(post_data)
        headers = self.session.headers.copy()
        headers['Content-Type'] = multipart.content_type
        with self.session.post('https://ascii2d.net/search/file', headers=headers, data=multipart) as r:
            soup = BeautifulSoup(r.text, 'lxml')
            results = self.__parse_asii2d_soup(soup)
            return results
    
    def request_thumbnail(self, target:Ascii2dResult):
        return self.session.get(f'https://ascii2d.net/{target.thumbnail_link}')

    def __parse_asii2d_soup(self, soup: BeautifulSoup) -> list[Ascii2dResult]:
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
        

def get_md5(img_path: str, chunk_size: int = 1024) -> str:
    with open(img_path, 'rb') as img:
        h = md5()
        c = img.read(chunk_size)
        while c:
            h.update(c)
            c = img.read(chunk_size)
        return h.hexdigest()

def parse_ascii2d_result(item_box:Tag) -> Ascii2dResult:
    md5_e = item_box.find_next(attrs={'class': 'hash'})
    info  = md5_e.find_next('small').decode_contents().split(' ')
    size = info[0]
    detail_box = item_box.find_next(attrs={'class': 'detail-box'})
    link = detail_box.find_next('a')
    origin = parse_origin(detail_box.find_next('img').get(key='alt'))
    author_e = link.find_next('a')

    thumbnail_link = item_box.find_next(attrs={'class': 'image-box'}).find_next('img').get(key='src')
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


def parse_origin(origin: str) -> Origin:
    match origin.lower():
        case "twitter":
            return Origin.Twitter
        case "pixiv":
            return Origin.Pixiv
        case "niconico":
            return Origin.Niconico
        case "fanbox":
            return Origin.Fanbox

class Origin(Enum):
    Twitter = 'twitter'
    Pixiv = 'pixiv'
    Niconico = 'niconico'
    Fanbox = 'fanbox'

class SortOrder(Enum):
    No = 0
    ImageSize = 1
    FileSize =2

class Ascii2dConfig:
    def __init__(self, user_agent: str = None, sort_order: SortOrder = SortOrder.No, first: int = 0, prefered: Origin = Origin.Pixiv) -> None:
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
    origin:Origin
    orig_link:str
    title:str
    author:str
    author_link:str
    index: int
    id: str

if __name__ == "__main__":
    pass
    

