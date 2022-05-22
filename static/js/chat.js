
const socket = io();
let is_on = []//現在啟用中的聊天 關閉才移除 縮小不會
let friend_list = {}//好友清單與上現狀態
let chatting_list={}//對方帳號與其房名對{account:room}

//放心安不知道有沒有用的東西 = ~ =
window.onbeforeunload = () => {
  socket.emit("logout", {
    account: me,
  });
};

//上線宣告請順便攜帶自己的好友名單
//定時打socketio刷新cache的timeout表明自己online，並且拿到最新好有上線狀態
const im_still_here = setInterval(async() => {
    //抓取已是好友的account清單
    let friends = document.getElementsByClassName("friend_avatar")
    for(friend of friends){
        friend_account = friend.id.split("friend_avatar")[1]
        friend_list[friend_account] = "off"
    }
    socket.emit("awake", {
    type: "awake_call",
    account: me,
    check_who_is_awake_too: friend_list,
    });

}, 5000);

socket.on("awake_result", (data) => {
  //會傳資料會用來顯現好友清單的上線狀態
  //上線的人伺服器也會有sid就可以直接加房間!
  for (friend in data) {
    if (data[friend] == "on") {
      friend_list[friend] = "on";
      document
        .getElementById("friend_avatar" + friend)
        .setAttribute("color", "#1cbfff");
        call = document.getElementById("mess_to" + friend);
        call.setAttribute("animation", "none");
    }else if(data[friend]=="on_calling"){
        if (is_on.includes(friend)){
            call = document.getElementById("mess_to" + friend);
            call.setAttribute("animation", "none");
            document
              .getElementById("friend_avatar" + friend)
              .setAttribute("color", "#1cbfff");
            return
        }
        document
          .getElementById("friend_avatar" + friend)
          .setAttribute("color", "#1cbfff");
        call = document.getElementById("mess_to" + friend)
        call.setAttribute("animation","tada")
    } else {
      friend_list[friend] = "off";
      document
        .getElementById("friend_avatar" + friend)
        .setAttribute("color", "#f71523");
    }
  }
});

socket.on("connected",(data)=>{
    return
    //連帶動作
})

start_chat = (account) =>{
  //只有還沒開始的聊天室的朋友才能執行
  //這裡務必檢查已經開啟的聊天室，若是已開啟將不理會
  chat_holder = document.getElementById("chat_holder");
  account = account.split("mess_to")[1];
  //前端上線檢查器
  // if (friend_list[account] == "off" || !friend_list[account]) {
  //   console.log("No user online!");
  //   return;
  // }
  //避免重複開聊天box
  if (is_on.includes(account)) {
    console.log("this room is already on");
    return;
  }

  //同意開始/開新，隱藏其他房間，並且創造
  is_on.push(account);

  //聊天房間open
  a_room = document.createElement("div");
  a_room.setAttribute("class", "a_room");
  a_room.setAttribute("id", "a_room" + account);

  //標籤
  chat_tag = document.createElement("div");
  tag_who = document.createElement("div");
  tag_who.setAttribute("class", "tag_who");
  tag_who.appendChild(document.createTextNode(account));
  chat_tag.appendChild(tag_who);
  chat_tag.setAttribute("class", "chat_tag");

  //放大
  plus_tag = document.createElement("img");
  plus_tag.setAttribute("src", "img/plus.png");
  plus_tag.setAttribute("class", "plus_tag");
  plus_tag.setAttribute("id", "plus_tag" + account);
  plus_tag.setAttribute("onclick", "plus_this(this.id)");
  //縮小
  min_tag = document.createElement("img");
  min_tag.setAttribute("src", "img/minus.png");
  min_tag.setAttribute("class", "min_tag");
  min_tag.setAttribute("id","min_tag"+account)
  min_tag.setAttribute("onclick","min_this(this.id)")

  close_tag = document.createElement("img");
  close_tag.setAttribute("src", "img/off.png");
  close_tag.setAttribute("class", "close_tag");
  close_tag.setAttribute("id", "close_tag" + account);
  close_tag.setAttribute("onclick", "end_chat(this.id)");

  tag_tool = document.createElement("div");
  tag_tool.setAttribute("class", "tag_tool");
  tag_tool.appendChild(plus_tag)
  tag_tool.appendChild(min_tag);
  tag_tool.appendChild(close_tag);
  chat_tag.appendChild(tag_tool);

  //完成上方
  a_room.appendChild(chat_tag);

  // //system message
  // sys_mess = document.createElement("div")
  // sys_mess.setAttribute("class","sys_mess")
  // sys_mess.appendChild(document.createTextNode("可以開始聊天囉"));

  //聊天bar_box
  bar_box = document.createElement("div");
  bar_box.setAttribute("class", "bar_box");
  bar_box.setAttribute("id","bar_box"+account)

  //world_of_words
  world_of_words = document.createElement("world_of_words");
  world_of_words.setAttribute("class", "world_of_words");
  world_of_words.setAttribute("id", "world_of_words" + account);
  a_room.appendChild(world_of_words);

  //聊天bar
  chat_input = document.createElement("input");
  chat_input.setAttribute("type", "text");
  chat_input.setAttribute("class", "chat_input");
  chat_input.setAttribute("id", "chat_input" + account);
  chat_input.setAttribute("placeholder", "message...");

  //聊天送出btn
  chat_send = document.createElement("box-icon");
  chat_send.setAttribute("name", "send");
  chat_send.setAttribute("id", "send_btn" + account);
  chat_send.setAttribute("onclick", "send_chat(this.id)");
  chat_send.setAttribute("color", "#1cbfff");

  bar_box.appendChild(chat_input);
  bar_box.appendChild(chat_send);

  // a_room.appendChild(sys_mess);

  a_room.appendChild(bar_box);

  chat_holder.appendChild(a_room);

  init_chat_with(account);
}


