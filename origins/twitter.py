from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

import asyncio_atexit
from aiohttp import ClientSession
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver import Chrome, ChromeOptions
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

from origins import DeletedException, Origin, OriginData

NAMES = ['thumb', 'small', 'medium', 'large', 'orig']
BLOCK_XPATH = '/html/body/div[1]/div/div/div[2]/main/div/div/div/div/div/section/div/div/div[1]/div/div/article/div/div/div[3]/div[3]/div/div/div/div/div[2]/div/div[2]'
POST_XPATH = '/html/body/div[1]/div/div/div[2]/main/div/div/div/div/div/section/div/div/div[1]/div/div/article'
POST_IMG_XPATH = '/html/body/div[1]/div/div/div[2]/main/div/div/div/div/div/section/div/div/div[1]/div/div/article/div/div/div[3]//img[contains(@src,"https://pbs.twimg.com/media")]'
POST_INNER = '/html/body/div[1]/div/div/div[2]/main/div/div/div/div/div/section/div/div/div[1]/div/div/article/div/div/div[3]'
DELETED_XPATH = '//a[contains(@href,"/search")]'


class Twitter(Origin):
    def __init__(self, config: TwitterConfig) -> None:
        self.config = config
        self.__session = None
        self.__driver_manager = ChromeDriverManager()
        self.__driver = None

    def __get_driver(self) -> WebDriver:
        if self.__driver is None:
            driver_path = self.__driver_manager.install()
            options = ChromeOptions()
            options.add_argument('--disable-gpu')
            options.add_argument('--blink-settings=imagesEnabled=false')
            options.add_argument('--disable-blink-features=automationcontrolled')
            if self.config.headless:
                options.add_argument('--headless')
                options.add_argument(f'--user-agent={self.config.user_agent}')

            service = Service(driver_path)
            caps = DesiredCapabilities().CHROME
            caps['pageLoadStrategy'] = 'eager'

            self.__driver = Chrome(service=service, desired_capabilities=caps, options=options)
            self.__driver.get('https://twitter.com')
            self.__driver.add_cookie(
                {
                    'name': 'auth_token',
                    'value': self.config.auth_token,
                    'domain': '.twitter.com',
                    'path': '/',
                    'secure': True,
                }
            )
        return self.__driver

    async def __get_session(self) -> ClientSession:
        if self.__session is None:
            self.__session = ClientSession()
            if self.config.user_agent is not None:
                self.__session.headers.update({'user-agent': self.config.user_agent})
        asyncio_atexit.register(self.__cleanup)
        return self.__session

    async def fetch_data(self, target: str) -> OriginData:
        driver = self.__get_driver()
        driver.get(target)
        WebDriverWait(driver, 30).until(
            EC.presence_of_all_elements_located((By.XPATH, f'{POST_XPATH}|{DELETED_XPATH}'))
        )
        try:
            driver.find_element(By.XPATH, POST_XPATH)
        except NoSuchElementException:
            raise TwitterDeletedException
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, POST_INNER)))
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

    async def fetch_img(self, url: str):
        session = await self.__get_session()
        async with session.get(url) as res:
            buf = await res.content.read()
            return BytesIO(buf)

    async def __cleanup(self):
        if self.__session is not None:
            await self.__session.close()
        if self.__driver is not None:
            self.__driver.quit()


def parse_twitter_url(url: str) -> TwitterUrls:
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    queries = {k: v[0] for k, v in qs.items()}
    ext = queries['format']
    urls = list[str]()
    for name in NAMES:
        queries.update({'name': name})
        urls.append(
            urlunparse(
                (
                    parsed.scheme,
                    parsed.netloc,
                    parsed.path,
                    parsed.params,
                    urlencode(queries),
                    parsed.fragment,
                )
            )
        )
    return TwitterUrls(urls[0], urls[1], urls[2], urls[3], urls[4], ext)


class TwitterDeletedException(DeletedException):
    pass


class TwitterConfig:
    def __init__(self, auth_token: str, user_agent: str, headless: bool = True) -> None:
        self.auth_token = auth_token
        self.user_agent = user_agent
        self.headless = headless


@dataclass
class TwitterUrls:
    thumb: str
    small: str
    medium: str
    large: str
    orig: str
    ext: str
