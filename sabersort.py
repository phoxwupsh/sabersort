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
from utils import split_list, async_write_file, async_copyfile, FileNameFmt
from origins.pixiv import Pixiv, PixivConfig
from origins.twitter import Twitter, TwitterConfig
import os.path
from configparser import RawConfigParser
from PIL import Image, UnidentifiedImageError
import aiofiles
import asyncio
import rtoml

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
        queue = self.__get_queue(src_img_list)

        for item in queue:
            await self.__sort_process(item)
    
    async def __sort_process(self, src_path: str):
        ctx = await SaberContext.with_hasher(src_path, self.hasher)
        ctx.results = await self.ascii2d.search(ctx.src_path)
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
        await async_copyfile(ctx.src_path, file_path)
    
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
            await async_write_file(res, file)
        self.db.add_img(self.hasher, file_path)

    async def __not_found_handler(self, ctx: SaberContext):
        await async_copyfile(ctx.src_path, self.config.not_found_dir)

    def __is_identical(self, src_hash: ImageHash, target_hash:ImageHash) -> bool:
        return self.__get_bias(src_hash, target_hash) <= self.config.threshold
    
    def __get_bias(self, src_hash: ImageHash, target_hash:ImageHash) -> int:
        return src_hash - target_hash

    def __get_queue(self, img_path_list:list[str]):
        splited = split_list(img_path_list, self.config.threads)
        threads = list[Thread]()
        targets = list[str]()
        lck = RLock()

        def __queue_thread(l:list[str]) -> list[str]:
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
            t = Thread(target=__queue_thread,args=(l,))
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
    def __init__(self, src_dir:str, dist_dir:str, not_found_dir:str, except_dir:str, filename_fmt: str, threshold: int = 0, user_agent: str = None) -> None:
        self.src_dir = src_dir
        self.dist_dir = dist_dir
        self.not_found_dir = not_found_dir
        self.except_dir = except_dir
        self.filename_fmt = filename_fmt
        self.threads = cpu_count()
        self.threshold = threshold
        self.user_agent = user_agent

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
    
    def is_found(self) -> bool:
        return self.__found
    
    def found(self):
        self.__found = True
    
    def is_deleted(self) -> bool:
        return self.__deleted

    def deleted(self):
        self.__deleted = True

if __name__ == '__main__':
    with open('config.toml', 'r') as c:
        config = rtoml.load(c)
    
    in_dir: str = config['sabersort']['input']
    out_dir: str = config['sabersort']['found']
    nf_dir: str = config['sabersort']['not_found']
    exc_dir: str = config['sabersort']['exception']
    fmt: str = config['sabersort']['filename']
    threshold: int = config['sabersort']['threshold']
    user_agent: str = config['sabersort']['user_agent']
    sabersort_cfg = SabersortConfig(in_dir, out_dir, nf_dir, exc_dir, fmt, threshold, user_agent)

    db_path: str = config['saberdb']['database_path']
    check_db: str = config['saberdb']['check_database']
    db_cfg = SaberDBConfig(db_path, check_db)
    db = SaberDB(db_cfg)

    hash_alg = HashAlg.from_str(config['hasher']['hash_algorithm'])
    hash_size: int = config['hasher']['hash_size']
    hasher = Hasher(hash_alg, hash_size)

    prefered = OriginType.from_str(config['ascii2d']['perfered_origin'])
    sort_order = SortOrder.from_str(config['ascii2d']['sort_order'])
    first: int = config['ascii2d']['first']
    ascii2d_cfg = Ascii2dConfig(user_agent, sort_order, first, prefered)
    ascii2d = Ascii2d(ascii2d_cfg)

    phpsessid: str = config['pixiv']['PHPSESSID']
    pixiv_cfg = PixivConfig(phpsessid,user_agent)
    pixiv = Pixiv(pixiv_cfg)

    auth_token: str = config['twitter']['auth_token']
    twitter_cfg = TwitterConfig(auth_token,user_agent)
    twitter = Twitter(twitter_cfg)
    
    saber = Sabersort(sabersort_cfg, ascii2d, hasher, db, pixiv, twitter)
    
    asyncio.run(saber.sort())