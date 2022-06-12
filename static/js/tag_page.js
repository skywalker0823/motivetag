let key_word
document.addEventListener("DOMContentLoaded",async() => {
    key_word = window.location.pathname.split("/tag/")[1]
    key_word = decodeURI(key_word)
    let tag_title = document.getElementById("the_word")
    let key_box = document.createElement("div")
    key_box.setAttribute("class","key_box")
    key_box.appendChild(document.createTextNode("#"+key_word))
    tag_title.appendChild(key_box)
    bricks = await init_tag_page(key_word)
    //我吃文章資料 等上面餵我謝謝
    building_posts(await bricks) 
});

init_tag_page = async(key_word) =>{
  const response = await fetch("/api/tag_page?keyword=" + key_word);
  const result = await response.json();
  if(result.ok){
    console.log(result)
    return result["data"]
  }
}

back = () =>{
  window.location.href="../"
}


po_up = () =>{
    mask = document.getElementById("mask");
    po_sq = document.getElementById("po_sq");
    mask.style.display = "block";
    po_sq.style.display = "flex";
}
close_po = () => {
    mask = document.getElementById("mask");
    po_sq = document.getElementById("po_sq");
    mask.style.display = "none";
    po_sq.style.display = "none";
}


send_po = async() => {
  let title = document.getElementById("po_title").value
  let content = document.getElementById("po_content").value
  let classifi
  let time = moment().format("YYYY-MM-DD HH:mm:ss");
  let tag_name = decodeURIComponent(window.location.pathname.split("/tag/")[1]);
  if (document.getElementById("quiz").checked) {
    classifi = "問題";
  } else if (document.getElementById("others").checked) {
    classifi = "其他";
  } else {
    classifi = "閒聊";
  }
  console.log(title,content,time,tag_name,classifi)
  const options = {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({
      title: title,
      content: content,
      time: time,
      classifi:classifi,
      tag_name: tag_name
    }),
  };
  const response = await fetch("/api/tag_page", options);
  const result = await response.json();
  if(result.ok){
    console.log(result.ok)
    window.location.reload();
    return
  }
  console.log(result.error)
  
}

//總蓋房器
building_posts = async(bricks) => {
  console.log(bricks)
  let Acheron = document.getElementById("Acheron");
  for(brick of bricks){
    let brick_id = brick.brick_id;
    let title = brick.title
    let time = brick.time
    let classifi = brick.classifi
    let author = brick.account
    let popu = brick.popularity
    let feedbacks = brick.feedbacks
    time = moment(time).subtract(8, "hours").format("MMMM Do YYYY, h:mm:ss a");
    let a_tag_discussion = document.createElement("div")
    a_tag_discussion.setAttribute("class", "a_tag_discussion");
    a_tag_discussion.setAttribute("id", "tag_discuss_id"+brick_id);

    //類別
    let typer = document.createElement("p")
    typer.appendChild(document.createTextNode(classifi))
    typer.setAttribute("class","nav_type")

    //標題
    let titler = document.createElement("p")
    titler.appendChild(document.createTextNode(title))
    titler.setAttribute("class","nav_title")
    titler.setAttribute("id","nav_title"+brick_id)
    titler.setAttribute("onclick","into_the_woods(this.id)")
    
    //作者
    let worker = document.createElement("p")
    worker.appendChild(document.createTextNode(author))
    worker.setAttribute("class","nav_author")

    //人氣與回覆
    let populer = document.createElement("p")
    populer.appendChild(document.createTextNode(popu+"/"+feedbacks))
    populer.setAttribute("class","nav_popu")
    
    //日期
    let timer = document.createElement("p")
    timer.appendChild(document.createTextNode(time))
    timer.setAttribute("class","nav_time")

    a_tag_discussion.appendChild(typer)
    a_tag_discussion.appendChild(titler)
    a_tag_discussion.appendChild(worker)
    a_tag_discussion.appendChild(populer)
    a_tag_discussion.appendChild(timer)

    Acheron.appendChild(a_tag_discussion)
  }
}

into_the_woods = async(brick_nav_title_id) => {
  brick_id = brick_nav_title_id.split("nav_title")[1];
    const options = {
      method: "PATCH",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        brick_id: brick_id,
      }),
    };
    const response = await fetch("/api/tag_page", options);
    const result = await response.json();
    if(result.ok){
      console.log(result)
      window.location = "/tag/" + key_word + "/" + brick_id;
      return
    }
    console.log(result.error)  
}