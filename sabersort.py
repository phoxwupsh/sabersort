from __future__ import annotations
from io import BufferedRandom
from multiprocessing import cpu_count
from threading import RLock, Thread
from tempfile import TemporaryFile
from typing import Iterator
from imagehash import ImageHash
from urllib.parse import urlparse, parse_qs
from saberdb.saberdb import SaberDB, SaberDBConfig
from saberdb.hasher import Hasher, HashAlg
from ascii2d import Ascii2d, Ascii2dConfig, Ascii2dResult, Origin, SortOrder
from glob import glob
from utils import split_list
from origins.pixiv import Pixiv, PixivConfig, PixivDeletedError, PixivUrls, get_pixiv_page
from origins.twitter import Twitter, TwitterConfig, TwitterUrls, parse_twitter_url, TwitterDeletedError
from requests import Response, get
import os.path
from configparser import RawConfigParser
from shutil import copy
from PIL import Image

class Sabersort():
    def __init__(self, config:SabersortConfig, ascii2d: Ascii2d, db: SaberDB, pixiv:Pixiv, twitter:Twitter) -> None:
        self.config = config
        self.ascii2d = ascii2d
        self.db = db
        self.pixiv = pixiv
        self.twitter = twitter

    def sort(self):
        src_img_list = glob(os.path.join(os.path.abspath(self.config.src_dir),'*'))
        target_img_list = self.get_target_list(src_img_list)

        def sort_thread(targets: list[str]):
            for img_path in targets:
                results = self.ascii2d.search(img_path)
                self.__results_handler(img_path, results)

        splited_targets = split_list(target_img_list, self.config.threads)
        ts = list[Thread]()
        for l in splited_targets:
            t = Thread(target=sort_thread, args=(l,))
            ts.append(t)
            t.start()
        for t in ts:
            t.join()
    
    def __results_handler(self, src_img_path:str, results: list[Ascii2dResult]):
        prefered = self.ascii2d.get_prefered_results(results)
        index = 0
        ptr = 0
        src_hash = self.db.hasher.hash(src_img_path)
        index_out = 0
        select = None
        while True:
            try:
                target = prefered[ptr][index]
                with TemporaryFile() as tmp:
                    with self.ascii2d.request_thumbnail(target) as thumb:
                        self.__iter_write_file(thumb.iter_content(), tmp)
                        target_hash = self.db.hasher.hash(Image.open(tmp))
                        if self.__is_identical(src_hash, target_hash):
                            select = target
                            break
                index += ptr
                ptr = (ptr + 1) % 2
            except IndexError:
                if index_out >= 2:
                    break
                index_out += 1
                continue
        if select is None:
            self.__not_found_handler(src_img_path)
            return
        self.__found_handler(src_img_path, src_hash, select)

    def __found_handler(self, src_img_path:str, src_hash:ImageHash, target: Ascii2dResult):
        match target.origin:
            case Origin.Pixiv:
                self.__pixiv_handler(src_img_path, src_hash, target)
            case Origin.Twitter:
                self.__twitter_handler(src_img_path, src_hash, target)
                
    def __pixiv_handler(self, src_img_path:str, src_hash:ImageHash, target:Ascii2dResult):
        try:
            id = urlparse(target.orig_link).path.split('/')[-1]
            urls = self.pixiv.get_urls(id)
            select = urls.original
            if urls.page > 1:
                select, index = self.__match_pixiv_result(src_hash, urls)
                target.index = index
            self.__finally_handler(select, target)
        except PixivDeletedError:
            self.__deleted_handler(src_img_path, target)

    def __match_pixiv_result(self, target_hash:ImageHash, results:PixivUrls) -> tuple[str, int]:
        select = None
        index = None
        for i in range(results.page):
            with self.pixiv.fetch_image(get_pixiv_page(results.small, i)) as res:
                with TemporaryFile() as tmp:
                    self.__iter_write_file(res.iter_content(chunk_size=self.config.chunk_size), tmp)
                    with Image.open(tmp) as tmp_img:
                        tmp_hash = self.db.hasher.hash(tmp_img)
                        if self.__is_identical(target_hash, tmp_hash):
                            select = get_pixiv_page(results.original, i)
                            index = i
                            break
        return select, index

    def __twitter_handler(self, src_img_path:str, src_hash:ImageHash, target: Ascii2dResult):
        try:
            urls = self.twitter.get_img_url(target.orig_link)
            select, index = self.__match_twitter_result(src_hash ,urls)
            target.index = index
            self.__finally_handler(select.orig, target)
        except TwitterDeletedError:
            self.__deleted_handler(src_img_path, target)

    def __match_twitter_result(self, target_hash:ImageHash, result_urls:list[str]) -> tuple[TwitterUrls, int]:
        select = None
        index = 0
        for result in result_urls:
            with self.__request(result) as res:
                with TemporaryFile() as tmp:
                    self.__iter_write_file(res.iter_content(chunk_size=self.config.chunk_size), tmp)
                    with Image.open(tmp) as tmp_img:
                        tmp_hash = self.db.hasher.hash(tmp_img)
                        if self.__is_identical(target_hash, tmp_hash):
                            select = result
                            break
                        index += 1
        return parse_twitter_url(select), index
    
    def __deleted_handler(self, src_img_path:str, result:Ascii2dResult):
        file_name = self.__get_filename(result)
        file_path = os.path.join(self.config.except_dir, file_name)
        copy(src_img_path, file_path)
    
    def __finally_handler(self, finally_url:str, target:Ascii2dResult):
        file_name = self.__get_filename(target)
        file_path = os.path.join(self.config.dist_dir, file_name)
        req = None
        match target.origin:
            case Origin.Twitter:
                req = self.__request
            case Origin.Pixiv:
                req = self.pixiv.fetch_image
        with req(finally_url) as final:
            with open(os.path.abspath(file_path), 'wb+') as file:
                self.__iter_write_file(final.iter_content(chunk_size=self.config.chunk_size), file)
        self.db.add_img(file_path)

    def __iter_write_file(self, src: Iterator, dist: BufferedRandom):
        for chunk in src:
            if chunk:
                dist.write(chunk)
    
    def __request(self, url:str) -> Response:
        return get(url, headers={'user-agent': self.config.user_agent})

    def __not_found_handler(self, src_img_path: str):
        copy(src_img_path, self.config.not_found_dir)

    def __is_identical(self, src_hash: ImageHash, target_hash:ImageHash) -> bool:
        return self.__get_bias(src_hash, target_hash) <= self.config.threshold
    
    def __get_bias(self, src_hash: ImageHash, target_hash:ImageHash) -> int:
        return src_hash - target_hash

    def get_target_list(self, img_path_list:list[str]):
        splited = split_list(img_path_list, self.config.threads)
        threads = list[Thread]()
        targets = list[str]()
        lck = RLock()

        def get_target_thread(l:list[str]):
            for i in l:
                if not os.path.isdir(i):
                    with Image.open(i) as img:
                        if not self.db.is_img_in_db(self.db.hasher.hash(img)):
                            lck.acquire()
                            targets.append(i)
                            lck.release()
        
        for l in splited:
            t = Thread(target=get_target_thread,args=(l,))
            threads.append(t)
            t.start()
        for t in threads:
            t.join()
        return targets

    def __get_filename(self, target:Ascii2dResult) -> str:
        author_id = None
        parsed_author = urlparse(target.author_link)
        match target.origin:
            case Origin.Twitter:
                author_id = parse_qs(parsed_author.query)['user_id'][0]
            case Origin.Pixiv:
                author_id = parsed_author.path.split('/')[-1]
        d = {
            'origin': target.origin.value,
            'author': target.author,
            'author_id': str(author_id),
            'title': target.title,
            'id': target.id,
            'index': str(target.index)
        }
        fd = FileNameFmt(d)
        return f'{self.config.filename_fmt.format_map(fd)}.{target.extension}'

