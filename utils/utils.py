from aiofiles.threadpool.binary import AsyncFileIO
import aiofiles
from imagehash import ImageHash
from io import BytesIO
from ascii2d import Ascii2dResult
from saber.context import SaberContext
from saberdb.model import SaberRecord
from os import stat

def split_list(l:list, n:int) -> list[list]:
    k, m = divmod(len(l), n)
    return [l[i*k+min(i, m):(i+1)*k+min(i+1, m)] for i in range(n)]


async def async_copyfile(src: str, dst: str, chunk_size: int=4096):
    async with aiofiles.open(src, "rb") as r:
        async with aiofiles.open(dst, "wb+") as w:
            await async_copyfileobj(r, w, chunk_size)

async def async_copyfileobj(async_fsrc: AsyncFileIO, async_fdst: AsyncFileIO, chunk_size: int=4096):
    while True:
        chunk = await async_fsrc.read(chunk_size)
        if not chunk:
            break
        await async_fdst.write(chunk)

async def async_write_file(src: BytesIO, dist: AsyncFileIO):
    while True:
        chunk = src.read(4096)
        if not chunk:
            break
        await dist.write(chunk)

def is_identical(hash_1: ImageHash, hash_2:ImageHash, threshold: int=0) -> bool:
    return get_bias(hash_1, hash_2) <= threshold

def get_bias(hash_1: ImageHash, hash_2:ImageHash) -> int:
    return abs(hash_1 - hash_2)

class FileNameFmt(dict):
    def __missing__(self, key):
        return f"{key}"
    
    def __getitem__(self, __key):
        r = super().__getitem__(__key)
        return "" if r is None else r
    
    def __setitem__(self, __key, __value) -> None:
        if not isinstance(__key, str):
            raise IndexError
        return super().__setitem__(__key, __value)

def format_filename(filename_fmt: str, target:Ascii2dResult) -> str:
        d = {
            'origin': target.origin.value,
            'author': target.author,
            'author_id': target.author_id,
            'title': target.title,
            'id': target.id,
            'index': str(target.index)
        }
        fd = FileNameFmt(d)
        return f'{filename_fmt.format_map(fd)}.{target.extension}'

def context_to_record(ctx: SaberContext) -> SaberRecord:
    return SaberRecord(
        str(ctx.hash),
        ctx.author,
        ctx.author_id,
        ctx.author_link,
        ctx.width,
        ctx.height,
        ctx.orig_link,
        ctx.dest_path,
        stat(ctx.dest_path).st_size
    )
        