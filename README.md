# Sabersort

## 這是做什麼用的？

Sabersort會將你的圖片，逐個透過[二次元画像詳細検索](https://ascii2d.net/)進行以圖片搜尋，並找到相似的圖片，藉此尋找該圖片的原創作者。Sabersort會自動將圖片的來源(通常是來自[Twitter](https://twitter.com)或[Pixiv](https://pixiv.net))儲存至指定的資料夾，並按照圖片或推文的ID、作者的ID或作者暱稱等資訊命名。資料庫功能會避免儲存到同樣的圖片，換而言之，Sabersort也能排除相同的圖片。

## 使用前要準備什麼？

先安裝Python，用Windows的話記得安裝時要選PATH的選項。

- [Python 3.10](https://www.python.org/downloads/release/python-3108/) 或以上的版本

以下是需要的程式庫，除了Google Chrome之外，你可以直接使用這個指令來安裝它們

    pip install -r requirements.txt

- [Google Chrome](https://www.google.com/chrome/)
- Beautiful Soup 4.11.1
- ImageHash 4.3.1
- Pillow 9.2.0
- requests 2.28.1
- requests_toolbelt 0.10.0
- Selenium 4.5.0
- Webdriver Manager 3.8.4
- packaging 21.3

以上都準備好時，打開``config.ini``，你會看到：

    [sabersort]
    Input directory = 
    Output directory = 
    Not found directory = 
    Exception directory = 
    Filename = {origin}-{author_id}-{id}
    Threshold = 10
    Thread = 3
    User-agent = 

    [saberdb]
    Database path = saberdb.db
    Check database = True
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
    + ``Thread``：平行處理數量，因為ascii2d.net有併發限制，3是極限，如果有問題的話可以降低這個數字。
    + ``User-agent``：直接去[這個網站](https://www.whatsmyua.info/)把文字輸入框裡面的字複製貼上到這裡就可以了。
+ ``[saberdb]``
    + ``Database path``：資料庫路徑，基本上不用改。
    + ``Check database``：要不要檢查資料庫去除已失效或刪除的圖片，改成``False``就不檢查，但這其實不會花多少時間，建議維持``True``。
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

## 關於為什麼我要寫Sabersort

只要你也有加Saber Chen(Lure Rabbit)的Facebook好友，基本上你每天都會被各種很香的東西洗版。鑑於Facebook上各粉絲專頁及用戶的智慧財產權觀念程度不同，並非所有人都會在貼文中附上來源資訊；即使附上了來源資訊，若只是順手按下儲存鍵，不論是Facebook或Twitter，皆無法依其預設儲存檔名推斷來源資訊，不只要找到喜歡的創作者更加困難，也是變相減少該名創作者的收益。綜上所述，我要在此感謝Saber給了我這個靈感，若沒有他每天堅持不懈地分享這些事物，Sabersort不會誕生。

以上都是過去式了，現在他交了一個可愛的女友，也不再分享那些東西。在這段期間他憑藉對VTuber產業的瞭解，與朋友共同成立成立極具前瞻性的[Lumina Works](https://www.facebook.com/LuminaWorks)，在台灣VTUber產業還在發展的時期，提供業界穩定且可靠的高品質音樂。他也在個人的創作上作出許多突破，起飛到無法想像的程度，直接看下面作品集聽歌可以比較直觀的理解他有多帥。

## 各種作品集
- [SoundCloud](https://soundcloud.com/lurerabbit)
- [Portfolio](foriio.com/lure-rabbit)
- [Patreon](https://www.patreon.com/lurerabbit)
