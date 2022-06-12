notifi_open = false
let notifies
send_notifi = async(data) => {
    console.log(data)
    let me = data["me"]
    let whom = data["someone_else"]
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


document.getElementById("notifi_bell").addEventListener("click",async () => {
    let notifi_list = document.getElementById("notifi_list");
    if(notifi_open){
        notifi_list.innerHTML=""
        notifi_list.style.height="0px"
        notifi_list.style.border = "solid 0px #1cbfff";
        notifi_open=false
    }else{
        notifi_list.style.height = "500px"
        notifi_list.style.border = "solid 1px #1cbfff";
        notifi_open = true
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
              moment(a_notifi.read_time).fromNow()
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