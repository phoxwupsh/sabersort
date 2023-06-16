from __future__ import annotations
from io import BytesIO
from multiprocessing import cpu_count
from threading import RLock, Thread
from imagehash import ImageHash
from urllib.parse import urlparse, parse_qs
from saberdb import SaberDB, SaberDBConfig
from hasher import Hasher, HashAlg
from ascii2d import Ascii2d, Ascii2dConfig, Ascii2dResult, OriginType, SortOrder
from origins import Origin, OriginData, DeletedException
from glob import glob
from utils import split_list
from origins.pixiv import Pixiv, PixivConfig
from origins.twitter import Twitter, TwitterConfig
import os.path
from configparser import RawConfigParser
from shutil import copy
from PIL import Image, UnidentifiedImageError
from aiofiles.threadpool.binary import AsyncFileIO
import aiofiles
import asyncio

class Sabersort():
    def __init__(self, config:SabersortConfig, ascii2d: Ascii2d, hasher: Hasher, db: SaberDB, pixiv:Pixiv, twitter:Twitter) -> None:
        self.config = config
        self.ascii2d = ascii2d
        self.hasher = hasher
        self.db = db
        self.pixiv = pixiv
        self.twitter = twitter
        if self.db.config.check_db:
            self.db.check_db(self.hasher)

    async def sort(self):
        src_img_list = glob(os.path.join(os.path.abspath(self.config.src_dir),'*'))
        target_img_list = self.get_target_list(src_img_list)

        for item in target_img_list:
            await self.__sort_process(item)
    
    async def __sort_process(self, src_path: str):
        ctx = await SaberContext.with_hasher(src_path, self.hasher)
        await ctx.search(self.ascii2d)
        await self.__results_handler(ctx)
        if ctx.is_found():
            await self.__found_handler(ctx)
            if not ctx.is_deleted():
                await self.__finally_handler(ctx)
            else:
                await self.__deleted_handler(ctx)
        else:
            await self.__not_found_handler()
    
    async def __results_handler(self, ctx: SaberContext):
        prefered = self.ascii2d.get_prefered_results(ctx.results)
        index = 0
        ptr = 0
        index_out = 0
        selected = None
        while True:
            try:
                target = prefered[ptr][index]
                res = await self.ascii2d.fetch_thumbnail(target)
                tmp_img = Image.open(res)
                target_hash = self.hasher.hash(tmp_img)
                if self.__is_identical(ctx.hash, target_hash):
                    selected = target
                    break
                index += ptr
                ptr = (ptr + 1) % 2
            except IndexError:
                if index_out >= 2:
                    break
                index_out += 1
                continue
        if selected is None:
            return
        ctx.target = selected
        ctx.found()

    async def __found_handler(self, ctx: SaberContext):
        origin_handler: Origin = None
        match ctx.target.origin:
            case OriginType.Pixiv:
                origin_handler = self.pixiv
            case OriginType.Twitter:
                origin_handler = self.twitter
        try:
            origin_data = await origin_handler.fetch_data(ctx.target.orig_link)
            select = await self.__match_origin_variant(origin_handler, ctx.hash, origin_data)
            ctx.dest_url = origin_data.original[select]
        except DeletedException:
            ctx.deleted()

    
    async def __match_origin_variant(self, origin_handler: Origin, target_hash: ImageHash, origin_data: OriginData) -> int:
        select = None
        for i in range(origin_data.variant):
            res = await origin_handler.fetch_img(origin_data.thumb[i])
            with Image.open(res) as tmp_img:
                tmp_hash = self.hasher.hash(tmp_img)
                if self.__is_identical(target_hash, tmp_hash):
                    select = i
                    break
        return select
    
    async def __deleted_handler(self, ctx: SaberContext):
        file_name = self.__get_filename(ctx.target)
        file_path = os.path.join(self.config.except_dir, file_name)
        await asyncio.to_thread(copy(ctx.src_path, file_path))
    
    async def __finally_handler(self, ctx: SaberContext):
        file_name = self.__get_filename(ctx.target)
        file_path = os.path.join(self.config.dist_dir, file_name)
        origin_handler = None
        match ctx.target.origin:
            case OriginType.Twitter:
                origin_handler = self.twitter
            case OriginType.Pixiv:
                origin_handler = self.pixiv
        async with aiofiles.open(os.path.abspath(file_path), 'wb+') as file:
            res = await origin_handler.fetch_img(ctx.dest_url)
            await self.__iter_write_file(res, file)
        self.db.add_img(self.hasher, file_path)

    async def __iter_write_file(self, src: BytesIO, dist: AsyncFileIO):
        while True:
            chunk = src.read(4096)
            if not chunk:
                break
            await dist.write(chunk)

    async def __not_found_handler(self, ctx: SaberContext):
        await asyncio.to_thread(copy(ctx.src_path, self.config.not_found_dir))

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
                    try:
                        with Image.open(i) as img:
                            if not self.db.is_img_in_db(self.hasher.hash(img)):
                                lck.acquire()
                                targets.append(i)
                                lck.release()
                    except UnidentifiedImageError:
                        pass
        
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
            case OriginType.Twitter:
                author_id = parse_qs(parsed_author.query)['user_id'][0]
            case OriginType.Pixiv:
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
    def __init__(self, src_dir:str, dist_dir:str, not_found_dir:str, except_dir:str, filename_fmt: str, threshold: int = 0, user_agent: str = None, chunk_size:int = 4096) -> None:
        self.src_dir = src_dir
        self.dist_dir = dist_dir
        self.not_found_dir = not_found_dir
        self.except_dir = except_dir
        self.filename_fmt = filename_fmt
        self.threads = cpu_count()
        self.threshold = threshold
        self.user_agent = user_agent if not user_agent is None else 'Sabersort'
        self.chunk_size = chunk_size

