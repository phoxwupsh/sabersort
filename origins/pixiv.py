from __future__ import annotations
from dataclasses import dataclass
from requests import Response, session
from bs4 import BeautifulSoup
from json import loads
from urllib.parse import urlparse, urlunparse

class Pixiv:
    def __init__(self, config:PixivConfig):
        self.config = config
        self.session = session()

        self.session.cookies.set(name='PHPSESSID', value=self.config.PHPSESSID)

        if not self.config.user_agent is None:
            self.session.headers.update({'user-agent': self.config.user_agent})
    def get_urls(self, img_id: int | str):
        url = f'https://www.pixiv.net/artworks/{img_id}'
        with self.session.get(url) as r:
            soup = BeautifulSoup(r.text, 'lxml')
            meta = soup.find('meta', attrs={'id': 'meta-preload-data'})
            if meta is None:
                raise PixivDeletedError
            meta_json = loads(meta['content'])
            urls_dict = meta_json['illust'][f'{img_id}']['urls']
            page = meta_json['illust'][f'{img_id}']['pageCount']
            return PixivUrls(urls_dict['mini'], urls_dict['thumb'], urls_dict['small'], urls_dict['regular'], urls_dict['original'],page)
    
    def fetch_image(self, url:str) -> Response:
        self.session.headers.update({'referer': 'https://www.pixiv.net/'})
        return self.session.get(url, stream=True)

def get_pixiv_page(url: str, page: int):
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

class PixivDeletedError(Exception):
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