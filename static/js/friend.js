

document.addEventListener("DOMContentLoaded", async () => {
  let result;
  setTimeout(async () => {
  result = await check_relation();
  render_friend_status(await result)
  }, 1500);
});

document.getElementById("friend_search_btn").addEventListener("click", async () => {
    let invite = document.getElementById("friend_searcher").value;
    if (!invite) {
      console.log("you insert nothing");
      return;
    }

    //步驟先確認彼此是否已是朋友
    result = await friend_invite(invite);

    //認證完畢 開始建立好友關係
    if(result.ok=="FAST"){
        console.log("quick build relation",result)
        //這裡
        let friend_ship_id =result.data[0]["friend_ship_id"]
        forge_relation(friend_ship_id)
        result["type"]="friend"
        result["content"] = "新好友成立"
        result["time"] = moment().format("YYYY-MM-DD HH:mm:ss");
        send_notifi(result)
        return
    }else{
      console.log("其他狀況", result);
      if(result.ok){
        console.log("動態render好友",result)
        let request_list = document.getElementById("request_list");
        content = document.createTextNode(result.someone_else);
        a_content = document.createElement("div");
        a_content.appendChild(content);
        request_list.appendChild(a_content);
        document.getElementById("friend_searcher").value=""

        result["type"] = "friend";
        result["content"] = "你有一則好友邀請來自:" + me;
        result["time"] = moment().format("YYYY-MM-DD HH:mm:ss");
        send_notifi(result)
      }
  }
});




friend_invite = async (invite) => {
  let check = await check_relation(invite);
  if (check.error) {
    return check.error
  }

  const options = {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ who: invite }),
  };
  const response = await fetch("/api/friend", options);
  const result = await response.json();
  return result

};



check_relation = async (invite) => {
  const response = await fetch("/api/friend?who=" + invite);
  const result = await response.json();
  return result;
};



render_friend_status=(data)=>{
    for(one_data of data.ok){
      // console.log(one_data)
        let req_f = one_data.req_from
        let req_t = one_data.req_to
        let status = one_data.status
        let friend_ship_id = one_data.friend_ship_id;
        if(req_t==me && status=="1"){
            render_wait_ur_accept(req_f,friend_ship_id)

        }else if(req_f==me && status=="1"){
            render_ur_request(req_t,friend_ship_id)

        }else{
            render_ur_friend(req_f, req_t, status, friend_ship_id);
        }
    }
}


render_wait_ur_accept = (req_f,friend_ship_id) =>{
    let waiting_list = document.getElementById("waiting_list");
    
    content = document.createTextNode(req_f);
    req_f = document.createElement("p")
    req_f.setAttribute("id","req_f"+friend_ship_id)
    req_f.appendChild(content)
    a_content = document.createElement("div");
    a_content.setAttribute("class","a_wait")
    a_content.setAttribute("id","a_wait"+friend_ship_id)
    check_ok = document.createElement("box-icon")
    check_ok.setAttribute("name","check")
    check_ok.setAttribute("class","check")
    check_ok.setAttribute("color","#1cbfff")
    check_ok.setAttribute("id","friend_ok_"+friend_ship_id)
    check_ok.setAttribute("onclick","befriend(this.id)")

    check_no = document.createElement("box-icon")
    check_no.setAttribute("name","x")
    check_no.setAttribute("class","x")
    check_no.setAttribute("color","#ff0402")
    check_no.setAttribute("id", "friend_no_" + friend_ship_id);
    check_no.setAttribute("onclick", "byefriend(this.id)");

    // <box-icon name='x' color='#ff0402' ></box-icon>
    a_content.appendChild(req_f);
    a_content.appendChild(check_ok)
    a_content.appendChild(check_no)
    waiting_list.appendChild(a_content);
}

render_ur_request = (req_t, friend_ship_id) => {
  let request_list = document.getElementById("request_list");
  content = document.createTextNode(req_t);
  a_content = document.createElement("div");
  a_content.appendChild(content);
  request_list.appendChild(a_content);
};

