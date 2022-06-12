
let brick_id 
document.addEventListener("DOMContentLoaded", async () => {
    key_word = window.location.pathname.split("/tag/")[1];
    key_word = decodeURI(key_word);
    brick_id = key_word.split("/")[1];
    data = await init_brick(brick_id);
    
    let tag_title = document.getElementById("the_word");
    let key_box = document.createElement("div");
    key_box.setAttribute("class", "key_box");
    key_box.appendChild(
      document.createTextNode(
        "#" + key_word.split("/")[0] +"/"+ data[0].title
      )
    );
    tag_title.appendChild(key_box);
    brick_discuss_fetcher()
});

init_brick = async(brick_id) =>{
  const response = await fetch("/api/bricks?brick_id=" + brick_id);
  const result = await response.json();
  if (result.ok) {
    main_brick_builder(result.data);
    return result.data;
  }
}

main_brick_builder = (data) => {
    data = data[0]
    let account = data.account
    let classifi = data.classifi
    let content = data.content
    let time = data.time
    let title = data.title

    document.getElementById("by_who").innerHTML = account
    document.getElementById("content").innerHTML = content

}

brick_discuss_fetcher = async() => {
  const response = await fetch("/api/get_brick_discuss?brick_id="+brick_id);
  const result = await response.json();

  if(result.ok){
    brick_discuss_builder(result.data)
    return
  }
  console.log(result.error)
}

discuss_sender = async() => {
  let content = document.getElementById("feedback_input").value;
  let time = moment().format("YYYY-MM-DD HH:mm:ss");

  if(!content){
    console.log("null input")
    return
  }

  const options = {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({
      brick_id: brick_id,
      content: content,
      time: time,
    }),
  };
  const response = await fetch("/api/bricks", options);
  const result = await response.json();
  if(result.ok){
    window.location.reload();
    return
  }
  console.log(result.error)
}

brick_discuss_builder = (datas) => {
  console.log(datas)
  let brick_discuss = document.getElementById("brick_discuss")

  for(a_discuss of datas){
    let a_discuss_box = document.createElement("div")
    a_discuss_box.setAttribute("class", "a_discuss_box");

    let account = a_discuss.account
    let content = a_discuss.content
    let time = a_discuss.time

    //account
    let account_box = document.createElement("div")
    account_box.setAttribute("class","account_box")
    account_box.appendChild(document.createTextNode(account))

    //content
    let content_box = document.createElement("div")
    content_box.setAttribute("class","content_box")
    content_box.appendChild(document.createTextNode(content))

    //time
    let time_box = document.createElement("div")
    time_box.setAttribute("class","time_box")
    time_box.appendChild(document.createTextNode(time))

    a_discuss_box.appendChild(account_box)
    a_discuss_box.appendChild(content_box)
    a_discuss_box.appendChild(time_box)

    brick_discuss.appendChild(a_discuss_box)
  }
}