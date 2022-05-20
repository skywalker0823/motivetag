const member_blocks = document.getElementById("member_blocks");
const block_box = document.getElementById("block_box");
let new_send = false;
let page = 0;
let open;
let deleting = false;
let fetching = false;
let url_now


// var tag = document.createElement("script");
// tag.src = "https://www.youtube.com/iframe_api";
// var firstScriptTag = document.getElementsByTagName("script")[0];
// firstScriptTag.parentNode.insertBefore(tag, firstScriptTag);
// window.onYouTubeIframeAPIReady = this.onYTready;


search_build_blocks = async (mode) => {
  if (mode == "windowed") {
    fetching = true;
    member_blocks.scrollTop = 0;
    page = 0;
    block_box.innerHTML = "";
  }
  const response = await fetch("/api/blocks?page=" + page);
  const result = await response.json();
  if (result.ok) {
    block_builder(result);
  } else {
    return result;
  }
};

block_builder = async (data) => {
  for (block of data.data) {
    let account = block.account;
    let content_type = block.content_type;
    let content = block.content;
    let image = block.block_img;
    let time = block.build_time;
    let good = block.good;
    let bad = block.bad;
    let member_id = block.member_id;
    let block_id = "block" + block.block_id;
    let del_btn;
    let tags = block.tags;
    if (!good) {
      good = "";
    }
    if (!bad) {
      bad = "";
    }

    a_block = document.createElement("div");
    a_block.setAttribute("class", "a_block");
    a_block.setAttribute("id", block_id);

    //Type
    block_title = document.createElement("div");
    block_title.setAttribute("class", "block_titler");
    typer = document.createTextNode(content_type);
    block_typer = document.createElement("div");
    block_typer.setAttribute("class", "block_typer");
    block_typer.appendChild(typer);

    //user_avatar
    block_avatar = document.createElement("img");
    block_avatar.setAttribute("onerror","this.onerror=null;this.src='/img/ghost-regular-24.png';")
    block_avatar.setAttribute("class", "block_avatar");
    block_avatar.setAttribute(
      "src",
      "https://d3nvrufajko3tj.cloudfront.net/avatar_" + member_id
    );

    //account
    author = document.createElement("div");
    who = document.createTextNode(" @" + account);
    author.appendChild(who);
    block_typer.appendChild(author);

    //個人大頭整合
    block_header = document.createElement("div");
    block_header.setAttribute("class", "block_header");
    block_header.appendChild(block_avatar);
    block_header.appendChild(block_typer);
    block_title.appendChild(block_header);

    //刪除鍵
    if (me == account) {
      del_btn = document.createElement("img");
      del_btn.setAttribute("src", "/img/icon_close.png");
      del_btn.setAttribute("onclick", "del_block(this.id)");
      del_btn.setAttribute("id", "del" + block_id);
      del_btn.setAttribute("class", "del_tag");
      block_title.appendChild(del_btn);
    }

    //發言
    block_content = document.createElement("div");
    block_content.setAttribute("class", "block_content");
    content_says = document.createTextNode(content);
    block_content.appendChild(content_says);

    //tag
    tagger = document.createElement("div");
    if (tags.length != 0) {
      tag = document.createTextNode("#TAG : " + tags);
    } else {
      tag = document.createTextNode("");
    }
    tagger.setAttribute("class", "a_block_tag");
    tagger.appendChild(tag);
    block_content.appendChild(tagger);

    //YT API
    // let ytplayer = document.createElement("div")
    // ytplayer.setAttribute("id","player_here")
    // let regExp =
    //   /^.*((youtu.be\/)|(v\/)|(\/u\/\w\/)|(embed\/)|(watch\?))\??v?=?([^#&?]*).*/;
    // let match = content.match(regExp);
    // if(match){
    //   console.log(match[7])
    //   url_now = match[7]
      
    // }

    //上傳圖片預定放置處
    block_image = document.createElement("img");
    block_image.setAttribute("class", "block_image");
    block_image.setAttribute("id", "block_image" + block.block_id);
    if (image) {
      block_image.setAttribute(
        "src",
        "https://d3nvrufajko3tj.cloudfront.net/" + image
      );
    }

    //讚box
    good_box = document.createElement("div");
    good_box.setAttribute("class", "good_box");
    //讚btn
    good_btn = document.createElement("box-icon");
    good_btn.setAttribute("name", "like");
    good_btn.setAttribute("color", "#1cbfff");
    good_btn.setAttribute("id", "good" + block.block_id);
    good_btn.setAttribute("onclick", "gooder(this.id)");
    good_btn.setAttribute("class", "good");

    //讚
    good_count = document.createElement("div");
    good_count.appendChild(document.createTextNode(good));
    good_count.setAttribute("id", "good_count" + block.block_id);
    good_box.appendChild(good_btn);
    good_box.appendChild(good_count);

    //爛box
    bad_box = document.createElement("div");
    bad_box.setAttribute("class", "bad_box");
    //爛btn
    bad_btn = document.createElement("box-icon");
    bad_btn.setAttribute("name", "dislike");
    bad_btn.setAttribute("color", "#1cbfff");
    bad_btn.setAttribute("id", "bad" + block.block_id);
    bad_btn.setAttribute("onclick", "badder(this.id)");
    bad_btn.setAttribute("class", "bad");

    //爛
    bad_count = document.createElement("div");
    bad_count.appendChild(document.createTextNode(bad));
    bad_count.setAttribute("id", "bad_count" + block.block_id);
    bad_box.appendChild(bad_btn);
    bad_box.appendChild(bad_count);
    good_box.appendChild(bad_box);

    //分享(預定)
    share_btn = document.createElement("box-icon");
    share_btn.setAttribute("name", "share");
    share_btn.setAttribute("color", "#1cbfff");
    share_btn.setAttribute("id", "share" + block.block_id);
    share_btn.setAttribute("onclick", "share(this.id)");
    share_btn.setAttribute("class", "share");
    good_box.appendChild(share_btn);

    //時間
    block_time = document.createElement("div");
    block_time.setAttribute("class", "block_time");
    time = moment(time).subtract(8, "hours").fromNow();
    block_spawn = document.createTextNode(time);
    // Tue, 10 May 2022 01:58:10 GMT
    block_time.appendChild(block_spawn);

    //開始建構留言區域
    block_message_control = document.createElement("div");
    block_message_control.setAttribute("class", "block_message_control");
    //block下留言
    guest_input = document.createElement("input");
    guest_input.setAttribute("id", "messes" + block.block_id);
    guest_input.setAttribute("style", "text");
    guest_input.setAttribute("class", "guest_input");
    guest_input.setAttribute("placeholder", "留下訊息...");
    //block按鈕
    guest_input_btn = document.createElement("button");
    btn_text = document.createTextNode("Stack");
    guest_input_btn.setAttribute("id", "mess_btn" + block.block_id);
    guest_input_btn.setAttribute("onclick", "leave_message(this.id)");
    guest_input_btn.setAttribute("class", "guest_input_btn");
    guest_input_btn.appendChild(btn_text);

    //裝箱
    block_message_control.appendChild(guest_input);
    block_message_control.appendChild(guest_input_btn);

    a_block.appendChild(block_title);
    a_block.appendChild(block_content);
    // a_block.appendChild(ytplayer);
    a_block.appendChild(block_image);
    a_block.appendChild(good_box);
    a_block.appendChild(block_time);
    a_block.appendChild(block_message_control);

    if (new_send) {
      block_id = block_id.split("block")[1];
      let guest_message = document.createElement("div");
      guest_message.setAttribute("id", "message_box" + block_id);
      guest_message.setAttribute("class", "message_box");
      a_block.appendChild(guest_message);
      block_box.prepend(a_block);
      new_send = false;
      return;
    }
    block_box.appendChild(a_block);
    resulter = await block_click(block_id);
    if (resulter == "ok") {
      continue;
    }
  }
  fetching = false;
};