init_chat_with = (account) =>{
    socket.emit("init_room",{account:account,me:me})
    socket.on("init_result",(result)=>{
        if(result.ok){
            chatting_list[account]=result.room
            return
        }
        console.log(result.error)
    })
}



//監聽:對方訊息
//藉由內容來知道貼到哪個視窗
socket.on("message",(data)=>{
    let say_box = document.createElement("p");
    let say = document.createTextNode(data.content);
    if(data.to==me){
        //對方的訊息
        who = data.from;
        say_box.setAttribute("class","who_mess")
    }else{
        //自己發的
        who = data.to;
        say_box.setAttribute("class","my_mess")
    }
    let talks = document.getElementById("world_of_words" + who);
    //自己靠左
    say_box.appendChild(say)
    if(!talks){
        return
    }
    talks.appendChild(say_box)
    talks.scrollTop =talks.scrollHeight;

})

//送出:訊息
send_chat = (btn_id) =>{
    //藉由id來知道是給誰的訊息
    account = btn_id.split("send_btn")[1]
    if(!chatting_list[account]){
        return
    }
    room = chatting_list[account]
    message = document.getElementById("chat_input"+account).value
    socket.emit("send",{"type":"message","to":account,"from":me,"content":message,"room":room})
    document.getElementById("chat_input" + account).value = "";
}





end_chat = (account) =>{
    let who = account.split("close_tag")[1]
    room = chatting_list[who]
    socket.emit("left",{"room":room,"me":me,"account":who})

    //關閉視窗
    op_ele = document.getElementById("a_room"+who)
    op_ele.remove();

    // is_on.pop(who)
    index = is_on.indexOf(who)
    if (index >= 0) {
      is_on.splice(index, 1);
    }
}

//系統訊息(進入離開或其他訊息)
socket.on("status",(result)=>{
    console.log(result)
})

min_this = (id) =>{
    let witch = id.split("min_tag")[1]
    let room = document.getElementById("a_room"+witch)

    room.style.maxHeight = "150px"

    return
}

plus_this = (id) => {
  let witch = id.split("plus_tag")[1];
  let room = document.getElementById("a_room" + witch);

  room.style.maxHeight = "450px";
  return;
};