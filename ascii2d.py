from __future__ import annotations
import logging
from os import path
import bs4
from bs4.element import ResultSet
import requests
from requests_toolbelt import MultipartEncoder
from collections import UserList
from collections.abc import Iterator
from bs4 import BeautifulSoup
import hashlib

class Ascii2dSearch:
    def __init__(self, img_path:str, user_agent:str = None, logger:logging.Logger = logging.getLogger('ascii2dsearch')) -> None:

        self.logger = logger

        self.img_path:str = img_path
        self.search_result: Ascii2dResultList = None

        self.session = requests.session()
        self.ua:str = user_agent
        if not self.ua is None:
            self.session.headers.update({'User-agent': self.ua})
        
        with open(img_path, 'rb') as img:
            h = hashlib.md5()
            cs = 4096
            c = img.read(cs)
            while c:
                h.update(c)
                c = img.read(cs)
            self.md5 = h.hexdigest()
    
    def search(self) -> None:
        self.search_with_md5()
        if not self.result_found:
            self.search_with_file()
    
    def search_with_file(self) -> None:
        try:
            b = BeautifulSoup(self.session.get('https://ascii2d.net/').text, 'html.parser')
            t = b.find_all(attrs={'action': '/search/file'})[0].find_all_next(attrs={'name': 'authenticity_token'})[0]['value']
            p = {'utf8': (None, '&#x2713;', 'text/html'), 'authenticity_token': (None, t, 'text/html'), 'file': (path.basename(self.img_path), open(self.img_path,'rb'), 'image/apng')}
            mp = MultipartEncoder(p)
            with self.session.post('https://ascii2d.net/search/file', headers=self.session.headers.update({'Content-Type': mp.content_type}), data=mp) as r:
                rb = BeautifulSoup(r.text, 'html.parser')
                rs = rb.find_all(attrs={'class':'item-box'})
                self.search_result = self.resolve_result(rs)
        except:
            self.renew_session()

    def search_with_md5(self) -> None:
        try:
            with self.session.get('https://ascii2d.net/search/color/{}'.format(self.md5)) as r:
                b = BeautifulSoup(r.text, 'html.parser')
                rs = b.find_all(attrs={'class':'item-box'})
                self.search_result = self.resolve_result(rs)
        except:
            self.renew_session()

    def renew_session(self) -> None:
        del self.session
        self.session = None
        self.session = requests.session()
        if not self.ua is None:
            self.session.headers.update({'User-agent': self.ua})

    def resolve_result(self, res:ResultSet) -> Ascii2dResultList:
        rrs = Ascii2dResultList()
        for r in res:
            rrs.append(Ascii2dResult(r))
        return rrs
        
    def result_found(self) -> bool:
        if self.search_result is None:
            self.search()
        return len(self.search_result) > 0
    

class Ascii2dResult:
    def __init__(self, item_box:bs4.element.Tag):
        md5 = item_box.find_next(attrs={'class': 'hash'})
        info  = md5.find_next(attrs={'class': 'text-muted'}).decode_contents().split(' ')
        size = info[0]
        detail_box = item_box.find_next(attrs={'class': 'detail-box'})
        site_icon = detail_box.find_next('img')
        link = site_icon.find_next('a')
        author = link.find_next('a')

        self.thumbnail_link = 'https://ascii2d.net/{}'.format(item_box.find_next(attrs={'class': 'image-box'}).find_next('img')['src'])
        self.md5 = md5.decode_contents()
        self.width = int(size.split('x')[0])
        self.height = int(size.split('x')[1])
        self.extension = info[1]
        self.file_size = float(info[2].split('KB')[0])

        self.site:str = site_icon['alt']
        self.link:str = link['href']
        self.title:str = link.decode_contents()
        self.author:str = author.decode_contents()
        self.author_link:str = author['href']

    def get_image_size(self) -> int:
        return self.width * self.height

    def __repr__(self) -> str:
        return 'Ascii2dResult(thumbnail_link={}, md5={}, width={}, height={}, extension={}, file_size={}, site={}, link={}, title={}, author={}, auhtor_link={})'.format(self.thumbnail_link, self.md5, self.width, self.height, self.extension, self.file_size, self.site, self.link, self.title, self.author, self.author_link)

class Ascii2dResultList(UserList):
    def __init__(self):
        self.data = list()

    def __getitem__(self, index:int) -> Ascii2dResult:
        return super().__getitem__(index)
    
    def __setitem__(self, index:int, item:Ascii2dResult):
        if not isinstance(item, Ascii2dResult):
            raise TypeError
        else:
            return super.__setitem__(index, item)
    
    def __iter__(self) -> Iterator[Ascii2dResult]:
        return super().__iter__()

    def append(self, item: Ascii2dResult) -> None:
        return super().append(item)
    
    def __len__(self) -> int:
        return super().__len__()
    

if __name__ == '__main__':
    pass