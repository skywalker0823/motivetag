# MotiveTag

https://motivetag.xyz/

## About
Motivetag is a website covers main functionality of social networks. With a "Tag cored" design.


### What is a Tag?

Inspired by hashtag, a Tag is any keyword you can think of. Use Tag in your posts, then others can search for it, thus anyone with same interests can easily reach the post, and so can you. You can also subscribe a Tag, cause you might not want miss anything you liked to follow.

Using "#" following by keyword, will tag this post with that keyword on sent. Ofcourse you can use multiple tags or none(but this let the post only will be seen by your friends).

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

<!-- ### Example
![Untitled](https://user-images.githubusercontent.com/56625237/172856140-9cfd9128-35ef-4f14-8c3b-74ed96fca716.gif) -->

### Friend & online status
<img width="277" alt="截圖 2022-06-09 下午9 29 08" src="https://user-images.githubusercontent.com/56625237/172858835-c76548e2-6ce0-45e1-8c6f-7e29a3305c32.png">




---

## Functions
May not perfect, but handmade with love.
### Member
* User avatar.
* Levels with activities.
* Personal if custom message.
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
* Anonymous - Special tag, can imply post with anonymous. 
* Upload Image - Share images.
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
        * Moment.js
            For time display, also helped managing time difference between server and local.
        * Chart.js
            Vote result graph dosplay.
        * Socket.io
            For chat and notification function.
        * box icons
    * Tech
        * AJAX
            We really don't like frequently refresh the page, right?


### Backend
* Python
    * Flask
        * RESTful API
        * Flask-socketio
        * MVC
        * Factory design pattern
    * Virtualenv

### Database
* MySQL
    * Pymysql
    * Connection Pool

### Version control
* Git
* Github

### Deploy
* Docker
* Docker hub

### AWS
* EC2
    * NGINX
        Reverse proxy, and cache static files.
    * Linux-Ubuntu
* Elastic LoadBalancer
    For auto-scaling group.
* Route53
    Imply with HTTPS.
* RDS
    AWS relational database with very easy set up and easy to use.
* S3
    Storing images.
* CloudFront
    Reduce latency delivering images to users.

---



## Structure

### Database


### AWS

---




