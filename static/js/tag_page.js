


document.addEventListener("DOMContentLoaded",async() => {
    let key_word = window.location.pathname.split("/tag/")[1]
    key_word = decodeURI(key_word)
    let tag_title = document.getElementById("the_word")
    let key_box = document.createElement("div")
    key_box.setAttribute("class","key_box")

    key_box.appendChild(document.createTextNode("#"+key_word))
    tag_title.appendChild(key_box)
    
    init_tag_page(key_word)

});



init_tag_page = async(key_word) =>{
  const response = await fetch("/api/tag_page?keyword=" + key_word);
  const result = await response.json();
  if(result.ok){
    console.log(result)
  }
}



