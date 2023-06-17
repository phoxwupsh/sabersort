from __future__ import annotations
from imagehash import ImageHash
from io import BytesIO
from origins import Origin, OriginData, DeletedException
from glob import glob
from utils import async_write_file, async_copyfile, is_identical, format_filename, context_to_record
import os.path
from saber.context import SaberContext
from saberdb import SaberDB
from ascii2d import Ascii2d, OriginType
from hasher import Hasher
from origins.pixiv import Pixiv
from origins.twitter import Twitter
from PIL import Image, UnidentifiedImageError
from hashlib import md5
from multiprocessing import cpu_count
import aiofiles

class Saber():
    def __init__(self, config: SaberConfig, ascii2d: Ascii2d, hasher: Hasher, db: SaberDB, pixiv:Pixiv, twitter:Twitter) -> None:
        self.config = config
        self.ascii2d = ascii2d
        self.hasher = hasher
        self.db = db
        self.pixiv = pixiv
        self.twitter = twitter

    async def sort(self):
        queue = glob(os.path.join(os.path.abspath(self.config.src_dir),'*'))

        for item in queue:
            if os.path.isfile(item):
                await self.__sort_process(item)
    
    async def __sort_process(self, src_path: str):
        async with aiofiles.open(src_path, 'rb') as f:
            buf = await f.read()
            md5_hash = md5()
            md5_hash.update(buf)
            try:
                img = Image.open(BytesIO(buf))
                src_hash = self.hasher.hash(img)
            except UnidentifiedImageError:
                return
        
        ctx = SaberContext(src_path, src_hash, md5_hash.hexdigest())

        in_db, valid = self.db.is_img_in_db_and_valid(ctx)
        if in_db:
            if valid:
                return
            else:
                self.db.delete(ctx.hash)

        ctx.results = await self.ascii2d.search(ctx.src_path, ctx.md5)
        await self.__results_handler(ctx)
        if ctx.is_found():
            await self.__found_handler(ctx)
            if not ctx.is_deleted():
                await self.__finally_handler(ctx)
            else:
                await self.__deleted_handler(ctx)
        else:
            await self.__not_found_handler(ctx)
    
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
                if is_identical(ctx.hash, target_hash, self.config.threshold):
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
        ctx.found(selected)

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
                if is_identical(target_hash, tmp_hash, self.config.threshold):
                    select = i
                    break
        return select
    
    async def __deleted_handler(self, ctx: SaberContext):
        file_name = format_filename(self.config.filename_fmt, ctx.target)
        file_path = os.path.join(self.config.except_dir, file_name)
        await async_copyfile(ctx.src_path, file_path)
    
    async def __finally_handler(self, ctx: SaberContext):
        file_name = format_filename(self.config.filename_fmt, ctx.target)
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
        ctx.dest_path = file_path
        self.db.add(context_to_record(ctx))

    async def __not_found_handler(self, ctx: SaberContext):
        await async_copyfile(ctx.src_path, self.config.not_found_dir)

class SaberConfig:
    def __init__(self, src_dir:str, dist_dir:str, not_found_dir:str, except_dir:str, filename_fmt: str, threshold: int = 0, user_agent: str = None) -> None:
        self.src_dir = src_dir
        self.dist_dir = dist_dir
        self.not_found_dir = not_found_dir
        self.except_dir = except_dir
        self.filename_fmt = filename_fmt
        self.threads = cpu_count()
        self.threshold = threshold
        self.user_agent = user_agent