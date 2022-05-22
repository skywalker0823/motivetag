//負責處理通知 ㄘ我通知拉
notifi_open = false
let notifies

//以自己為觀點出發 就是以大家的觀點出發
//1.好友
//當對一個人發送邀請 也發送通知
//對好友邀請(打勾/拒絕）的動作發送通知
//通知器標準格式{me:member_id,someone_else:account,type:類型,content:"內容"}
send_notifi = async(data) => {
    console.log(data)
    let me = data["me"]//its member_id
    let whom = data["someone_else"]//its account
    let type = data["type"]
    let content = data["content"]
    let time = data["time"]
    const options = {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ me: me ,who:whom,type:type,content:content,time:time}),
    };
    const response = await fetch("/api/notifi", options);
    const result = await response.json();
    if(result.ok){
        console.log(result.ok)
        return
    }
    console.log(result.error)

}
//2.文章部分
//新文章將對自身好友發通知

//3.留言
//在他人文章下留言 對發文章發送通知

//4.聊天

get_my_notification_every_15s = async() =>{
    const response = await fetch("/api/notifi");
    const result = await response.json();
    if(result.ok){
        console.log(result);
    }

}

//通知定時抓取器
const interval = setInterval(async function () {
    let unread_notifis = document.getElementById("unread_notifis");
    let notifi_bell = document.getElementById("notifi_bell");
    const response = await fetch("/api/notifi");
    const result = await response.json();
    if(result.ok){
        // console.log(result,"你老兄有",result.count,"未讀訊息");
        unread_notifis.innerHTML=""
        if(result.count==0){
            unread_notifis.innerHTML = "";
            notifi_bell.setAttribute("animation","none")

        }else{
            unread_notifis.innerHTML = result.count;
            notifi_bell.setAttribute("animation", "tada");
            notifies = result
        }
    }
}, 12000);


//通知被打開並打PATCH清除過去通知(其實好像可以刪除舊通知)
document.getElementById("notifi_bell").addEventListener("click",async () => {
    //這裡將會打開清單 
    let notifi_list = document.getElementById("notifi_list");
    if(notifi_open){
        notifi_list.innerHTML=""
        notifi_list.style.height="0px"
        notifi_list.style.border = "solid 0px #1cbfff";
        notifi_open=false
    }else{
        console.log("OPEN!");
        notifi_list.style.height = "500px"
        notifi_list.style.border = "solid 1px #1cbfff";
        notifi_open = true
        //將訊息放置在清單上 並發出DELETE
        if(!notifies){
            console.log("查無通知")
            let one_notify = document.createElement("div");
            one_notify.setAttribute("class", "one_notify");
            let content = document.createTextNode("沒有最新通知");
            one_notify.appendChild(content);
            notifi_list.appendChild(one_notify);
            return
        }
        console.log(notifies.data)
        for(a_notifi of notifies.data){
            console.log(a_notifi)
            let one_notify = document.createElement("div");
            one_notify.setAttribute("class", "one_notify");
            let content = document.createTextNode(a_notifi.content)
            let time_box = document.createElement("div")
            time_box.setAttribute("class","notify_time")
            let time = document.createTextNode(
              moment(a_notifi.read_time).subtract(8, "hours").fromNow()
            );
            time_box.appendChild(time)
            let notifi_box = document.createElement("div")
            notifi_box.setAttribute("class","notifi_box")
            one_notify.appendChild(content)
            one_notify.appendChild(time_box)
            notifi_box.appendChild(one_notify)
            notifi_list.appendChild(notifi_box);
        }
        const options = {
            method: "DELETE",
            headers: { "content-type": "application/json" },
            body: JSON.stringify({
            me: me,
            content: "content here will be use in near future",
            }),
        };
        const response = await fetch("/api/notifi", options);
        const result = await response.json();
        if(result.ok){
            console.log("notifi read and deleted")
        }
        
    }
});