from __future__ import annotations
from dataclasses import dataclass
import threading
from selenium.webdriver import Chrome
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from urllib.parse import urlparse, urlunparse, urlencode, parse_qs

NAMES = ['thumb', 'small', 'medium', 'large', 'orig']
BLOCK_XPATH = '/html/body/div[1]/div/div/div[2]/main/div/div/div/div/div/section/div/div/div[1]/div/div/div[1]/article/div/div/div/div[3]/div[3]/div/div/div/div/div/div/div/div/div/div/div/div[2]/div/div[2]/div'
POST_XPATH = '/html/body/div[1]/div/div/div[2]/main/div/div/div/div/div/section/div/div/div[1]/div/div/div[1]/article/div/div/div/div[3]'
POST_IMG_XPATH = '/html/body/div[1]/div/div/div[2]/main/div/div/div/div/div/section/div/div/div[1]/div/div/div[1]/article/div/div/div/div[3]//img[contains(@src,"https://pbs.twimg.com/media")]'
POST_INNER = '/html/body/div[1]/div/div/div[2]/main/div/div/div/div/div/section/div/div/div[1]/div/div/div[1]/article/div/div/div/div[3]/div[3]'
DELETED_XPATH = '//a[contains(@href,"/search")]'

class Twitter:
    def __init__(self, config: TwitterConfig) -> None:
        self.config = config
        self.__chrome_options = Options() 
        self.__chrome_options.add_argument(f'user-agent={self.config.user_agent}')
        self.__chrome_options.add_argument('--headless')
        self.__chrome_options.add_argument('--disable-gpu')
        self.__driver_manager = ChromeDriverManager()
        self.__driver_path = self.__driver_manager.install()
        self.__chrome_service = Service(self.__driver_path)
        self.__chrome_caps = DesiredCapabilities().CHROME
        self.__chrome_caps["pageLoadStrategy"] = "eager"
        self.drivers = dict[str, Chrome]()

    def __init_chrome(self, name:str):
        self.drivers[name] = Chrome(service=self.__chrome_service, desired_capabilities=self.__chrome_caps, options=self.__chrome_options)
        self.drivers[name].get('https://twitter.com')
        self.drivers[name].add_cookie({'name': 'auth_token','value':self.config.auth_token, 'domain': '.twitter.com', 'path': '/', 'secure': True})

    def get_img_url(self, target:str)-> list[str] | None:
        thread = threading.current_thread().name
        if not thread in self.drivers:
            self.__init_chrome(thread)
        driver = self.drivers[thread]
        driver.get(target)
        WebDriverWait(driver ,30).until(EC.presence_of_all_elements_located((By.XPATH, f'{POST_XPATH}|{DELETED_XPATH}')))
        try:
            driver.find_element(By.XPATH, POST_XPATH)
        except NoSuchElementException:
            raise TwitterDeletedError
        WebDriverWait(driver ,10).until(EC.presence_of_element_located((By.XPATH, POST_INNER)))
        try:
            block = driver.find_element(By.XPATH, BLOCK_XPATH)
            block.click()
        finally:
            imgs = driver.find_elements(By.XPATH, POST_IMG_XPATH)
            return [e.get_attribute('src') for e in imgs]

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

class TwitterDeletedError(Exception):
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