//載入時render好友
render_ur_friend = (req_f, req_t, status, friend_ship_id) => {
  let friend_list = document.getElementById("friend_list");
  if (me == req_f) {
    friend = req_t;
  } else {
    friend = req_f;
  }
  a_friend = document.createTextNode(friend);
  friend_box = document.createElement("div");

  // <box-icon name="user" type="solid" color="#1cbfff"></box-icon>;
  friend_avatar = document.createElement("box-icon");
  friend_avatar.setAttribute("name", "user");
  friend_avatar.setAttribute("color", "#f71523");
  friend_avatar.setAttribute("id","friend_avatar"+friend)
  friend_avatar.setAttribute("class", "friend_avatar");


  friend_box.setAttribute("id","friend_box"+friend_ship_id)
  friend_box.setAttribute("class", "friend_box");

  mess_img = document.createElement("box-icon")
  mess_img.setAttribute("class","mess_img")
  mess_img.setAttribute("color", "#1cbfff");
  mess_img.setAttribute("name", "message-square-dots");
  mess_img.setAttribute("id","mess_to"+friend)
  mess_img.setAttribute("onclick","start_chat(this.id)")

  // <box-icon name='user-x' color='#1cbfff' ></box-icon>
  bye_friend = document.createElement("box-icon")
  bye_friend.setAttribute("class", "bye_f");
  bye_friend.setAttribute("name","user-x")
  bye_friend.setAttribute("color","#f71523")
  bye_friend.setAttribute("id","del_fr"+friend_ship_id)
  bye_friend.setAttribute("onclick","delete_friend(this.id)")

  friend_box.appendChild(friend_avatar);
  friend_box.appendChild(a_friend);
  friend_box.appendChild(mess_img);
  friend_box.appendChild(bye_friend);
  friend_list.appendChild(friend_box);
};

//點擊同意時render好友
befriend = async(id)=>{
  let friend_ship_id = id.split("friend_ok_")[1]
  let result = await forge_relation(friend_ship_id)
  if(result.ok){
    console.log("start be friend render")
    let friend = document.getElementById("req_f"+friend_ship_id).innerHTML;
    let friend_list = document.getElementById("friend_list");
    a_friend = document.createTextNode(friend);
    friend_box = document.createElement("div");


    friend_avatar = document.createElement("box-icon");
    friend_avatar.setAttribute("name", "user");
    friend_avatar.setAttribute("color", "#f71523");
    friend_avatar.setAttribute("id", "friend_avatar" + friend);
    friend_avatar.setAttribute("class", "friend_avatar");

    mess_img = document.createElement("box-icon");
    mess_img.setAttribute("class", "mess_img");
    mess_img.setAttribute("color", "#1cbfff");
    mess_img.setAttribute("name", "message-square-dots");
    mess_img.setAttribute("id", "mess_to" + friend);
    mess_img.setAttribute("onclick", "start_chat(this.id)");

    bye_friend = document.createElement("box-icon");
    bye_friend.setAttribute("class","bye_f")
    bye_friend.setAttribute("name", "user-x");
    bye_friend.setAttribute("color", "#f71523");
    bye_friend.setAttribute("id", "del_fr" + friend_ship_id);
    bye_friend.setAttribute("onclick", "delete_friend(this.id)");


    friend_box.setAttribute("id", "friend_box" + friend_ship_id);
    friend_box.setAttribute("class","friend_box")
    friend_box.appendChild(friend_avatar);
    friend_box.appendChild(a_friend);
    friend_box.appendChild(mess_img);
    friend_box.appendChild(bye_friend);
    friend_list.appendChild(friend_box);
    document.getElementById("a_wait" + friend_ship_id).remove();
  }
}

//拒絕與刪除好友都走這
byefriend = async(id) =>{
  let friend_ship_id = id.split("friend_no_")[1];
  let friend_account = document.getElementById("req_f"+friend_ship_id).innerHTML
  let result = await not_friend(friend_ship_id)
  if (result.ok) {
    console.log("start bye friend render");
    document.getElementById("a_wait" + friend_ship_id).remove();
    let data = {
      me: my_id,
      someone_else: friend_account,
      type: "deny_friend_request",
      content: me + " 拒絕了你的好友邀請。Sad!",
      time: moment().format("YYYY-MM-DD HH:mm:ss"),
    };
    send_notifi(data)

  } 
}





forge_relation = async(friend_ship_id) =>{
  const options = {
    method: "PATCH",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ friend_ship_id:friend_ship_id }),
  };
  const response = await fetch("/api/friend", options);
  const result = await response.json();
  if(result.ok && result.datachanged!=0){
      console.log("new friend accepted!",result)
      return {"ok":true}
  }
  console.log("forge friend error",result)
}

not_friend = async(friend_ship_id) =>{
  const options = {
    method: "DELETE",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ friend_ship_id: friend_ship_id }),
  };
  const response = await fetch("/api/friend", options);
  const result = await response.json();
  if (result.ok && result.datachanged != 0) {
    return { ok: true };
  }
  console.log("forge friend error", result);
}

delete_friend = async(id) =>{
  let fr_id = id.split("del_fr")[1]
  result = await not_friend(fr_id)
  if(result.ok){
    document.getElementById("friend_box"+fr_id).remove()
    return
  }
  console.log("del friend fail")

}