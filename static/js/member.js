let me
let my_id

document.addEventListener("DOMContentLoaded", async() => {
  result = await check_user_identity();
  me = result.data.account
  my_id = result.data.member_id
  init_render_user(result)
  all_user_tags = await get_all_tags_of_member();
  init_render_tags(await all_user_tags.tag)
  search_build_blocks();
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
  let account = document.createTextNode(user_data.data.account);
  let email = document.createTextNode(user_data.data.email)
  let first_signup = document.createTextNode(user_data.data.first_signup.slice(0,17))
  let exp = user_data.data.exp
  let member_img = user_data.data.member_img
  let mood = user_data.data.mood
  let user_account = document.getElementById("user_account");
  let user_mail = document.getElementById("user_mail");
  let user_firstday = document.getElementById("user_firstday");
    document.getElementById("user_main_avatar").setAttribute("src", "/images/avatar_"+my_id);
    document.getElementById("user_main_avatar").setAttribute("onerror","this.onerror=null;this.src='/img/user-regular-24.png';");
  if(mood==null){
    mood_text.innerHTML = "今天心情如何?";
  }else{
    mood_text.textContent=mood
  }
  user_account.appendChild(account)
  user_mail.appendChild(email)
  user_firstday.appendChild(first_signup)
  render_level(exp)
}


// Uploads go straight from the browser to S3 with a presigned POST, then the server
// records the image (see api/blueprints/api_images.py).
upload_image = async (file, type, target_id) => {
  const sign = await fetch("/api/images/upload", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ type: type, target_id: target_id, content_type: file.type }),
  });
  const signed = await sign.json();
  if (!signed.ok) {
    alert(signed.error === "file type not allowed" ? "只能上傳 PNG、JPEG 或 GIF 圖片" : "圖片上傳失敗");
    return false;
  }
  const form = new FormData();
  for (const [name, value] of Object.entries(signed.fields)) {
    form.append(name, value);
  }
  form.append("file", file); // S3 requires the file to be the last field
  const upload = await fetch(signed.url, { method: "POST", body: form });
  if (!upload.ok) {
    alert(file.size > 5 * 1024 * 1024 ? "圖片不能超過 5 MB" : "圖片上傳失敗");
    return false;
  }
  const done = await fetch("/api/images", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ type: type, target_id: target_id }),
  });
  const result = await done.json();
  return Boolean(result.ok);
}

upload_user_img = async() => {
  let file = document.getElementById("upload_user_avatar").files[0];
  if (!file) {
    return;
  }
  if (await upload_image(file, "avatar", null)) {
    // A new query string makes the browser fetch the new avatar instead of its cached one.
    document.getElementById("user_main_avatar").setAttribute("src", "/images/avatar_" + my_id + "?t=" + Date.now());
  }
}

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
  mood_text.textContent=new_mood
  
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