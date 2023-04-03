from __future__ import annotations
from dataclasses import dataclass
import threading
from .origin_base import Origin, OriginData, DeletedException
from undetected_chromedriver import Chrome, ChromeOptions
# from selenium.webdriver import Chrome
# from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from io import BufferedRandom
import atexit
from requests import get
from urllib.parse import urlparse, urlunparse, urlencode, parse_qs

CHUNK_SIZE = 4096
NAMES = ['thumb', 'small', 'medium', 'large', 'orig']
BLOCK_XPATH = '/html/body/div[1]/div/div/div[2]/main/div/div/div/div/div/section/div/div/div[1]/div/div/article/div/div/div[3]/div[3]/div/div/div/div/div[2]/div/div[2]'
POST_XPATH = '/html/body/div[1]/div/div/div[2]/main/div/div/div/div/div/section/div/div/div[1]/div/div/article'
POST_IMG_XPATH = '/html/body/div[1]/div/div/div[2]/main/div/div/div/div/div/section/div/div/div[1]/div/div/article/div/div/div[3]//img[contains(@src,"https://pbs.twimg.com/media")]'
POST_INNER = '/html/body/div[1]/div/div/div[2]/main/div/div/div/div/div/section/div/div/div[1]/div/div/article/div/div/div[3]'
DELETED_XPATH = '//a[contains(@href,"/search")]'

class Twitter(Origin):
    def __init__(self, config: TwitterConfig) -> None:
        self.config = config
        # self.__chrome_options = Options()
        # self.__chrome_options.add_argument(f'user-agent={self.config.user_agent}')
        # self.__chrome_options.add_argument('--disable-gpu')
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
        self.drivers[name].get('https://twitter.com')
        self.drivers[name].add_cookie({'name': 'auth_token','value':self.config.auth_token, 'domain': '.twitter.com', 'path': '/', 'secure': True})

    def fetch_data(self, target:str)-> list[str] | None:
        thread = threading.current_thread().name
        if not thread in self.drivers:
            self.__init_chrome(thread)
        driver = self.drivers[thread]
        driver.get(target)
        WebDriverWait(driver ,30).until(EC.presence_of_all_elements_located((By.XPATH, f'{POST_XPATH}|{DELETED_XPATH}')))
        try:
            driver.find_element(By.XPATH, POST_XPATH)
        except NoSuchElementException:
            raise TwitterDeletedException
        WebDriverWait(driver ,10).until(EC.presence_of_element_located((By.XPATH, POST_INNER)))
        try:
            block = driver.find_element(By.XPATH, BLOCK_XPATH)
            block.click()
        finally:
            imgs = driver.find_elements(By.XPATH, POST_IMG_XPATH)

            orig_urls = list[str]()
            thumb_urls = list[str]()
            for e in imgs:
                urls = parse_twitter_url(e.get_attribute('src'))
                orig_urls.append(urls.orig)
                thumb_urls.append(urls.small)
            return OriginData(orig_urls, thumb_urls, len(imgs))
    
    def fetch_img(self, url: str, dist: BufferedRandom):
        with get(url, headers={'user-agent': self.config.user_agent}, stream= True) as res:
            for chunk in res.iter_content(chunk_size=CHUNK_SIZE):
                if chunk:
                    dist.write(chunk)
    
    def __cleanup(self):
        for driver in self.drivers.values():
            driver.quit()

def parse_twitter_url(url:str) -> TwitterUrls:
        parsed = urlparse(url)
        qs = parse_qs(parsed.query)
        queries = {k: v[0] for k, v in qs.items()}
        ext = queries['format']
        urls = list[str]()
        for name in NAMES:
            queries.update({'name': name})
            urls.append(urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, urlencode(queries), parsed.fragment)))
        return TwitterUrls(urls[0],urls[1],urls[2],urls[3],urls[4],ext)

class TwitterDeletedException(DeletedException):
    pass

class TwitterConfig:
    def __init__(self, auth_token:str, user_agent: str) -> None:
        self.auth_token = auth_token
        self.user_agent = user_agent

@dataclass
class TwitterUrls:
    thumb:str
    small: str
    medium:str
    large:str
    orig: str
    ext: str

if __name__ == '__main__':
    pass
