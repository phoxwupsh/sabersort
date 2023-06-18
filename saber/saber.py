from __future__ import annotations

import os.path
from glob import glob
from hashlib import md5
from io import BytesIO
from multiprocessing import cpu_count
from os import stat

import aiofiles
from imagehash import ImageHash, ImageMultiHash
from PIL import Image, UnidentifiedImageError

from ascii2d import Ascii2d, Ascii2dResult, OriginType
from hasher import Hasher
from origins import DeletedException, Origin, OriginData
from origins.pixiv import Pixiv
from origins.twitter import Twitter
from saber.context import SaberContext
from saberdb import SaberDB
from saberdb.model import SaberRecord
from utils import async_copyfile, async_write_file, is_identical


class Saber:
    def __init__(
        self,
        config: SaberConfig,
        ascii2d: Ascii2d,
        hasher: Hasher,
        db: SaberDB,
        pixiv: Pixiv,
        twitter: Twitter,
    ) -> None:
        self.config = config
        self.ascii2d = ascii2d
        self.hasher = hasher
        self.db = db
        self.pixiv = pixiv
        self.twitter = twitter

    async def sort(self):
        queue = glob(os.path.join(os.path.abspath(self.config.src_dir), '*'))

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

        in_db, valid = self.db.is_img_in_db_and_valid(ctx.hash)
        if in_db:
            if valid:
                return
            else:
                self.db.delete(ctx.hash)

        ctx.results = await self.ascii2d.search(ctx.src_path, ctx.md5)
        try:
            await self.__match_results(ctx)
            await self.__match_varaint(ctx)
            await self.__finally_handler(ctx)
        except NoMatchResultException:
            await self.__not_found_handler(ctx)
            print('no result match')
        except NoMatchVariantException:
            await self.__deleted_handler(ctx)
            print('no varaint match')
        except DeletedException:
            await self.__deleted_handler(ctx)
            print('deleted')

    async def __match_results(self, ctx: SaberContext):
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
            except (IndexError, UnidentifiedImageError):
                if index_out >= 2:
                    break
                index_out += 1
                continue
        if selected is None:
            raise NoMatchResultException
        ctx.target = selected

    async def __match_varaint(self, ctx: SaberContext):
        origin_handler: Origin = None
        match ctx.target.origin:
            case OriginType.Pixiv:
                origin_handler = self.pixiv
            case OriginType.Twitter:
                origin_handler = self.twitter
        if origin_handler is None:
            raise NotSupportOriginException
        origin_data = await origin_handler.fetch_data(ctx.target.orig_link)
        select = await self.__match_origin_variant(origin_handler, ctx.hash, origin_data)
        ctx.dest_url = origin_data.original[select]

    async def __match_origin_variant(
        self,
        origin_handler: Origin,
        target_hash: ImageHash | ImageMultiHash,
        origin_data: OriginData,
    ) -> int:
        select = None
        for i in range(origin_data.variant):
            res = await origin_handler.fetch_img(origin_data.thumb[i])
            with Image.open(res) as tmp_img:
                tmp_hash = self.hasher.hash(tmp_img)
                if is_identical(target_hash, tmp_hash, self.config.threshold):
                    select = i
                    break
        if select is not None:
            return select
        raise NoMatchVariantException

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
        dst_path = os.path.join(self.config.not_found_dir, os.path.basename(ctx.src_path))
        await async_copyfile(ctx.src_path, dst_path)


class SaberConfig:
    def __init__(
        self,
        src_dir: str,
        dist_dir: str,
        not_found_dir: str,
        except_dir: str,
        filename_fmt: str,
        threshold: int = 0,
        user_agent: str = None,
    ) -> None:
        self.src_dir = src_dir
        self.dist_dir = dist_dir
        self.not_found_dir = not_found_dir
        self.except_dir = except_dir
        self.filename_fmt = filename_fmt
        self.threads = cpu_count()
        self.threshold = threshold
        self.user_agent = user_agent


def context_to_record(ctx: SaberContext) -> SaberRecord:
    return SaberRecord(
        str(ctx.hash),
        ctx.target.author,
        ctx.target.author_id,
        ctx.target.author_link,
        ctx.target.width,
        ctx.target.height,
        ctx.target.orig_link,
        ctx.dest_path,
        stat(ctx.dest_path).st_size,
    )


def format_filename(filename_fmt: str, target: Ascii2dResult) -> str:
    d = {
        'origin': target.origin.value,
        'author': target.author,
        'author_id': target.author_id,
        'title': target.title,
        'id': target.id,
        'index': str(target.index),
    }
    return f'{filename_fmt.format_map(d)}.{target.extension}'


class NoMatchResultException(BaseException):
    pass


class NoMatchVariantException(BaseException):
    pass


class NotSupportOriginException(BaseException):
    pass
