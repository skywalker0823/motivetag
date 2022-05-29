let preview_span = document.getElementById("preview_span");
let sign_account = document.getElementById("sign_account");
let loading = document.getElementById("loading")
let check_ok = document.getElementById("check_ok")
let x = document.getElementById("x")
let changing = false
let fetching = false
document.addEventListener("DOMContentLoaded", () => {
  check_user_identity(); 
  render_dates()
});

document.getElementById("login_submit").addEventListener("click", () => {
  signin();
});

document.getElementById("signup_submit").addEventListener("click", () => {
  signup()
})

document.getElementById("account").addEventListener("input",()=>{
  let account_x = document.getElementById("account_x");
  account_x.style.display="none"
})
document.getElementById("password").addEventListener("input", () => {
  let account_x = document.getElementById("pass_x");
  pass_x.style.display = "none";
});




sign_account.addEventListener("input", () => {
  // if(changing){return}
  if(fetching){return}
  changing = true
  check_ok.style.display="none"
  x.style.display = "none";
  loading.style.display="block";
  fetching = true
  account_checker()
})

let day=new Date()

//檢查狀態
check_user_identity = async() =>{
  const options = {method: "GET"};
  const response = await fetch("/api/member", options);
  const result = await response.json();
  if(result.ok){
      console.log("already login!")
      window.location.href=result.account
      //轉至個人頁
  }else{console.log(result.error)}
}


//登入
signin = async() => {
  let account = document.querySelector("#account").value;
  let password = document.querySelector("#password").value;
  let account_x = document.getElementById("account_x")
  let pass_x = document.getElementById("pass_x")
  let time = moment().format("YYYY-MM-DD HH:mm:ss");
  if(!account){
    account_x.style.display="block"
    return
  }
  if(!password){
    pass_x.style.display="block"
    return
  }
  const options = {
    method: "PUT",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({
      account:account,
      password:password,
      time:time
    }),
  };
  const response = await fetch("/api/member",options)
  const result = await response.json();
  if(result.ok){
      window.location.href = result.data.account;
  }else{
    let pass_x = document.getElementById("pass_x");
    let account_x = document.getElementById("account_x");
    pass_x.style.display = "block";
    account_x.style.display = "block";
  }
};

//註冊
signup = async () => {
  let account = document.querySelector("#sign_account").value;
  let password = document.querySelector("#sign_password").value;
  let email = document.querySelector("#sign_email").value;
  let b_year = document.querySelector("#b_year").value;
  let b_month = document.querySelector("#b_month").value;
  let b_day = document.querySelector("#b_day").value;
  let today =
  day.getFullYear() + "-" + (day.getMonth() + 1) + "-" + day.getDate();
  let birth = b_year + "-" + b_month + "-" + b_day
  if (!account || !password || !email || !b_year || !b_month || !b_day) {
    console.log("null input");
    return;
  }
  const options = {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ account: account, password: password ,email:email,birthday:birth,first_signup:today}),
  };
  const response = await fetch("/api/member", options);
  const result = await response.json();
  if (result.ok) {
    console.log("註冊成功!")
    document.getElementById("signup_check").style.opacity="1"
    //增加畫面提示
  } else {
    console.log(result.error);
  }
};

//輸入帳號檢查
account_checker = () => {
  if(!sign_account.value){
      loading.style.display = "none";
      check_ok.style.display = "none";
      x.style.display = "block";
    return}
  //輸入停止一段時間後 執行一次帳號檢查
  const interval = setInterval(async()=>{
    if(!changing){return}
    const response = await fetch("/api/member?account_check="+sign_account.value);
    const result = await response.json();
    if(result.ok==null && !result.error){
      console.log("this account OK!")
      changing = false
      loading.style.display = "none";
      check_ok.style.display = "block";
      x.style.display = "none"
      fetching= false
      preview_span.innerHTML = sign_account.value;

    }else{
      changing = false
      loading.style.display = "none";
      check_ok.style.display = "none";
      x.style.display="block"
      fetching = false;
      preview_span.innerHTML = sign_account.value;
    }
  },5000);

  
}


render_dates = () => {
  let year_list = document.getElementById("b_year")
  let month_list = document.getElementById("b_month")
  let day_list = document.getElementById("b_day")
  //year
  let start_year = 1943
  let end_year = new Date().getFullYear();
  for(let year = start_year;year<=end_year;year++){
    let option = document.createElement("option")
    option.appendChild(document.createTextNode(year))
    year_list.appendChild(option)
  }

  let start_month = 1
  let end_month = 12
  for (let month = start_month; month <= end_month; month++) {
    let option = document.createElement("option");
    option.appendChild(document.createTextNode(month));
    month_list.appendChild(option);
  }

  let start_day = 1
  let end_day = 31
  for (let day = start_day; day <= end_day; day++) {
    let option = document.createElement("option");
    option.appendChild(document.createTextNode(day));
    day_list.appendChild(option);
  }
};



// GOOGLE AUTH

handleCredentialResponse = (response) => {
  const responsePayload = decodeJwtResponse(response.credential);
  google_login(responsePayload)
}

function decodeJwtResponse(token) {
  var base64Url = token.split(".")[1];
  var base64 = base64Url.replace(/-/g, "+").replace(/_/g, "/");
  var jsonPayload = decodeURIComponent(
    atob(base64)
      .split("")
      .map(function (c) {
        return "%" + ("00" + c.charCodeAt(0).toString(16)).slice(-2);
      })
      .join("")
  );

  return JSON.parse(jsonPayload);
};

google_login = async(user_data)=>{
    const options = {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ user_data:user_data }),
    };
    const response = await fetch("/api/google_sign_in", options);
    const result = await response.json();
    if(result.ok=="let_in"){
      window.location.href = result.account;
      return
    }
    if(result.ok=="again"){
      google_login(user_data);
      return
    }
    console.log(result.error)
}