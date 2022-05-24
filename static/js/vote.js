let voter =  document.getElementById("voter");
let vote_up=false
let voter_counter=0
start_poll = () =>{
    console.log("Poll!")
    voter.style.display = "block";
    vote_up=true
}

document.getElementById("del_vote").addEventListener("click",()=>{
    document.getElementById("voter").style.display="none"
    vote_up=false
})

more_options = () =>{
    if(voter_counter>=5){
        console.log("Full!")
        
        return
    }
    voter_counter=0
    vote_holder = document.getElementById("vote_holder")
    let a_option = document.createElement("div")
    let option_input = document.createElement("input")
    a_option.setAttribute("class","a_option")
    option_input.setAttribute("class","option_input")
    option_input.setAttribute("type","text")
    option_input.setAttribute("placeholder","選項")
    a_option.appendChild(option_input)
    vote_holder.appendChild(a_option)
    total_check = document.getElementsByClassName("a_option")
    for(a of total_check){
        voter_counter+=1
        console.log(voter_counter)
    }
}

bye_guard = (id) => (document.getElementById(id).innerHTML = "");

vote_this = async (btnid) => {
  a = btnid.split("vote_btn")[1];
  what = a.split("block_id");
  id = what[0];
  block_id = what[1];
  const options = {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({
      vote_option_id: id,
      block_id: block_id,
    }),
  };
  const response = await fetch("/api/vote", options);
  const result = await response.json();
  if (result.ok) {
    console.log("投票成功");
  } else {
    console.log(result.error,result.data);

    
  }
};

see_vote_result = async (id) => {
    let the_block = id.split("vote_result")[1];
    document.getElementById("chart_holder"+the_block).innerHTML=""
    the_canvas = document.createElement("canvas")
    the_canvas.setAttribute("class","the_canvas")
    the_canvas.setAttribute("id","canvas"+the_block)
    document.getElementById("chart_holder"+the_block).appendChild(the_canvas)


  const response = await fetch("/api/vote?block_id="+the_block);
  const result = await response.json();
  if(result.ok){
      console.log(result.data)
    //   for (a_vote of result.data){
    //       document.getElementById("vote_result" + a_vote.vote_option_id).innerHTML=0;
    //   }
      total={}
    for (a_vote of result.data) {
        now = document.getElementById("vote_result" + a_vote.vote_option_id);
        // now.innerHTML = parseInt(now.innerHTML) + 1;
        choice = document.getElementById("vote_option_id" + a_vote.vote_option_id).innerHTML;
        console.log(choice)
        if(!total[choice]){
            total[choice]=1
        }else{
            total[choice] += 1;
        }

    }
    let xValues=[]
    let yValues=[]
    console.log(total)
    for(key in total){
        console.log(key,total[key])
        xValues.push(key)
        yValues.push(total[key])
    }
    // var xValues = ["Italy", "France", "Spain"];
    // var yValues = [55, 49, 0];
    // const tmpChart = Chart.getChart("canvas" + the_block);
    // if (tmpChart) {
    //   tmpChart.destroy();
    // }
    new Chart("canvas" + the_block, {
      type: "horizontalBar",
      data: {
        labels: xValues,
        datasets: [
          {
            backgroundColor: "rgba(219, 107, 129, 86)",
            data: yValues,
            borderColor: "rgba(86, 129, 108, 86)",
            borderWidth: 1,
          },
        ],
      },
      options: {
          scales: {
      yAxes: [{
         ticks: {
            stepSize: 1
         }
      }]
   },
        legend: { display: false },
        title: {
          display: false,
          text: "投票狀況",
        },
      },
    });
      return

  }
  console.log("get vote result error")
};