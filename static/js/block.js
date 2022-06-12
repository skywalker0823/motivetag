const member_blocks = document.getElementById("member_blocks");
const block_box = document.getElementById("block_box");
let new_send = false;
let page = 0;
let open;
let deleting = false;
let fetching = false;
let url_now
let ob_mode = false
let ob_page = 0

search_build_blocks = async (mode) => {
  
  if (mode == "windowed") {
    
    fetching = true;
    document.getElementById("loading").style.display="block"
    member_blocks.scrollTop = 0;
    page = 0;
    block_box.innerHTML = "";
  }
  document.getElementById("tag_observer").value=""
  ob_mode=false
  ob_page=0
  const response = await fetch("/api/blocks?page=" + page);
  const result = await response.json();
  if (result.ok) {
    block_builder(result);
  } else {
    document.getElementById("loading").style.display = "none";
    return result;
  }
};

block_builder = async (data) => {
  let temp_box = [];
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
    if(content_type=="Anonymous"){
      block_typer.setAttribute("class", "block_anonymous");
    }else{block_typer.setAttribute("class", "block_typer");}
    block_typer.appendChild(typer);

    //user_avatar
    block_avatar = document.createElement("img");
    block_avatar.setAttribute("onerror","this.onerror=null;this.src='/img/ghost-regular-24.png';")
    block_avatar.setAttribute("class", "block_avatar");
    if(content_type=="Anonymous"){
      block_avatar.setAttribute("src", "/img/ghost-regular-24.png");
    }else{
      block_avatar.setAttribute(
        "src",
        "https://d3nvrufajko3tj.cloudfront.net/avatar_" + member_id
      );
    }

    //account
    author = document.createElement("div");
    if(content_type=="Anonymous"){
      who = document.createTextNode("")
    }else{
      who = document.createTextNode(" @" + account);
    }
    author.appendChild(who);
    block_typer.appendChild(author);

    let block_counter = document.createElement("div")
    block_counter.setAttribute("class","block_counter")
    block_counter.setAttribute("id","block_counter"+block_id.split("block")[1])
    block_counter.innerHTML="+0"

    block_header = document.createElement("div");
    block_header.setAttribute("class", "block_header");
    if (content_type == "Anonymous"){
      block_header.setAttribute("onclick", "return false");
    }else{
      block_header.setAttribute("id", "block_header" + member_id);
      block_header.setAttribute(
        "onclick",
        "display_member_info(this.id)"
      );
    }
    block_header.appendChild(block_counter)
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


    let vote_display = document.createElement("div");
    let chart_holder = document.createElement("div");
    if(block.votes.length!=0){
    vote_display.setAttribute("class","vote_display")
    for(vote of block.votes){
      let a_vote_box = document.createElement("div")
      let vote_name = document.createElement("div")
      let vote_btn = document.createElement("button")
      let vote_result = document.createElement("div")
      a_vote_box.setAttribute("class","a_vote_box")
      vote_btn.setAttribute(
        "id",
        "vote_btn" + vote.vote_option_id + "block_id" + block.block_id
      );
      vote_btn.innerHTML="Vote"
      vote_btn.setAttribute("onclick","vote_this(this.id)")
      vote_btn.setAttribute("class","vote_btn")
      vote_name.appendChild(document.createTextNode(vote.option_name));
      vote_name.setAttribute("id", "vote_option_id" + vote.vote_option_id);
      vote_result.setAttribute("id", "vote_result" + vote.vote_option_id);
      
      a_vote_box.appendChild(vote_name)
      a_vote_box.appendChild(vote_btn)

      vote_display.appendChild(a_vote_box)
    }
    let see_result = document.createElement("button")
    see_result.innerHTML="See result"
    see_result.setAttribute("id", "vote_result" + block.block_id);
    see_result.setAttribute("class","see_result")
    see_result.setAttribute("onclick","see_vote_result(this.id)")
    vote_display.appendChild(see_result)

    //圖表
    chart_holder.setAttribute("class","chart_holder")
    chart_holder.setAttribute("id", "chart_holder" + block.block_id);
    the_canvas = document.createElement("canvas")
    the_canvas.setAttribute("id","canvas"+block.block_id)
    the_canvas.setAttribute("class","the_canvas")
    chart_holder.appendChild(the_canvas)
    
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
    guest_input_holder = document.createElement("div");
    guest_input_holder.setAttribute("class", "guest_input_holder");


    //分數統整區+-5
    score = document.createElement("div")
    score.setAttribute("id","score"+block.block_id)
    score.appendChild(document.createTextNode("0"))

    //up&down
    up_vote = document.createElement("box-icon")
    up_vote.setAttribute("name","chevron-up")
    up_vote.setAttribute("color","#f70307")
    up_vote.setAttribute("id","up_vote"+block.block_id)
    up_vote.setAttribute("onclick","up_score(this.id)")

    down_vote = document.createElement("box-icon")
    down_vote.setAttribute("name","chevron-down")
    down_vote.setAttribute("color", "#09eb5b");
    down_vote.setAttribute("id","down_vote"+block.block_id)
    down_vote.setAttribute("onclick","down_score(this.id)")

    guest_input_btn = document.createElement("button");
    btn_text = document.createTextNode("Stack");
    guest_input_btn.setAttribute("id", "mess_btn" + block.block_id);
    guest_input_btn.setAttribute("onclick", "leave_message(this.id)");
    guest_input_btn.setAttribute("class", "guest_input_btn");
    guest_input_btn.appendChild(btn_text);

    guest_input_holder.appendChild(score)
    guest_input_holder.appendChild(up_vote)
    guest_input_holder.appendChild(down_vote)
    // guest_input_holder.appendChild(guest_upload)
    guest_input_holder.appendChild(guest_input_btn)

    //裝箱
    block_message_control.appendChild(guest_input);
    block_message_control.appendChild(guest_input_holder);

    //投票所裝箱
    vote_boss = document.createElement("div")
    vote_boss.setAttribute("class","vote_boss")
    vote_boss.appendChild(vote_display)
    vote_boss.appendChild(chart_holder)

    a_block.appendChild(block_title);
    a_block.appendChild(block_content);
    // a_block.appendChild(ytplayer);
    a_block.appendChild(block_image);
    a_block.appendChild(vote_boss);
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
    document.getElementById("block" + block.block_id).style.display = "none";
    resulter = await block_click(block_id);

    if (resulter == "ok") {
      temp_box.push(block.block_id);
      continue;
    }
  }
  fetching = false;
  
  document.getElementById("loading").style.display="block"
  if(data.data.length<5){
    document.getElementById("loading").style.display = "none";
  }

  for(a_box of temp_box){
    document.getElementById("block"+a_box).style.display="block"
  }
};

