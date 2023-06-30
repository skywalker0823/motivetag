![title](https://user-images.githubusercontent.com/56625237/173245676-b0f6ed11-947e-4b86-ac2b-6dc098fbf1f1.png)
Designed with photoshop.

# MotiveTag
預計回歸

待辦清單Note
* Images in ECR should be seperated or not?

0. ~~Nginx~~
1. EKS
2. Full CICD
3. Redis/Kafka setting(chat status)
4. MySQL improve, ORM
5. Security
6. UI/UX and RWD redesign
7. Basic code improve
8. PlanetScale
9. Axiom

## Note
* Redis for managing online/chat status.
* Kafka for chat message.
* MySQL for data storage.
* All resources should in AWS.

~~https://motivetag.xyz/~~
closed due to aws free tier expired.

貼文、標記、送出，跟其他人一起討論並認識新朋友，加入/訂閱你有興趣的內容(Tag)，持續關注你想關注的話題，沒有廢話!沒有廣告!


## About

* Motivetag is a website covers main functionality of social networks. With a "Tag cored" design.
* 這是一個社群網站，本身以 Tag 為核心運作。

### 目前已部署功能
* 貼文(包含匿名、投票、圖片上傳), 加tag, 按讚與留言
* 訂閱你有興趣的內容(Tag)並追蹤
* 聊天功能 包含上線狀態與來訊提示
* 好友系統
* 通知功能
* 無限多的討論區

### What is a Tag?

* Inspired by hashtag, a Tag is any keyword you can think of. Use Tag in your posts, then others can search for it, thus anyone with same interests can easily reach the post, and so can you. You can also subscribe a Tag, cause you might not want miss anything you liked to follow.
* 啟發自 Hashtag ，Tag是一個任何你能想到的關鍵字。在你的貼文當中加入 Tag ，其他人能依此去尋找到這些貼文，如此與你有相同興趣的人就可以跟你討論這個主題。
你也可以訂閱 Tag ，這樣就不會錯過任何有關此 Tag 的內容了。

* Using "#" following by keyword, will tag this post with that keyword on sent. Ofcourse you can use multiple tags or none(but this let the post only will be seen by your friends).
* 在任何字串前加上"#" 後面以空白分開(#像這樣 )，就可以自動標記該文章。當然你也可以加上一堆標記又或者什麼都不加(什麼都不加就只有你的好友能看到這篇文章了!)

<img width="509" alt="截圖 2022-06-09 下午9 27 39" src="https://user-images.githubusercontent.com/56625237/172858559-ead4c27c-fe52-42cd-a186-84adecdfcba8.png">


<img width="501" alt="截圖 2022-06-09 下午9 02 51" src="https://user-images.githubusercontent.com/56625237/172853490-67223880-8baf-406e-80ee-ef92f8594123.png">


---

## PREVIEW

### Testing account
| Account     | Password|
| ------------- |:-------------:|
| guest     | guest | 


### Front page
<img width="1327" alt="截圖 2022-06-09 下午8 53 59" src="https://user-images.githubusercontent.com/56625237/172851655-beb06ce6-0d45-4943-b34b-886799ac5339.png" style="width:49%;">

### User page(Main page)
<img width="1327" alt="截圖 2022-06-09 下午8 59 41" src="https://user-images.githubusercontent.com/56625237/172852759-20085ebb-5ced-4c35-bb49-803f0899957f.png" style="width:49%;">

### Tag subscribe
<img width="284" alt="截圖 2022-06-09 下午9 00 57" src="https://user-images.githubusercontent.com/56625237/172853054-36d8e15f-aff2-42c9-a5ad-bc2cb748d2e1.png">


### Friend & online status
<img width="277" alt="截圖 2022-06-09 下午9 29 08" src="https://user-images.githubusercontent.com/56625237/172858835-c76548e2-6ce0-45e1-8c6f-7e29a3305c32.png">




---

## Functions

### Member
* User avatar.
* Levels with activities.
* Personal custom message.
* Click on user avatar or friend status to show his/her personal information.
### Tag
* Trend - Order by the number of subscribers.
* Tag subscribe.
* PrimeTag - Experimental tag that has specific ability.
    1. Beginner's guide Tag.(新手引導) Initial attached to new users.
    2. Anonymous Tag.
### Post & Comment
* Displays following content/posts. 
    1. Contains tag you subscribed. 
    2. Friend post. 
    3. Your own posts(include secret post).
* Tag - Automatically insert any tag with #keyword in your posts.
* Thumbs up or down.
* Vote - Praise democracy.
* Anonymous - Special tag, can imply post with anonymous, only those who subscribes Anonymous tag will see them, but they won't know the poster. 
* Upload Image - Share images with others.
* Secret - A ONLY YOU CAN SEE post.
<dt>Tags, Vote, Anonymous, image upload can use separately or together!</dt>

* Tag of interest - Search for specific tagged content.
* Refresh posts with the button located in middle of nav bar.
* Up & Down scoring - Leave your comment with scroe!
### Chat
* OK with multi-window chat.
* Ringing - When someone wants to start a chat with you, will recieve a shaking effect on the chat image.
* Online status - Online = blue, Offline = red
### Notification
* Informs you with friendship status update and offline calling.
### Tag forum (In progress)
This idea comes when the website is almost done. The final goal is to create a 「Any Tag is a individual discussion area」environment. And will use the PrimeTag to enforce the forum feature. Stay tuned!


---

## Tech & tool used 
### Frontend
* HTML
* CSS
* Javascript
    * Tools
        * Moment.js - Time management.
        * Chart.js - Chart display.
        * Socket.io - For websocket protocol, a real-time communication library.
    * Tech
        * AJAX

### Backend
* Use Python
* Flask
    * Tools
        * Flask-socketio - Server side websocket connetion tool.
        * Virtualenv
        * boto3 - Upload images to AWS.
        * Pymysql
            * Connection Pool - Maintain connections between RDS and Flask.
    * Tech
        * RESTful API
        * MVC

### Database
* MySQL
    * Tools
        * MySQL workbench
    * Tech 
        * Database normalization

### Version control
* Git
* Github

### Deploy
* Docker
* Docker hub

### AWS
* EC2
    * NGINX : Reverse proxy, and cache static files.
    * Linux-Ubuntu
* Route53 : Domain name mabage.
* Elastic LoadBalancer : Imply with HTTPS protocol.
* RDS : A relational database with simple set up and easy to use, include backup.
* S3 : Storing images.
* CloudFront : Reduces latency when delivering images to users.

---

## Structure

### Database
<img width="683" alt="截圖 2022-06-11 下午5 45 15" src="https://user-images.githubusercontent.com/56625237/173182791-a17bc194-b150-4350-99f1-9ccea75d641f.png">


### AWS
<img width="1023" alt="截圖 2022-06-14 上午2 32 08" src="https://user-images.githubusercontent.com/56625237/173420968-f6c5a324-6646-49e9-ae22-2512e79285f2.png">


---