//發文
document
  .getElementById("block_submit_btn")
  .addEventListener("click", async () => {
    let type = document.getElementById("blockor_type").value;
    let content = document.getElementById("blockor_content").value;
    let time = moment().format("YYYY-MM-DD HH:mm:ss");
    let tags = tag_appender();
    if (!content) {
      return;
    }
    const options = {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        type: type,
        content: content,
        time: time,
        tags: tags,
      }),
    };
    const response = await fetch("/api/blocks", options);
    const result = await response.json();
    if (result.ok) {
      new_send = true;
      let file = document.getElementById("upload_block_img").files[0];
      if (file) {
        let reader = new FileReader();
        reader.readAsDataURL(
          document.getElementById("upload_block_img").files[0]
        );
        reader.onload = function (oFREvent) {
          document.getElementById(
            "block_image" + result.data[0]["block_id"]
          ).src = oFREvent.target.result;
        };
        document.getElementById("img_pre_box").style.display = "none";
        block_img_uploader(result);
      }

      block_builder(result);
      document.getElementById("blockor_content").value = "";
      console.log(document.getElementById("upload_block_img").files);
    } else {
      console.log(result.msg, result.msg2);
    }
  });

textarea_holder = () => {
  let textarea = document.getElementById("blockor_content");
  let limit = 80; //height limit
  textarea.oninput = function () {
    textarea.style.height = "";
    textarea.style.height = Math.min(textarea.scrollHeight, limit) + "px";
  };
};

