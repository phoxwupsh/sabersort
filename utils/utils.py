from aiofiles.threadpool.binary import AsyncFileIO
import aiofiles
from io import BytesIO

def split_list(l:list, n:int) -> list[list]:
    k, m = divmod(len(l), n)
    return (l[i*k+min(i, m):(i+1)*k+min(i+1, m)] for i in range(n))


async def async_copyfile(src: str, dst: str, chunk_size: int=4096):
    async with aiofiles.open(src, "rb") as r:
        async with aiofiles.open(dst, "wb+") as w:
            await async_copyfileobj(r, w)

async def async_copyfileobj(async_fsrc: AsyncFileIO, async_fdst: AsyncFileIO, *, chunk_size: int=4096):
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