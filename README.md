# Sabersort

## 這是做什麼用的？

Sabersort會將你的圖片，逐個透過[二次元画像詳細検索](https://ascii2d.net/)進行以圖片搜尋，並找到相似的圖片，藉此尋找該圖片的原創作者。Sabersort會自動將圖片的來源(通常是來自[Twitter](https://twitter.com)或[Pixiv](https://pixiv.net))儲存至指定的資料夾，並按照圖片或推文的ID、作者的ID或作者暱稱等資訊命名。資料庫功能會避免儲存到同樣的圖片，換而言之，Sabersort也能排除相同的圖片。

## 使用前要準備什麼？

先安裝Python，用Windows的話記得安裝時要選PATH的選項。

- [Python 3.10](https://www.python.org/downloads/release/python-3108/) 或以上的版本

以下是需要的程式庫，除了Google Chrome之外，你可以直接使用這個指令來安裝它們

    pip install -r requirements.txt

- [Google Chrome](https://www.google.com/chrome/)
- aiofiles==23.1.0
- aiohttp==3.8.3
- asyncio_atexit==1.0.1
- beautifulsoup4==4.12.2
- ImageHash==4.3.1
- packaging==21.3
- PicImageSearch==3.9.2
- Pillow==9.5.0
- selenium==4.10.0
- webdriver_manager==3.8.4

以上都準備好時，將``config.ini.template``重新命名成``config.ini``後打開，你會看到：

    [sabersort]
    Input directory = 
    Found directory = 
    Not found directory = 
    Exception directory = 
    Filename = {origin}-{author_id}-{id}
    Threshold = 10
    User-agent = 

    [saberdb]
    Database path = saberdb.db
    Check database = True

    [hasher]
    Hash algorithm = Perceptual
    Hash size = 16

    [ascii2d]
    Prefered origin = Pixiv
    Sort order = No
    First = 0

    [pixiv]
    PHPSESSID = 

    [twitter]
    auth_token = 

+ ``[sabersort]``
    + ``Input directory``：填放著需要搜尋的圖片所在的資料夾，資料夾裡面建議只放圖片。
    + ``Found directory``：填要放下載下來的圖片的資料夾。
    + ``Not found directory``：填要找不到的圖片的資料夾，會把檔案複製過去。
    + ``Exception directory``：填要找到了但有問題的圖片的資料夾，會把檔案複製過去，並按照已知的資訊命名；這種狀況通常發生在有找到但原作者刪文。
    + ``Filename``是檔名，你有以下標籤可以使用：
        + ``{origin}``：從哪裡下載的
        + ``{author}``：作者的名字，因為有些作者可能會用一些奇奇怪怪的字元當名字，你的系統不一定會支援，斟酌使用。
        + ``{author_id}``作者的id，要儲存作者資訊建議用這個。
        + ``{title}``圖片標題，推特的是日期，pixiv的話可能會出現包含奇奇怪怪的字元的標題，斟酌使用。
        + ``{id}``：圖片的id，推特的話是貼文的id。
        + ``{index}``：同一個圖片id裡面可能會有超過1張圖片，這是用來識別是第幾張圖片的。
    + ``Threshold``：圖片相似度的容許度，基本上沒必要修改，改高一點的話可能會找到一些差分。
    + ``User-agent``：直接去[這個網站](https://www.whatsmyua.info/)把文字輸入框裡面的字複製貼上到這裡就可以了。
+ ``[saberdb]``
    + ``Database path``：資料庫路徑，基本上不用改。
    + ``Check database``：要不要檢查資料庫去除已失效或刪除的圖片，改成``False``就不檢查，但這其實不會花多少時間，建議維持``True``。
+ ``[hasher]``
    + ``Hash algorithm``：用來判斷圖片是否相似的演算法，具體差異參考[這裡](https://github.com/JohannesBuchner/imagehash)，你有以下選擇：
        + ``Average``
        + ``Perceptual``
        + ``PerceptualSimple``
        + ``Difference``
        + ``Wavelet``
        + ``HSV``
    + ``Hash size``：可以看成是計算的精確度，越大越精確，基本上維持16已經足夠。
+ ``[ascii2d]``
    + ``Prefered origin``：優先選擇哪個來源，建議``Pixiv``，推特有畫質上限，你有以下選擇：
        + ``Pixiv``
        + ``Twitter``
    + ``Sort order``：如何排序搜尋結果，``No``代表不排，基本上是不用排，``Image_Size``代表用圖片長寬大小來排，``File_Size``代表用檔案大小來排。
        + ``No``
        + ``Image_Size``
        + ``File_Size``
    + ``First``：只搜尋前幾個結果，0代表不限制，要設定的話建議在``3``到``6``，太高沒意義，太低會找不出來。
+ ``[pixiv]``
    + ``PHPSESSID``：把Pixiv的cookies複製到這裡，不知道怎麼找可以看[這裡](https://www.minwt.com/webdesign-dev/html/18437.html)，進入Pixiv網站後，它會在``pixiv.net``底下。
+ ``[twitter]``
    + ``auth_token``：一樣是cookies，只是要進去Twitter網站，它會在``twitter.com``底下。

## 怎麼用？

上面的設定填好存檔後，直接在終端機輸入：

    python sabersort.py

## 專案進度

- [x] 重寫整個Sabersort(對的這是新版)
- [ ] log紀錄檔
- [ ] 圖形化使用者介面
- [ ] 其他以圖搜圖網站的支援(例如iqdb)