//或許有其他用途的打字偵測
// let hash_mode = false
// let key = [];
// const blockor_content = document.getElementById("blockor_content");
// blockor_content.addEventListener("input",(word)=>{
//   console.log(blockor_content.value);
// })

tag_appender = () => {
  return;
};

//Block deleter
del_block = async (block) => {
  deleting = true;
  let block_id = block.split("delblock")[1];
  const options = {
    method: "DELETE",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ block_id: block_id }),
  };
  const response = await fetch("/api/blocks", options);
  const result = await response.json();
  if (result.ok) {
    document.getElementById("block" + block_id).remove();
    open = false;
    deleting = false;
    return;
  }
  deleting = false;
};

//留言 召喚!
block_click = async (id) => {
  let block_id = id.split("block")[1];
  const response = await fetch("/api/message?block_id=" + block_id);
  const result = await response.json();
  if (result.ok) {
    let guest_message = document.createElement("div");
    guest_message.setAttribute("id", "message_box" + block_id);
    guest_message.setAttribute("class", "message_box");
    for (a_message of result.ok) {
      let one_mess = document.createElement("div");
      one_mess.setAttribute("class", "one_mess");

      let mess_avatar = document.createElement("img");
      mess_avatar.setAttribute("class", "mess_avatar");
      mess_avatar.setAttribute(
        "src",
        "https://d3nvrufajko3tj.cloudfront.net/avatar_" + a_message.member_id
      );

      let who = document.createElement("p");
      who.setAttribute("class", "message_who");
      who.appendChild(document.createTextNode(a_message.account + " said : "));

      let say = document.createElement("p");
      say.setAttribute("class", "message_say");
      say.appendChild(document.createTextNode(a_message.content));

      let nice_commenter = document.createElement("box-icon");
      nice_commenter.setAttribute("name", "like");
      nice_commenter.setAttribute("id", "nice" + a_message.comment_id);
      nice_commenter.setAttribute("class", "nice");
      nice_commenter.setAttribute("onclick", "nice(this.id)");
      nice_commenter.setAttribute("color", "#1cbfff");

      //留言的讚
      let nice_count = document.createElement("div");
      nice_count.setAttribute("id", "how_nice" + a_message.comment_id);
      nice_count.appendChild(document.createTextNode(a_message.nice_comment));

      let time = moment(a_message.build_time).subtract(8, "hours").fromNow();
      let time_box = document.createElement("div");
      time_box.setAttribute("class", "message_time");
      timestamp = document.createTextNode(time);
      time_box.appendChild(timestamp);
      one_mess.appendChild(mess_avatar);
      one_mess.appendChild(who);
      one_mess.appendChild(say);
      one_mess.appendChild(nice_commenter);
      one_mess.appendChild(nice_count);

      one_mess.appendChild(time_box);
      guest_message.appendChild(one_mess);
    }
    document.getElementById("block" + block_id).appendChild(guest_message);
    return "ok";
  } else {
    console.log("get message fail");
  }
};

