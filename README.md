# Sabersort

## 這是做甚麼用的？

Sabersort會將你所輸入的資料夾中的圖片，逐個使用[二次元画像詳細検索(https://ascii2d.net)](https://ascii2d.net/)進行以圖片搜尋，如果有找到跟該圖片相同的圖片時，會自動將該圖片的來源(通常是來自[Twitter](https://twitter.com)或[Pixiv](https://pixiv.net))儲存至指定的資料夾，並按照來源、圖片或推文的ID、作者的ID及作者暱稱命名。資料庫功能將避免儲存到同樣的圖片，換而言之，Sabersort也能排除相同的圖片。

## 使用前要準備什麼？

- [Python 3.8.7](https://www.python.org/) 或以上的版本
- beautifulsoup4 4.9.3 或以上的版本 (可使用``pip install beautifulsoup4``安裝)
- ImageHash 4.2.1 或以上的版本 (可使用``pip install ImageHash``安裝)
- Pillow 8.3.2 或以上的版本 (可使用``pip install Pillow``安裝)
- requests 2.25.1 或以上的版本 (可使用``pip install requests``安裝)
- requests_toolbelt 0.9.1 或以上的版本 (可使用``pip install requests_toolbelt``安裝)
- [Google Chrome](https://www.google.com/chrome/)
- Chrome的webdriver (在[https://chromedriver.chromium.org](https://chromedriver.chromium.org)中找到與你的Google Chrome相對應的版本)

以上都準備好時，打開``config.ini``，並依照這樣填入對應的資訊：

    [sabersort]
    Input directory = 你要輸入的圖片所存放的資料夾
    Output directory = 下載下來的圖片要儲存的資料夾
    Exception directory = 如果沒有搜尋到結果就把圖片移到這裡(保持空白的話預設存在Output directory下的Exception中)
    Database path = 資料庫的路徑(預設為Sabersort資要夾下的saberdb.db)
    User-agent = 1.
    
    [pixiv]
    PHPSESSID = 2.
    device_token = 2.
    
    [twitter]
    Chrome webdriver path = 你剛剛下載的Chrome webdriver存在哪裡

1. 如果你不知道使用者代理是甚麼的話，就開瀏覽器去[https://www.whatsmyua.info/](https://www.whatsmyua.info/)把最上面那個框框裡面的字全部複製下來貼上去就好了。

2. Pixiv的Cookie可以這樣找： ``Google Chrome重新整理和網址列中間那個鎖頭`` → ``(目前使用 x 個Cookie) 個Cookie`` → ``pixiv.net`` → ``Cookie`` → ``找到PHPSESSID和device_token`` → ``複製貼上內容的部分``

## 怎麼用？

    usage: sabersort.py [-h] [-c] [-ch] [-sw] [-t THRESHOLD] [-v]
    
    optional arguments:
      -h, --help            show this help message and exit
      -c, --check-db        check if images in the database are still there
      -ch, --check-db-hash  check if image in the database are still there and correct.
      -sw, --show-window    show chrome window while fetching twitter image.
      -t THRESHOLD, --threshold THRESHOLD
                            number of results to check while searching on ascii2d
      -v, --verbose         increase output verbosity

 - ``-h``或``--help``：顯示上面那段說明文字，不做任何其他事情。
 - ``-c``或``--check-db``：開始搜尋前先檢查資料庫，確定資料庫(先前搜尋過的檔案)還在不在。
 - ``-ch``或``--check-db-hash``：開始搜尋前先檢查資料庫，但除了檢查檔案之外還會確定檔案是否正確，選這個選項的話會檢查的比較慢。
 - ``-sw``或``--show-window``：使用Chrome webdriver時顯示視窗，如果你很好奇Sabersort做了什麼就選，基本上沒意義。
 - ``-t 檢查數``或``--threshold 檢查數``：在[二次元画像詳細検索](https://ascii2d.net/)以圖搜圖的時候常常會搜尋到一些不相關的圖片，這個選項會讓Sabersort只比對前``檢查數``個最相似的結果，建議啟用這個選項，推薦設定為``3``或以下。
 - ``-v``或``--verbose``：在終端機或命令提示字元顯示更多資訊，基本上這是拿來是除錯用，如果你很想了解Sabersort當下正在做什麼就開吧。然後開這個也會讓log的檔案大小增加，雖然沒差多少就是了。

### 懶人包

``python sabersort.py -t 3``

## 關於為什麼我要寫Sabersort

只要你也有加Saber Chen(Lure Rabbit)的Facebook好友，基本上你每天都會被各種很香的東西洗版。鑑於Facebook上各粉絲專頁及用戶的智慧財產權觀念程度不同，並非所有人都會在貼文中附上來源資訊；即使附上了來源資訊，若只是順手按下儲存鍵，不論是Facebook或Twitter，皆無法依其預設儲存檔名推斷來源資訊，不只要找到喜歡的創作者更加困難，也是變相減少該名創作者的收益(更不用說fb他媽壓畫質壓音質壓到變低能兒)。綜上所述，我要在此感謝Saber給了我這個靈感，若沒有他每天堅持不懈地分享這些事物，Sabersort不會誕生。

## 他的歌超屌的快去聽
 - [Soundcloud](https://soundcloud.com/lurerabbit)
 - [BASS QREW COMPILATION VOL.1](https://www.toneden.io/quotex/post/bass-qrew-compilation-vol-1)
 - [DISCLOAX Bandcamp](https://discloax.bandcamp.com/)
