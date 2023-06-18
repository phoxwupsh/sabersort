from io import BytesIO
from typing import Any

import aiofiles
from aiofiles.threadpool.binary import AsyncFileIO
from imagehash import ImageHash


def split_list(list_: list[Any], n: int) -> list[list]:
    k, m = divmod(len(list_), n)
    return [list_[i * k + min(i, m) : (i + 1) * k + min(i + 1, m)] for i in range(n)]


async def async_copyfile(src: str, dst: str, chunk_size: int = 4096):
    async with aiofiles.open(src, 'rb') as r:
        async with aiofiles.open(dst, 'wb+') as w:
            await async_copyfileobj(r, w, chunk_size)


async def async_copyfileobj(
    async_fsrc: AsyncFileIO, async_fdst: AsyncFileIO, chunk_size: int = 4096
):
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


def is_identical(hash_1: ImageHash, hash_2: ImageHash, threshold: int = 0) -> bool:
    return get_bias(hash_1, hash_2) <= threshold


def get_bias(hash_1: ImageHash, hash_2: ImageHash) -> int:
    return abs(hash_1 - hash_2)