class SabersortConfig:
    def __init__(self, src_dir:str, dist_dir:str, not_found_dir:str, except_dir:str, filename_fmt: str, threads:int=1, threshold: int = 0, user_agent: str = None, chunk_size:int = 4096) -> None:
        self.src_dir = src_dir
        self.dist_dir = dist_dir
        self.not_found_dir = not_found_dir
        self.except_dir = except_dir
        self.filename_fmt = filename_fmt
        self.threads = threads if threads > 0 else cpu_count()
        self.threshold = threshold
        self.user_agent = user_agent if not user_agent is None else 'Sabersort'
        self.chunk_size = chunk_size

class FileNameFmt(dict):
    def __missing__(self, key):
        return '{%s}'.format(key)
    
    def __getitem__(self, __key):
        r = super().__getitem__(__key)
        if r is None:
            return ''
        return r
    
    def __setitem__(self, __key, __value) -> None:
        if not isinstance(__key, str):
            raise IndexError
        return super().__setitem__(__key, __value)

if __name__ == '__main__':
    config = RawConfigParser()
    config.optionxform = str
    config.read('config.ini')

    sections = config.sections()
    if not os.path.isfile('config.ini'):
        with open('config.ini', 'w+') as cf:
            config.write(cf)
    if not 'sabersort' in sections:
        config['sabersort'] = {'Input directory': '', 'Found directory':'', 'Not found directory':'', 'Exception directory':'', 'Filename': '{origin}-{author_id}-{id}', 'Threshold': '10', 'Thread': '3', 'User-agent': ''}
        with open('config.ini', 'w+') as cf:
            config.write(cf)
    if not 'saberdb' in sections:
        config['saberdb'] = {'Database path': 'saberdb.db', 'Check database': 'True', 'Hash algorithm': 'Perceptual', 'Hash size': '16'}
        with open('config.ini', 'w+') as cf:
            config.write(cf)
    if not 'ascii2d' in sections:
        config['ascii2d'] = {'Prefered origin': 'Pixiv', 'Sort order': 'No', 'First': '0'}
        with open('config.ini', 'w+') as cf:
            config.write(cf)
    if not 'pixiv' in sections:
        config['pixiv'] = {'PHPSESSID': ''}
        with open('config.ini', 'w+') as cf:
            config.write(cf)
    if not 'twitter' in sections:
        config['twitter'] = {'auth_token': ''}
        with open('config.ini', 'w+') as cf:
            config.write(cf)
    
    in_dir = config.get('sabersort', 'Input directory')
    out_dir = config.get('sabersort', 'Found directory')
    nf_dir = config.get('sabersort', 'Not found directory')
    exc_dir = config.get('sabersort', 'Exception directory')
    fmt = config.get('sabersort', 'Filename')
    threshold = int(config.get('sabersort', 'Threshold'))
    threads = int(config.get('sabersort', 'Thread'))
    user_agent = config.get('sabersort', 'User-agent')
    sabersort_cfg = SabersortConfig(in_dir, out_dir, nf_dir, exc_dir, fmt, threads, threshold, user_agent)

    db_path = config.get('saberdb', 'Database path')
    check_db = bool(config.get('saberdb', 'Check database'))
    hash_alg = None
    match config.get('saberdb', 'Hash algorithm').lower():
        case 'perceptual':
            hash_alg = HashAlg.Perceptual
        case 'perceptual_simple':
            hash_alg = HashAlg.PerceptualSimple
        case 'average':
            hash_alg = HashAlg.Average
        case 'difference':
            hash_alg = HashAlg.Difference
        case 'wavelet':
            hash_alg = HashAlg.Wavelet
        case 'hsv':
            hash_alg = HashAlg.HSV    
    hash_size = int(config.get('saberdb', 'Hash size'))
    db_cfg = SaberDBConfig(db_path, check_db, 0)
    hasher = Hasher(hash_alg, hash_size)

    prefered = None
    match config.get('ascii2d', 'Prefered origin').lower():
        case 'pixiv':
            prefered = Origin.Pixiv
        case 'twitter':
            prefered = Origin.Twitter
    sort_order = None
    match config.get('ascii2d', 'Sort order').lower():
        case 'no':
            sort_order = SortOrder.No
        case 'image_size':
            sort_order = SortOrder.ImageSize
        case 'file_size':
            sort_order = SortOrder.FileSize
    first = int(config.get('ascii2d', 'First'))
    ascii2d_cfg = Ascii2dConfig(user_agent, sort_order, first, prefered)

    phpsessid = config.get('pixiv', 'PHPSESSID')
    pixiv_cfg = PixivConfig(phpsessid,user_agent)

    auth_token = config.get('twitter', 'auth_token')
    twitter_cfg = TwitterConfig(auth_token,user_agent)
    
    db = SaberDB(db_cfg,hasher)
    ascii2d = Ascii2d(ascii2d_cfg)
    pixiv = Pixiv(pixiv_cfg)
    twitter = Twitter(twitter_cfg)
    saber = Sabersort(sabersort_cfg, ascii2d, db, pixiv, twitter)
    saber.sort()