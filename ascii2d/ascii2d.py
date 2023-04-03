from __future__ import annotations
from dataclasses import dataclass
from urllib.parse import urlparse
from requests import session
from hashlib import md5
from bs4 import BeautifulSoup
from bs4.element import Tag
from enum import Enum
import threading
import atexit

from undetected_chromedriver import Chrome, ChromeOptions

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

class Ascii2d():
    def __init__(self, config: Ascii2dConfig) -> None:
        self.config = config
        self.session = session()
        if not self.config.user_agent is None:
            self.session.headers.update({'user-agent':self.config.user_agent})

        self.__driver_manager = ChromeDriverManager()
        self.__driver_path = self.__driver_manager.install()
        self.__chrome_service = Service(self.__driver_path)
        self.__chrome_caps = DesiredCapabilities().CHROME
        self.__chrome_caps["pageLoadStrategy"] = "eager"
        self.drivers = dict[str, Chrome]()
        atexit.register(self.__cleanup)
    
    def __init_chrome(self, name:str):
        options = ChromeOptions() 
        # options.add_argument('--headless') # it seems like undetected_chromedriver can't run under headless mode
        options.add_argument('--disable-gpu')
        self.drivers[name] = Chrome(service=self.__chrome_service, desired_capabilities=self.__chrome_caps, options=options)
    
    def search(self, img_path:str) -> list[Ascii2dResult]:
        result_md5 = self.search_md5(img_path)
        if len(result_md5) > 0:
            return result_md5
        return self.search_file(img_path)

    def search_md5(self, img_path:str) -> list[Ascii2dResult]:
        thread = threading.current_thread().name
        if not thread in self.drivers:
            self.__init_chrome(thread)
        driver = self.drivers[thread]
        driver.get(f'https://ascii2d.net/search/color/{get_md5(img_path)}')
        WebDriverWait(driver ,30).until(EC.presence_of_all_elements_located((By.CLASS_NAME, 'container')))
        results = self.__parse_asii2d_soup(BeautifulSoup(driver.page_source, 'lxml'))
        return results
    
    def search_file(self, img_path:str) -> list[Ascii2dResult]:
        thread = threading.current_thread().name
        if not thread in self.drivers:
            self.__init_chrome(thread)
        driver = self.drivers[thread]
        driver.get('https://ascii2d.net/')
        WebDriverWait(driver ,30).until(EC.presence_of_all_elements_located((By.XPATH, '/html/body/div/div/form[1]/input[2]')))
        upload = driver.find_element(By.NAME, 'file')
        upload.send_keys(img_path)
        btn = driver.find_element(By.XPATH, '/html/body/div/div/form[2]/div/div[3]/button')
        btn.click()
        WebDriverWait(driver ,30).until(EC.presence_of_all_elements_located((By.CLASS_NAME, 'container')))
        results = self.__parse_asii2d_soup(BeautifulSoup(driver.page_source, 'lxml'))
        return results
    
    def request_thumbnail(self, target:Ascii2dResult):
        return self.session.get(f'https://ascii2d.net/{target.thumbnail_link}')

    def __parse_asii2d_soup(self, soup: BeautifulSoup) -> list[Ascii2dResult]:
        rs = soup.find_all(attrs={'class':'item-box'})
        results = list[Ascii2dResult]()
        for r in rs:
            parsed = parse_ascii2d_result(r)
            if not parsed.origin == None:
                results.append(parsed)
        if len(results) > self.config.first and self.config.first > 0:
            results = results[:self.config.first]
        self.__sort_result(results)
        return results

    def __sort_result(self, results: list[Ascii2dResult]):
        match self.config.sort_order:
            case SortOrder.No:
                return
            case SortOrder.FileSize:
                results.sort(key=lambda r: r.file_size, reverse=True)
            case SortOrder.ImageSize:
                results.sort(key=lambda r: r.image_size, reverse=True)
    
    def get_prefered_results(self, results: list[Ascii2dResult]) -> tuple[list[Ascii2dResult], list[Ascii2dResult]]:
        pref = [r for r in results if r.origin == self.config.prefered]
        non_pref = [r for r in results if not r.origin == self.config.prefered]
        return pref, non_pref
    
    def __cleanup(self):
        for driver in self.drivers.values():
            driver.quit()
        

def get_md5(img_path: str, chunk_size: int = 1024) -> str:
    with open(img_path, 'rb') as img:
        h = md5()
        c = img.read(chunk_size)
        while c:
            h.update(c)
            c = img.read(chunk_size)
        return h.hexdigest()

def parse_ascii2d_result(item_box:Tag) -> Ascii2dResult:
    md5_e = item_box.find_next(attrs={'class': 'hash'})
    info  = md5_e.find_next('small').decode_contents().split(' ')
    size = info[0]
    detail_box = item_box.find_next(attrs={'class': 'detail-box'})
    link = detail_box.find_next('a')
    origin = parse_origin(detail_box.find_next('img').get(key='alt'))
    author_e = link.find_next('a')

    thumbnail_link = item_box.find_next(attrs={'class': 'image-box'}).find_next('img').get(key='src')
    md5_hash = md5_e.decode_contents()
    width = int(size.split('x')[0])
    height = int(size.split('x')[1])
    extension = info[1].lower()
    if extension == 'jpeg':
        extension = 'jpg'
    file_size = float(info[2].split('KB')[0])
    image_size = width*height

    orig_link = link['href']
    title = link.decode_contents()
    author = author_e.decode_contents()
    author_link = author_e['href']
    id = urlparse(str(orig_link)).path.split('/')[-1]
    return Ascii2dResult(thumbnail_link,md5_hash,width,height,extension,file_size,image_size,origin,orig_link,title,author,author_link,None,id)


def parse_origin(origin: str) -> OriginType:
    match origin.lower():
        case "twitter":
            return OriginType.Twitter
        case "pixiv":
            return OriginType.Pixiv
        case "niconico":
            return OriginType.Niconico
        case "fanbox":
            return OriginType.Fanbox

class OriginType(Enum):
    Twitter = 'twitter'
    Pixiv = 'pixiv'
    Niconico = 'niconico'
    Fanbox = 'fanbox'

class SortOrder(Enum):
    No = 0
    ImageSize = 1
    FileSize =2

class Ascii2dConfig:
    def __init__(self, user_agent: str = None, sort_order: SortOrder = SortOrder.No, first: int = 0, prefered: OriginType = OriginType.Pixiv) -> None:
        self.user_agent = user_agent
        self.sort_order = sort_order
        self.first = first
        self.prefered = prefered


@dataclass
class Ascii2dResult:
    thumbnail_link:str
    md5:str
    width:int
    height:int
    extension:str
    file_size:float
    image_size:int
    origin:OriginType
    orig_link:str
    title:str
    author:str
    author_link:str
    index: int
    id: str

if __name__ == "__main__":
    pass
    