//Block_Messages->POST
leave_message = async (message_block_id) => {
  console.log(message_block_id);
  let block_id = message_block_id.split("mess_btn")[1];
  let message = document.getElementById("messes" + block_id);
  if (!message.value) {
    return;
  }
  let time = moment().format("YYYY-MM-DD HH:mm:ss");
  console.log(block_id, message.value); //1019,XD (這裡是block ID)
  //請上傳block_id,message,time
  const options = {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({
      block_id: block_id,
      message: message.value,
      time: time,
    }),
  };
  const response = await fetch("/api/message", options);
  const result = await response.json();

  if (result.ok) {
    let comm_id = result.ok["LAST_INSERT_ID()"];
    let target = document.getElementById("message_box" + block_id);

    let a_message = document.createElement("div");
    a_message.setAttribute("class", "one_mess");

    //img
    let mess_avatar = document.createElement("img");
    mess_avatar.setAttribute("class", "mess_avatar");
    mess_avatar.setAttribute(
      "src",
      "https://d3nvrufajko3tj.cloudfront.net/avatar_" + result.member_id
    );

    //who
    let who = document.createElement("p");
    who.setAttribute("class", "message_who");
    who.appendChild(document.createTextNode(result.account + " said : "));

    //say
    let say = document.createElement("p");
    say.setAttribute("class", "message_say");
    say.appendChild(document.createTextNode(message.value));

    let nice_commenter = document.createElement("box-icon");
    nice_commenter.setAttribute("name", "like");
    nice_commenter.setAttribute("id", "nice" + comm_id);
    nice_commenter.setAttribute("class", "nice");
    nice_commenter.setAttribute("onclick", "nice(this.id)");
    nice_commenter.setAttribute("color", "#1cbfff");

    //留言的讚
    console.log(a_message);
    let nice_count = document.createElement("div");
    nice_count.setAttribute("id", "how_nice" + comm_id);
    nice_count.appendChild(document.createTextNode(""));

    //time
    let time = moment(result.build_time).fromNow();
    let time_box = document.createElement("div");
    time_box.setAttribute("class", "message_time");
    timestamp = document.createTextNode(time);
    time_box.appendChild(timestamp);

    a_message.appendChild(mess_avatar);
    a_message.appendChild(who);
    a_message.appendChild(say);
    a_message.appendChild(nice_commenter);
    a_message.appendChild(nice_count);
    a_message.appendChild(time_box);

    target.appendChild(a_message);
    message.value = "";
    return;
  }
};

//讚
gooder = async (id) => {
  let target = id.split("good")[1];
  console.log(target);
  const options = {
    method: "PATCH",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({
      block_id: target,
    }),
  };
  const response = await fetch("/api/blocks", options);
  const result = await response.json();
  if (result.ok) {
    console.log("good complete");
    let add_this = document.getElementById("good_count" + target);
    console.log(add_this);
    if (add_this.innerHTML == "") {
      add_this.innerHTML = "1";
      return;
    }
    add_this.innerHTML = parseInt(add_this.innerHTML) + 1;
  } else {
    console.log("good fail");
  }
};

//讚
badder = async (id) => {
  let target = id.split("bad")[1];
  console.log(target);
  const options = {
    method: "PUT",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({
      block_id: target,
    }),
  };
  const response = await fetch("/api/blocks", options);
  const result = await response.json();
  if (result.ok) {
    console.log("bad complete");
    let add_this = document.getElementById("bad_count" + target);
    console.log(add_this);
    if (add_this.innerHTML == "") {
      add_this.innerHTML = "1";
      return;
    }
    add_this.innerHTML = parseInt(add_this.innerHTML) + 1;
  } else {
    console.log("bad fail");
  }
};

