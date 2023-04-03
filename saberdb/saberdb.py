from __future__ import annotations
from dataclasses import dataclass
from genericpath import isfile
from sqlite3 import connect, Error
from hasher import Hasher
from utils import split_list
from PIL import Image
from os import stat
from threading import Thread, RLock
from multiprocessing import cpu_count

class SaberDB():
    def __init__(self, config: SaberDBConfig) -> None:
        self.config = config
        self.lock = RLock()
        self.conn = None
        self.cur = None
        try:
            self.conn = connect(self.config.db_path,check_same_thread=False)
            self.cur = self.conn.cursor()
        except Error as e:
            print(e)
        self.cur.execute('CREATE TABLE IF NOT EXISTS `saberdb` (hash text PRIMARY KEY, width integer, height integer, size integer, path text);')
    
    def is_img_in_db(self, img_hash: str) -> bool:
        self.lock.acquire()
        self.cur.execute(f'SELECT hash FROM `saberdb` WHERE hash="{img_hash}"')
        self.lock.release()
        return not self.cur.fetchone() is None
    
    def is_img_valid(self, hasher: Hasher, img_hash: str, img_path: str) -> bool:
        if not isfile(img_path):
            return False
        with Image.open(img_path) as target_img:
            target_hash = hasher.hash(target_img)
            return img_hash == str(target_hash)
    
    def add_img(self, hasher: Hasher, img_path:str):
        with Image.open(img_path) as img:
            img_hash = hasher.hash(img)
            self.cur.execute(f'INSERT INTO `saberdb` VALUES("{str(img_hash)}", {img.width}, {img.height}, {stat(img_path).st_size}, "{img_path}")')
            try:
                self.lock.acquire()
                self.conn.commit()
            finally:
                self.lock.release()
    
    def get_img(self, img_hash: str) -> ImageEntry | None:
        self.cur.execute(f'SELECT hash, width, height, size, path FROM `saberdb` WHERE hash="{img_hash}"')
        result = self.cur.fetchone()
        if result is None:
            return None
        return ImageEntry(result[0],result[1],result[2],result[3],result[4])
    
    def del_img(self, img_hash: str):
        self.lock.acquire()
        self.cur.execute(f'DELETE FROM `saberdb` WHERE hash="{img_hash}"')
        self.conn.commit()
        self.lock.release()
    
    def check_db(self, hasher: Hasher):
        threads = list[Thread]()
        
        def check_db_thread(check_list:list):
            for img in check_list:
                img_hash = img[0]
                img_path = img[1]
                if not self.is_img_valid(hasher, img_hash, img_path):
                    self.lock.acquire()
                    self.del_img(img_hash)
                    self.lock.release()

        self.cur.execute('SELECT hash, path FROM `saberdb`')
        check_list = self.cur.fetchall()
        for l in split_list(check_list, self.config.threads):
            t = Thread(target=check_db_thread, args=(l,))
            threads.append(t)
            t.start()
        for t in threads:
            t.join()
    
@dataclass
class ImageEntry:
    hash: str
    width: int
    height: int
    size: int
    path: str

class SaberDBConfig:
    def __init__(self, db_path: str = 'saberdb.db', check_db:bool=False, threads: int = 0) -> None:
        self.db_path = db_path
        self.check_db = check_db
        self.threads = threads if threads > 0 else cpu_count()

if __name__ == "__main__":
    pass