from __future__ import annotations
from selenium import webdriver
from selenium.webdriver.chrome import options
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions, wait
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
import requests
import logging

WINDOW_WIDTH = 1920
WINDOW_HEIGHT = 1080
BLOCK_TIMEOUT = 3
TIMEOUT = 5

DELETED_XPATH = '/html/body/div/div/div/div[2]/main/div/div/div/div/div/div[2]/div/div/div/div/div/a' # a element
IMAGE_XPATH = '//img[contains(@src,"https://pbs.twimg.com/media")]' # img element
BLOCKED_XPATH = '/html/body/div/div/div/div[2]/main/div/div/div/div/div/div[2]/div/section/div/div/div[1]/div/div/article/div/div/div/div[3]/div[2]/div/div/div/div[2]/article/div/div/div/div/div/div[2]/div/div[2]/div/div/span/span' # span element

class Twitter:
    def __init__(self, twittersetting:TwitterSetting, logger:logging.Logger=logging.getLogger('twitter')) -> None:

        self.setting = twittersetting
        self.logger = logger
        self.session = requests.session()
        self.session.headers = {'user-agent': self.setting.user_agent}
        
        self.driver_path = self.setting.driver_path

        self.chrome_options = options.Options()
        if self.setting.silent:
            self.chrome_options.add_argument('--headless')
        self.chrome_options.add_argument('--disable-extensions')
        self.chrome_options.add_argument('--window-size={},{}'.format(str(WINDOW_WIDTH),str(WINDOW_HEIGHT)))
        self.chrome_options.add_experimental_option('excludeSwitches', ['enable-logging']) # disable selenium output

        # self.driver_path = webdriver.Chrome(driver_path, chrome_options=chrome_options)
    
    def get_image_urls(self, url:str) -> list():
        def wait_for_image(driver:webdriver.Chrome) -> list:
            url_list = list()
            try:
                e = WebDriverWait(driver, timeout=TIMEOUT).until(expected_conditions.presence_of_all_elements_located((By.XPATH, '{}|{}|{}'.format(BLOCKED_XPATH, IMAGE_XPATH, DELETED_XPATH))))
                if isinstance(e, list):
                    for i in e:
                        if isinstance(i, WebElement) and i.tag_name == 'img': # this element is image
                            url_list.append(i.get_attribute('src'))
                        if isinstance(i, WebElement) and i.tag_name == 'span': # this element is the show button
                            i.click()
                            url_list = wait_for_image(driver)
                        if isinstance(i, WebElement) and i.tag_name == 'a': # deleted post
                            self.logger.info('"{}" has been deleted.'.format(url))
                            break
                    return url_list
                elif isinstance(e, WebElement):
                    url_list.append(e.get_attribute('src'))
                    return url_list
            except TimeoutException:
                self.logger.error('Time out for fetching "{}"'.format(url))
            finally:
                return url_list
        
        driver = webdriver.Chrome(self.driver_path, options=self.chrome_options)
        driver.get(url)
        img_urls = wait_for_image(driver)

        return img_urls
    
    def get_image(self, url:str, path:str=None):
        with self.session.get(url, stream=True) as r:
            fn = '{}.{}'.format(url.split('/')[-1].split('?')[0], url.split('?')[-1].split('&')[0].split('=')[-1]) if path is None else path
            with open(fn, 'wb+') as f:
                for c in r.iter_content(chunk_size=4096):
                    if c:
                        f.write(c)

class TwitterSetting:
    def __init__(self, driver_path:str, user_agent:str, silent:bool=True) -> None:
        self.driver_path = driver_path
        self.user_agent = user_agent
        self.silent = silent
        pass


def get_original_image_url(url:str):
    if 'https://pbs.twimg.com' in url:
        if not url.split('name=')[-1] == 'orig':
            return url.split('name=')[0] + 'name=orig'

if __name__ == '__main__':
    pass