//發文
document
  .getElementById("block_submit_btn")
  .addEventListener("click", async () => {
    document.getElementById("block_guard").innerHTML="";
    let type = document.getElementById("blockor_type").value;
    let content = document.getElementById("blockor_content").value;
    let time = moment().format("YYYY-MM-DD HH:mm:ss");
    let tags = tag_appender();
    let vote_box=[]
    if(type=="SECRET" && anonymous){
      document.getElementById("block_guard").innerHTML =
        "Tips: You cannot anonymous with secret";
      return;
    }
    if(type=="SECRET" && content.indexOf("#")!=-1){
      document.getElementById("block_guard").innerHTML =
        "Tips: You cannot use tags in secret mode";
      return
    }
    if(anonymous){
      type = "Anonymous";
      tags = "Anonymous";
    }else{tags=null}
    if (!content) {
      return;
    }
    if (vote_up) {
      let votes = document.getElementsByClassName("option_input");
      for (vote of votes) {
        if (vote.value == "") {
          continue;
        }
        vote_box.push(vote.value);
      }
      if (vote_box.length == 0) {
        console.log("nothing to vote!");
        vote_box=null
      }
    }
    const options = {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        type: type,
        content: content,
        time: time,
        tags: tags,
        vote_box: vote_box,
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
      if(vote_up){
        document.getElementById("voter").style.display = "none";
        vote_up=false
      }
      document.getElementById("blockor_content").value = "";
      document.getElementById("blockor_content").style.height="37px";
      exp_mod("block_creater");
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
    exp_mod("block_destroy");
    return;
  }
  deleting = false;
};

//留言 召喚!
//限制數量
block_click = async (id) => {
  let block_id = id.split("block")[1];
  const response = await fetch("/api/message?block_id=" + block_id);
  const result = await response.json();
  if (result.ok) {
    let guest_message = document.createElement("div");
    guest_message.setAttribute("id", "message_box" + block_id);
    guest_message.setAttribute("class", "message_box");
    let counter = 0
    for (a_message of result.ok) {
      let one_mess = document.createElement("div");
      one_mess.setAttribute("class", "one_mess");
      let score = document.createElement("div");
      if(parseInt(a_message.given_score)>0){
        score.appendChild(document.createTextNode("+"+a_message.given_score));
        score.style.color="#f70307"
      }else if (parseInt(a_message.given_score) < 0){
        score.appendChild(document.createTextNode(a_message.given_score));
        score.style.color="#09eb5b"
      }else{score.appendChild(document.createTextNode("+0"));}
      counter += parseInt(a_message.given_score);

      let mess_avatar = document.createElement("img");
      mess_avatar.setAttribute("onclick","display_member_info(this.id)")
      mess_avatar.setAttribute("id","mess_avatar"+a_message.member_id)
      mess_avatar.setAttribute("class", "mess_avatar");
      mess_avatar.setAttribute(
        "onerror",
        "this.onerror=null;this.src='/img/ghost-regular-24.png';"
      );
      mess_avatar.setAttribute(
        "src",
        "https://d3nvrufajko3tj.cloudfront.net/avatar_" + a_message.member_id
      );

      let who = document.createElement("p");
      who.setAttribute("class", "message_who");
      who.appendChild(document.createTextNode(a_message.account + " : "));

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
      one_mess.appendChild(score)
      one_mess.appendChild(who);
      one_mess.appendChild(say);
      one_mess.appendChild(nice_commenter);
      one_mess.appendChild(nice_count);
      one_mess.appendChild(time_box);
      guest_message.appendChild(one_mess);
    }
    if(parseInt(counter)>0){
      document.getElementById("block_counter" + block_id).innerHTML = "+"+counter;
      document.getElementById("block_counter" + block_id).style.color="#f70307";
    }else if (parseInt(counter) < 0) {
      document.getElementById("block_counter" + block_id).innerHTML = counter;
      document.getElementById("block_counter" + block_id).style.color="#09eb5b"
    }else{document.getElementById("block_counter" + block_id).innerHTML = "+0";}
    
    document.getElementById("block" + block_id).appendChild(guest_message);
    return "ok";
  } else {
    console.log("get message fail");
  }
};

//Block_Messages->POST
leave_message = async (message_block_id) => {
  let block_id = message_block_id.split("mess_btn")[1];
  let message = document.getElementById("messes" + block_id);
  let score = document.getElementById("score"+block_id).innerHTML

  if (!message.value) {
    return;
  }
  let time = moment().format("YYYY-MM-DD HH:mm:ss");
  //請上傳block_id,message,time
  const options = {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({
      block_id: block_id,
      message: message.value,
      time: time,
      score:parseInt(score),
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
    mess_avatar.setAttribute("id", "mess_avatar"+result.member_id);
    mess_avatar.setAttribute("onclick","display_member_info(this.id)")
    mess_avatar.setAttribute(
      "onerror",
      "this.onerror=null;this.src='/img/ghost-regular-24.png';"
    );
    mess_avatar.setAttribute(
      "src",
      "https://d3nvrufajko3tj.cloudfront.net/avatar_" + result.member_id
    );

    //score
    let block_counter = document.getElementById("block_counter" + block_id);
    let given_score = document.createElement("div")
    if (parseInt(score) > 0) {
      given_score.appendChild(document.createTextNode("+" + score));
      given_score.style.color = "#f70307";
    } else if (parseInt(score) < 0) {
      given_score.appendChild(document.createTextNode(score));
      given_score.style.color = "#09eb5b";
    } else {
      given_score.appendChild(document.createTextNode("+0"));
    }


    block_counter.innerHTML = parseInt(block_counter.innerHTML)+parseInt(score)
    if(parseInt(block_counter.innerHTML)>0){
      block_counter.style.color="#f70307"
      block_counter.innerHTML = "+"+(block_counter.innerHTML);
    }else if(parseInt(block_counter.innerHTML)<0){
      block_counter.style.color = "#09eb5b"

    }else{
      block_counter.style.color="#1cbfff"
      block_counter.innerHTML = "+" + block_counter.innerHTML;
    }

    //who
    let who = document.createElement("p");
    who.setAttribute("class", "message_who");
    who.appendChild(document.createTextNode(result.account + " : "));

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
    a_message.appendChild(given_score)
    a_message.appendChild(who);
    a_message.appendChild(say);
    a_message.appendChild(nice_commenter);
    a_message.appendChild(nice_count);
    a_message.appendChild(time_box);

    target.appendChild(a_message);
    message.value = "";
    document.getElementById("score" + block_id).innerHTML=0;
    exp_mod("message")
    return;
  }
};

//讚
gooder = async (id) => {
  let target = id.split("good")[1];
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
    exp_mod("good_bad")
    let add_this = document.getElementById("good_count" + target);
    if (add_this.innerHTML == "") {
      add_this.innerHTML = "1";
      return;
    }
    add_this.innerHTML = parseInt(add_this.innerHTML) + 1;
  } else {
    console.log("good fail",result.error);
    

  }
};

//boo
badder = async (id) => {
  let target = id.split("bad")[1];
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
    exp_mod("good_bad");
    let add_this = document.getElementById("bad_count" + target);
    if (add_this.innerHTML == "") {
      add_this.innerHTML = "1";
      return;
    }
    add_this.innerHTML = parseInt(add_this.innerHTML) + 1;
  } else {
    console.log("bad fail",result.error);
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
    if(ob_mode==false){
    page += 5;
    //目前數量一次3篇 好好規劃數量~
    fetching = true;
    //從這裡做分野 抓某特定人的所有tag(包含自己)，但請考量隱私問題 不要牴觸朋友權限
    result = search_build_blocks();
    if (result.error) {
      console.log(result.error)
    }
  }else{
    ob_page+=5
    fetching=true
    result = observe();

  }
  }
});

