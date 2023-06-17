from __future__ import annotations
from origins import Origin, OriginData, DeletedException
from dataclasses import dataclass
from aiohttp import ClientSession
from bs4 import BeautifulSoup
from json import loads
from urllib.parse import urlparse, urlunparse
from io import BytesIO
import asyncio_atexit

class Pixiv(Origin):
    def __init__(self, config:PixivConfig):
        self.config = config
        self.session = None

    async def __get_session(self) -> ClientSession:
        if self.session is None:
            cookies = {"PHPSESSID": self.config.PHPSESSID}
            self.session = ClientSession(cookies=cookies)
            if not self.config.user_agent is None:
                self.session.headers.update({'user-agent':self.config.user_agent})
        asyncio_atexit.register(self.__cleanup)
        return self.session
    
    async def fetch_data(self, url: str) -> OriginData:
        session = await self.__get_session()
        img_id = urlparse(url).path.split('/')[-1]
        async with session.get(url) as r:
            text = await r.text()
            soup = BeautifulSoup(text, 'lxml')
            meta = soup.find('meta', attrs={'id': 'meta-preload-data'})
            if meta is None:
                raise PixivDeletedException
            meta_json = loads(meta['content'])
            urls_dict = meta_json['illust'][f'{img_id}']['urls']
            page = meta_json['illust'][f'{img_id}']['pageCount']

            orig_urls = list[str]()
            thumb_urls = list[str]()
            for i in range(page):
                orig_urls.append(get_page_url(urls_dict['original'], i))
                thumb_urls.append(get_page_url(urls_dict['small'], i))
            return OriginData(orig_urls, thumb_urls, page)
    
    async def fetch_img(self, url:str) -> BytesIO:
        session = await self.__get_session()
        session.headers.update({'referer': 'https://www.pixiv.net/'})
        async with session.get(url) as res:
            buf = await res.content.read()
            return BytesIO(buf)
    
    async def __cleanup(self):
        if not self.session is None:
            await self.session.close()

def get_page_url(url: str, page: int):
    parsed = urlparse(url)
    paths = parsed.path.split('/')
    filename = paths[-1]
    splited_filename = filename.split('.')
    cmp = splited_filename[0].split('_')
    cmp[1] = f'p{page}'
    ext = splited_filename[1]
    new_filename = '_'.join(cmp)
    target = f'{new_filename}.{ext}'
    paths[-1] = target
    new_path = '/'.join(paths)
    return urlunparse((parsed.scheme, parsed.netloc, new_path, parsed.params, parsed.query, parsed.fragment))

class PixivDeletedException(DeletedException):
    pass

class PixivConfig:
    def __init__(self, PHPSESSID:str, user_agent:str='') -> None:
        self.PHPSESSID = PHPSESSID
        self.user_agent = user_agent

@dataclass
class PixivUrls:
    mini:str
    thumb:str
    small:str
    regular:str
    original:str
    page: int
    
if __name__ == '__main__':
    pass