//Infite Scroll
member_blocks.addEventListener("scroll", () => {
  if (fetching) {
    return;
  }
  if (
    member_blocks.scrollHeight * 0.9 <=
    member_blocks.scrollTop + member_blocks.offsetHeight
  ) {
    console.log("BOT!");
    page += 5;
    console.log(page);
    //目前數量一次3篇 好好規劃數量~
    fetching = true;
    result = search_build_blocks();
    if (result.error) {
    }
  }
});

upload_block_img_preview = () => {
  document.getElementById("img_pre_box").style.display = "flex";
  let reader = new FileReader();
  reader.readAsDataURL(document.getElementById("upload_block_img").files[0]);
  reader.onload = function (oFREvent) {
    // cancel = document.createElement("p")
    // cancel.appendChild(document.createTextNode("取消"))
    // cancel.setAttribute("onclick","cancel_upload()")
    // document.getElementById("img_pre_box").appendChild(cancel)
    document.getElementById("upload_preview").src = oFREvent.target.result;
    
  };
};

block_img_uploader = async (block_data) => {
  console.log(block_data);
  let block_id = block_data["data"][0]["block_id"];
  let file = document.getElementById("upload_block_img").files[0];
  if (!file) {
    return;
  }
  console.log("有圖片 開始上傳");

  let data = new FormData();
  data.append("image", file);
  data.append("type", "block");
  data.append("target_id", block_id);
  console.log(file, block_id);
  const options = { method: "POST", body: data };
  const response = await fetch("/api/images", options);
  const result = await response.json();
  if (result.ok) {
    console.log("Upload OK!");
    document.getElementById("upload_block_img").value = "";
  }
};

cancel_upload = () => {
  console.log("取消上傳")
  document.getElementById("img_pre_box").style.display = "none";
  let file = document.getElementById("upload_block_img").files;
  document.getElementById("upload_block_img").value = "";
}

nice = async (id) => {
  let target = id.split("nice")[1];
  const options = {
    method: "PATCH",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({
      message_id: target,
    }),
  };
  const response = await fetch("/api/message", options);
  const result = await response.json();

  //
  if (result.ok) {
    let add_this = document.getElementById("how_nice" + target);
    console.log(add_this);
    if (add_this.innerHTML == "") {
      add_this.innerHTML = "1";
      return;
    }
    add_this.innerHTML = parseInt(add_this.innerHTML) + 1;
  } else {
    console.log("good fail");
  }
};

let anonymous = false;
anonymous_mode = () => {
  console.log("anonymous mode");
  let blockor = document.getElementById("blockor_inner");
  let inner = document.getElementById("blockor_content");
  if (!anonymous) {
    anonymous = true;
    blockor.style.border = "#e20cfc 1px solid";
    inner.placeholder = "Anonymous";

    return;
  }
  blockor.style.border = "#1cbfff 1px solid";
  let thoughts = [
    "Any thoughts?",
    "Any?...",
    "Really?...",
    "Talk about?...",
    "Today...",
    "OK...",
    ":)",
    "Good day!",
    "Say something...",
    "Looking for?",
    "Check some Tags",
    "Let's build!",
  ];
  thought = thoughts[Math.floor(Math.random() * thoughts.length)];
  inner.placeholder = thought;
  anonymous = false;
};

////////////////////YOUTUBE API////////////////////

// var player;
// window.onYouTubeIframeAPIReady=()=>{
//   player = new YT.Player("player_here", {
//     width: "100%",
//     videoId: url_now,
//     events: {
//       onReady: onPlayerReady,
//       onStateChange: onPlayerStateChange,
//     },
//   });
// }

// // 4. The API will call this function when the video player is ready.
// function onPlayerReady(event) {
//   event.target.playVideo();
// }

// // 5. The API calls this function when the player's state changes.
// //    The function indicates that when playing a video (state=1),
// //    the player should play for six seconds and then stop.
// var done = false;
// function onPlayerStateChange(event) {
//   if (event.data == YT.PlayerState.PLAYING && !done) {
//     setTimeout(stopVideo, 6000);
//     done = true;
//   }
// }
// function stopVideo() {
//   player.stopVideo();
// }