upload_block_img_preview = () => {
  document.getElementById("img_pre_box").style.display = "flex";
  let reader = new FileReader();
  reader.readAsDataURL(document.getElementById("upload_block_img").files[0]);
  reader.onload = function (oFREvent) {
    document.getElementById("upload_preview").src = oFREvent.target.result;
  };
};

block_img_uploader = async (block_data) => {
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
  const options = { method: "POST", body: data };
  const response = await fetch("/api/images", options);
  const result = await response.json();
  if (result.ok) {
    console.log("Upload OK!");
    document.getElementById("upload_block_img").value = "";
  }
};

cancel_upload = () => {
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

  if (result.ok) {
    exp_mod("good_message");
    let add_this = document.getElementById("how_nice" + target);
    if (add_this.innerHTML == "") {
      add_this.innerHTML = "1";
      return;
    }
    add_this.innerHTML = parseInt(add_this.innerHTML) + 1;
  } else {
    console.log("good fail",result.error);
  }
};

let anonymous = false;
anonymous_mode = () => {
  document.getElementById("block_guard").innerHTML="";
  let blockor = document.getElementById("blockor_inner");
  let inner = document.getElementById("blockor_content");
  if (!anonymous) {
    document.getElementById("blockor_type").value="PUBLIC"
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


observe = async() => {
  let loading = document.getElementById("loading")
  console.log("observe!")
  if(ob_mode==false){
    block_box.innerHTML = "";
    member_blocks.scrollTop = 0;
  }
  ob_mode = true;
  let target = document.getElementById("tag_observer").value;
  if(target=="" || target==null){
    loading.style.display = "none";
    console.log("@@")
    return
  }
  fetching = true;
  loading.style.display = "block";
  
  const response = await fetch("/api/blocks?page=" + ob_page+"&key="+target);
  const result = await response.json();
  if(result.ok){
    block_builder(result)
    return
  }
  loading.style.display="none"
  ob_page=0
}

document.getElementById("observer_btn").addEventListener("click",()=>{
      
      block_box.innerHTML = "";
      member_blocks.scrollTop = 0;
      ob_page=0
})


display_member_info = async(member_block_id) => {
  let member_id
  if(member_block_id.split("friend_avatar")[0]==""){
    member_id = member_block_id.split("friend_avatar")[2];
  }else if (member_block_id.split("mess_avatar")[0]=="") {
    member_id = member_block_id.split("mess_avatar")[1];
  } else {
    member_id = member_block_id.split("block_header")[1];
  }

  let mask = document.getElementById("mask")
  let user_sq = document.getElementById("user_info_sq")
  let avatar = document.getElementById("popup_avatar")
  avatar.setAttribute(
    "onerror",
    "this.onerror=null;this.src='/img/ghost-regular-24.png';"
  );
  mask.style.display="block";
  user_sq.style.display="block";
  avatar.src = "https://d3nvrufajko3tj.cloudfront.net/avatar_"+member_id;

  const response = await fetch(
    "/api/get_user_sp?member_id=" + member_id
  );
  const result = await response.json();
  if(result.ok){

    //開始渲染畫面
    let user_info = result.data
    let friendship = result.is_friend
    let mood = user_info.mood
    if(!mood){
      mood = "沒有任何紀錄:)"
    }
    document.getElementById("pop_account").innerHTML=user_info.account
    document.getElementById("pop_birthday").innerHTML =
      moment(user_info.birthday).format("YYYY MMM Do") +
      "(" +
      moment(user_info.birthday).fromNow().split(" years ago") +
      "歲" +
      ")";
    document.getElementById("pop_first").innerHTML=moment(user_info.first_signup).format("YYYY MMM Do")
    document.getElementById("pop_last").innerHTML=moment(user_info.last_signin).subtract(8, "hours").fromNow()
    document.getElementById("pop_mood").innerHTML=mood
    document.getElementById("pop_level").innerHTML =
      parseInt((((8 * user_info.exp) / 50 + 1) ** 0.5 + 1) / 2) +
      "(總經驗值" +
      user_info.exp +
      ")";

    let pop_add = document.getElementById("pop_add")
    let pop_follow = document.getElementById("pop_follow")

    if(friendship){
      pop_add.style.display = "block";
      // pop_follow.style.display = "block";

      //開始多項判斷 首先觀察status
      if(friendship.status==0){
        pop_add.innerHTML="已是好友"
        pop_add.style.color = "#1cbfff";
        pop_add.setAttribute("onclick", "return false;");
        return
      }
      if(friendship.request_from==my_id){
        pop_add.innerHTML="已送出邀請"
        pop_add.style.color="#1cbfff"
        pop_add.setAttribute("onclick", "return false;");
        return
      }
      pop_add.innerHTML = "接受邀請";
      pop_add.style.color = "#09ed5d";
      pop_add.setAttribute(
        "onclick",
        "befriend('"+"friend_ok_"+friendship.friend_ship_id+"')"
      );
      return
    }
    if (me == user_info.account) {
      console.log("這是自己");
      return
    }
    pop_add.style.display = "block";
    pop_add.style.color = "#1cbfff";
    pop_add.innerHTML = "加好友";
    pop_add.setAttribute(
      "onclick",
      "pop_add_friend('" + user_info.account + "')"
    );
  }
}

close_pop = () => {
    let pop_add = document.getElementById("pop_add");
    let pop_follow = document.getElementById("pop_follow");
    document.getElementById("mask").style.display="none";
    document.getElementById("user_info_sq").style.display="none";
    pop_add.style.display = "none";
    // pop_follow.style.display = "none";

}

up_score = (id) => {
  let target = document.getElementById("score"+id.split("up_vote")[1])
  if(target.innerHTML==5){
    return
  }
  target.innerHTML=parseInt(target.innerHTML)+1
}

down_score = (id) => {
  let target = document.getElementById("score" + id.split("down_vote")[1]);
    if (target.innerHTML == -5) {
      return;
    }
    target.innerHTML = parseInt(target.innerHTML) - 1;
}