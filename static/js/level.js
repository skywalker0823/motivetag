//定義升級細節
//新增Tag一個可以加5。但一天最高三個 = 15exp
//一篇文章 讚與爛各會算1exp
//文章下留言3exp
//一篇文章10exp 相對的 刪文章-10exp
//留言按讚1exp
//每日登入25exp

//獎勵之後再做，預計是增加使用者權限與功能
//Anonymous預計開放給5等的人
//10等的人可創建PrimeTag(但要符合相關規範)
//15等可以發起vote
//功能開啟做在前端JS中


exp_mod = async(action,who) =>{
    //1.定義動作
    //2.定義自身獲得/減少exp
    //3.定義對方獲得/減少exp
    //4.未來額外依照天賦技能做增減調整
    let self_exp_modify
    // let who=null
    if (action == "block_creater") {
      self_exp_modify = 50;
    } else if (action == "block_destroy") {
      self_exp_modify = -150;
    }  else if (action == "good_bad" || action == "good_message") {
      self_exp_modify = 5;//if praised 25
    } else if (action == "message") {
      self_exp_modify = 3;//if praised 9
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

// locker = () => {
//   window.scrollTo(0, 0);
// };

// loger_on = () => {
//   loger.style.display = "block";
//   mask.style.display = "block";
//   window.addEventListener("scroll", locker);
// };

// loger_off = () => {
//   loger.style.display = "none";
//   mask.style.display = "none";
//   signer.style.display = "none";
//   window.removeEventListener("scroll", locker);
// };

