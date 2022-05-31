let me
let my_id

document.addEventListener("DOMContentLoaded", async() => {
  result = await check_user_identity();//1 個人資料
  me = result.data.account
  my_id = result.data.member_id
  init_render_user(result)
  all_user_tags = await get_all_tags_of_member();//2 自身tag
  init_render_tags(await all_user_tags.tag)
  search_build_blocks();//3
  textarea_holder();
});

document.getElementById("signout").addEventListener("click", async () => {
  console.log("signout!");
  const options = { method: "DELETE" };
  const response = await fetch("/api/member", options);
  const result = await response.json();
  if (result.ok) {
    socket.emit("logout", {
      account: me,
    });
    window.location.href = "/";
  } else {
    console.log("signout fail");
  }
});

//檢查狀態
check_user_identity = async() =>{
  const response = await fetch("/api/member");
  const result = await response.json();
  if(result.ok){
      return result

  }else{console.log(result.error)}
}


init_render_tags = (tags) => {
  for (tag in tags) {
    let tag_box = document.getElementById("tag_box");
    let a_tag = document.createElement("div");
    let del_tag = document.createElement("img")
    let tag_name = document.createElement("a");
    a_tag.setAttribute("class", "a_tag");
    a_tag.setAttribute("id", "tag"+tags[tag].member_tag_id);
    del_tag.setAttribute("src","/img/icon_close.png")
    del_tag.setAttribute("class","del_tag")
    del_tag.setAttribute("id", "tag_img"+tags[tag].member_tag_id);
    del_tag.setAttribute("onclick","del_tag(this.id)")
    let tag_content = document.createTextNode(tags[tag].name);
    tag_name.setAttribute("href", "/tag/" + tags[tag].name);
    if(tags[tag].name=="Anonymous"){
        tag_name.setAttribute("class", "a_prime_name");
    }else{
      tag_name.setAttribute("class", "a_tag_name");
      tag_name.setAttribute("id", "a_tag_name" + tags[tag].member_tag_id);
  }
    tag_name.appendChild(tag_content)
    a_tag.appendChild(tag_name);
    a_tag.appendChild(del_tag)
    tag_box.appendChild(a_tag);
  }
};

init_render_user = (user_data) => {
  //個資畫面呈現
  let account = document.createTextNode(user_data.data.account);
  let email = document.createTextNode(user_data.data.email)
  let first_signup = document.createTextNode(user_data.data.first_signup.slice(0,17))
  let exp = user_data.data.exp
  let member_img = user_data.data.member_img
  let mood = user_data.data.mood
  let user_account = document.getElementById("user_account");
  let user_mail = document.getElementById("user_mail");
  let user_firstday = document.getElementById("user_firstday");
  //個人圖片
  if(member_img!=null){
    document.getElementById("user_main_avatar").setAttribute("src", "https://d3nvrufajko3tj.cloudfront.net/avatar_"+my_id);
  }
  if(mood==null){
    mood_text.innerHTML = "今天心情如何?";
  }else{
    mood_text.innerHTML=mood
  }


  user_account.appendChild(account)
  user_mail.appendChild(email)
  user_firstday.appendChild(first_signup)
  render_level(exp)
}


upload_user_img = async() => {

  let file = document.getElementById("upload_user_avatar").files;
  let data = new FormData();
  console.log("start upload")
  data.append("image",file[0])
  data.append("type","avatar")
  data.append("target_id",null)
  const options = { method: "POST", body: data };
  const response = await fetch("/api/images", options);
  const result = await response.json();
  if (result.ok) {
    console.log("Upload OK!");
    document.getElementById("user_main_avatar").setAttribute("src", "https://d3nvrufajko3tj.cloudfront.net/avatar_"+my_id);
  }
}



    // <div id="user_mood" onclick="change_mood()">
    //     <p id="mood_text">今天心情如何?</p>
    //     <input type="text" id="mood_input">
    // </div>

let mood_text = document.getElementById("mood_text");
let mood_input = document.getElementById("mood_input");
let mood_now

change_mood = () => {
  mood_text.style.display="none"
  mood_input.style.display="block"
  mood_input.focus()
  mood_input.value = mood_text.innerHTML
  mood_now = mood_text.innerHTML;
};

mood_input.addEventListener("focusout",() => {
  new_mood = mood_input.value
  mood_text.style.display = "block";
  mood_input.style.display = "none";
  if(mood_now==new_mood){
    return
  }
  if(new_mood=="" || new_mood==null || !new_mood){
    return
  }
  mood_text.innerHTML=new_mood
  
  upload_mood(new_mood)
})


upload_mood = async(content) => {
    const options = {
    method: "PATCH",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({
      category: "mood",
      content: content,
    }),
  };
  const response = await fetch("/api/member", options);
  const result = await response.json();
  if(result.ok){
    return
  }
  console.log("update error")
}