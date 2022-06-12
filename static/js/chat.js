
const socket = io();
let is_on = []
let friend_list = {}
let chatting_list={}

window.onbeforeunload = () => {
  socket.emit("logout", {
    account: me,
  });
};


const im_still_here = setInterval(async() => {
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
  chat_holder = document.getElementById("chat_holder");
  account = account.split("mess_to")[1];
  if (is_on.includes(account)) {
    console.log("this room is already on");
    return;
  }

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
  a_room.appendChild(bar_box);
  chat_holder.appendChild(a_room);
  document.getElementById("chat_input" + account).addEventListener("keypress",()=>{
    if (event.key === "Enter"){
      send_chat("send_btn" + account);
    }
  })
  init_chat_with(account);
}

let now_init
init_chat_with = (account) =>{
  now_init = account
    socket.emit("init_room",{account:now_init,me:me})
    socket.on("init_result",(result)=>{
        if(result.ok){
            chatting_list[now_init]=result.room
            return
        }
        let notifi={}
        notifi["me"]=my_id;
        notifi["someone_else"] = now_init
        notifi["type"]="chat request"
        notifi["content"] = me + "想找你聊天但你不在!";
        notifi["time"] = moment().format("YYYY-MM-DD HH:mm:ss");
        send_notifi(notifi)
    })
}


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
    say_box.appendChild(say)
    if(!talks){
        return
    }
    talks.appendChild(say_box)
    talks.scrollTop =talks.scrollHeight;

})

//送出:訊息
send_chat = (btn_id) =>{
      account = btn_id.split("send_btn")[1];
    if(!chatting_list[account]){
        return
    }
    if (document.getElementById("chat_input" + account).value == "") {
      return;
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

    op_ele = document.getElementById("a_room"+who)
    op_ele.remove();

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
