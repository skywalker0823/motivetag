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

