exp_mod = async(action,who) =>{
    let self_exp_modify
    if (action == "block_creater") {
      self_exp_modify = 50;
    } else if (action == "block_destroy") {
      self_exp_modify = -150;
    }  else if (action == "good_bad" || action == "good_message") {
      self_exp_modify = 5;
    } else if (action == "message") {
      self_exp_modify = 3;
    }  else {
      return "error";
    }
  
    const options = {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({exp: self_exp_modify}),
    };
    const response = await fetch("/api/level", options);
    const result = await response.json();

    if(result.ok){

        return
    }
    console.log(result.error)
}

open_talent = () =>{
    console.log("open_talent")
    mask = document.getElementById("mask")
    talent_sq = document.getElementById("talent_sq")
    mask.style.display = "block";
    talent_sq.style.display="flex"

}
close_talent = () =>{
    mask = document.getElementById("mask");
    talent_sq = document.getElementById("talent_sq");
    mask.style.display = "none";
    talent_sq.style.display = "none";
}

render_level = (exp) =>{
    if(exp==0 || exp<0){
        return
    }
    let level;
    let percent;
    level = ((((8*exp/50)+1)**0.5)+1)/2
    percent = (level-parseInt(level))*100+"%"
    document.getElementById("level_display").innerHTML = parseInt(level);
    document.getElementById("progress_display").style.width=percent;
}

