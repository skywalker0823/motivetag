//進畫面後，會主動去取得該使用者擁有的tag

document.addEventListener("DOMContentLoaded", async() => {
    let result
    setTimeout(async() => {
        result = await get_hot_tags();  
        render_hot_tags(await result);      
    }, 2000);
});





del_tag = async(tag) =>{
    console.log("進入刪除個人tag環節", tag);
    tag = tag.split("tag_img")[1]
    const options = {
      method: "DELETE",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ tag: tag }),
    };
    const response = await fetch("/api/member_tags", options);
    const result = await response.json();
    if(result.ok){
        console.log(tag)
        target = document.getElementById("tag"+tag)
        target.remove()
    }
}

document.getElementById("tag_search_btn").addEventListener("click",async()=>{
    let tag = document.getElementById("tag_searcher").value;
    if(!tag){
        console.log("you insert nothing");
        return;
    }
    result = await check_tag(tag);
    if(!result.ok){
        console.log(result.error)
        return
    }
    global_tag_adjust = await adjust_global_tag(tag)//調整global tag
    if(!global_tag_adjust.msg=="1"){
        console.log("gloal adjust fail")
        return
    }
    console.log("global tag調整完畢")
    result = await adjust_my_tag(tag);//調整會員tag
    //這裡只應該追回最新的tag name and tag id
    if(!result.ok){
        console.log("add member tag error",result.error)
        return
    }
    user_append_tag(result)
    return

})



check_tag = async(tag) =>{
    const response = await fetch("/api/find_member_tags?tag="+tag)
    const result = await response.json()
    return result
}











adjust_global_tag = async(tag) =>{
    console.log("進入調整global tag環節",tag);
    const options = {
        method: "PATCH",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ tag: tag }),
    };
    const response = await fetch("/api/tags", options);
    const result = await response.json();
    return result
}





adjust_my_tag = async(tag) =>{
    console.log("進入調整個人tag環節",tag);
    const options = {
        method: "PATCH",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ tag: tag }),
    };
    const response = await fetch("/api/member_tags", options);
    const result = await response.json();
    return result
}


get_all_tags_of_member = async() =>{
  const options = { method: "GET" };
  const response = await fetch("/api/member_tags", options);
  const result = await response.json();
  return result
}

user_append_tag=(result)=>{
    //如果有空位，將之改成此tag
    console.log("lookhere",result)
    let tag_box = document.getElementById("tag_box");
    let a_tag = document.createElement("div");
    let word = document.createElement("a")
    let del_tag = document.createElement("img");
    del_tag.setAttribute("src", "/img/icon_close.png");
    del_tag.setAttribute("class", "del_tag");
    del_tag.setAttribute("id", "tag_img"+result.member_tag_id);
    del_tag.setAttribute("onclick", "del_tag(this.id)");
    a_tag.setAttribute("class","a_tag");
    a_tag.setAttribute("id", "tag"+result.member_tag_id);
    let tag_content = document.createTextNode(result.tag);
    word.appendChild(tag_content)
    word.setAttribute("class","a_tag_name")
    word.setAttribute("href","/tag/"+result.tag)
    a_tag.appendChild(word);
    a_tag.appendChild(del_tag);
    tag_box.appendChild(a_tag);
    return
}


//global top10 tag.get OK
get_hot_tags=async()=>{
  const options = { method: "GET" };
  const response = await fetch("/api/tag", options);
  const result = await response.json();
  return result
}

render_hot_tags = (hot_tags) =>{
    let hot_box = document.getElementById("hot_box")
    let rank = 1
    for(hot_tag of hot_tags.hot_tags){
        let a_tag = document.createElement("div")
        let tag_name = document.createElement("div")
        let tag_pop = document.createElement("div")
        let ranking = document.createElement("div")
        let name = document.createTextNode(hot_tag.name)
        let pop = document.createTextNode(hot_tag.popularity)
        tag_name.setAttribute("onclick","append_from_hot(this.innerHTML)")
        tag_name.setAttribute("class","a_hot_tag")
        a_tag.setAttribute("class","a_hot_box")
        ranking.appendChild(document.createTextNode(rank));
        tag_name.appendChild(name)
        tag_pop.appendChild(pop)
        a_tag.appendChild(ranking)
        a_tag.appendChild(tag_name)
        // a_tag.appendChild(tag_pop)
        hot_box.appendChild(a_tag)
        rank+=1
    }

}

append_from_hot = async(tag) =>{
    result = await check_tag(tag);
    if(!result.ok){
        console.log(result.error)
        return
    }
    global_tag_adjust = await adjust_global_tag(tag)//調整global tag
    if(!global_tag_adjust.msg=="1"){
        console.log("gloal adjust fail")
        return
    }
    console.log("global tag調整完畢")
    result = await adjust_my_tag(tag);//調整會員tag
    //這裡只應該追回最新的tag name and tag id
    if(!result.ok){
        console.log("add member tag error",result.error)
        return
    }
    user_append_tag(result)
    return
}