class SaberContext:
    def __init__(self, src_path: str) -> None:
        self.src_path: str = src_path
        self.hash: ImageHash = None
        self.target: Ascii2dResult = None
        self.results: list[Ascii2dResult] = None
        self.dest_url: str = None
        self.__found = False
        self.__deleted = False
    
    @classmethod
    async def with_hasher(cls, src_path: str, hasher: Hasher):
        self = cls(src_path)
        async with aiofiles.open(self.src_path, "rb") as file:
            buf = await file.read()
            img = Image.open(BytesIO(buf))
            self.hash = hasher.hash(img)
            return self
    
    async def search(self, searcher: Ascii2d):
        res = await searcher.search(self.src_path)
        self.results = res
    
    def is_found(self) -> bool:
        return self.__found
    
    def found(self):
        self.__found = True
    
    def is_deleted(self) -> bool:
        return self.__deleted

    def deleted(self):
        self.__deleted = True

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
        config['sabersort'] = {'Input directory': '', 'Found directory':'', 'Not found directory':'', 'Exception directory':'', 'Filename': '{origin}-{author_id}-{id}', 'Threshold': '10', 'User-agent': ''}
        with open('config.ini', 'w+') as cf:
            config.write(cf)
    if not 'saberdb' in sections:
        config['saberdb'] = {'Database path': 'saberdb.db', 'Check database': 'True'}
        with open('config.ini', 'w+') as cf:
            config.write(cf)
    if not 'hasher' in sections:
        config['hasher'] = {'Hash algorithm': 'Perceptual', 'Hash size': '16'}
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
    user_agent = config.get('sabersort', 'User-agent')
    sabersort_cfg = SabersortConfig(in_dir, out_dir, nf_dir, exc_dir, fmt, threshold, user_agent)

    db_path = config.get('saberdb', 'Database path')
    check_db = bool(config.get('saberdb', 'Check database'))
    db_cfg = SaberDBConfig(db_path, check_db, 0)
    db = SaberDB(db_cfg)

    hash_alg = None
    match config.get('hasher', 'Hash algorithm').lower():
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
    hash_size = int(config.get('hasher', 'Hash size'))
    hasher = Hasher(hash_alg, hash_size)

    prefered = None
    match config.get('ascii2d', 'Prefered origin').lower():
        case 'pixiv':
            prefered = OriginType.Pixiv
        case 'twitter':
            prefered = OriginType.Twitter
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
    
    ascii2d = Ascii2d(ascii2d_cfg)
    pixiv = Pixiv(pixiv_cfg)
    twitter = Twitter(twitter_cfg)
    saber = Sabersort(sabersort_cfg, ascii2d, hasher, db, pixiv, twitter)
    
    asyncio.run(saber.sort())