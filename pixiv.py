from __future__ import annotations
from json.decoder import JSONDecodeError
import requests
import requests.cookies
import json
from collections.abc import Iterable
from bs4 import BeautifulSoup
import logging

class Pixiv:
    def __init__(self, pixivsetting:PixivSetting, logger:logging.Logger=logging.getLogger('pixiv')):
        self.setting = pixivsetting
        self.session = requests.session()
        self.logger = logger

        self.session.cookies['PHPSESSID'] = self.setting.PHPSESSID
        self.session.cookies['device_token'] = self.setting.device_token

        if not self.setting.user_agent is None:
            self.session.headers = {'user-agent': self.setting.user_agent}
        
    
    def get_image_urls(self, img_id:int) -> PixivUrls:
        url = 'https://www.pixiv.net/artworks/{}'.format(str(img_id))
        with self.session.get(url) as r:
            soup = BeautifulSoup(r.text, 'html.parser')
            meta_list = list()
            for meta in soup.find_all('meta'):
                try:
                    meta_list.append(json.loads(meta['content'])) # check if meta content is json
                except (JSONDecodeError, KeyError):
                    pass
            for j in meta_list:
                if isinstance(j, Iterable):
                    if 'illust' in j:
                        try:
                            return PixivUrls(j['illust'][list(j['illust'].keys())[0]]['urls']) # meta -> content -> illust -> [illust id] -> urls
                        except:
                            pass
        self.logger.info('"{}" has been deleted.'.format(url))
        return PixivUrls()
                        
    def get_image(self, url:str, path:str=None) -> None:
        self.session.headers['referer'] = 'https://www.pixiv.net/'
        with self.session.get(url, stream=True) as r:
            fn = url.split('/')[-1] if path is None else path
            with open(fn, 'wb+') as f:
                for c in r.iter_content(chunk_size=4096):
                    if c:
                        f.write(c)
                self.logger.debug('"{}" has been retrieved.'.format(url))

class PixivSetting:
    def __init__(self, PHPSESSID:str, device_token:str, user_agent:str=None) -> None:
        self.PHPSESSID = PHPSESSID
        self.device_token = device_token
        self.user_agent = user_agent

class PixivUrls:
    def __init__(self, src:dict=None) -> None:
        if not src is None:
            self.mini:str = src['mini']
            self.thumb:str = src['thumb']
            self.small:str = src['small']
            self.regular:str = src['regular']
            self.original:str = src['original']
        else:
            self.mini:str = None
            self.thumb:str = None
            self.small:str = None
            self.regular:str = None
            self.original:str = None
    def is_all_available(self):
        return self.mini is None or self.thumb is None or self.small is None or self.regular is None or self.original is None


if __name__ == '__main__':
    pass