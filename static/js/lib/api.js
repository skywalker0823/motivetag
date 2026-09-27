// One place for talking to the Flask API: JSON in and out, errors in plain Chinese.
// Many endpoints answer 200 with {"error": ...}; callers check `data.error` for those
// and use `errorMessage()` to show them. Network and HTTP failures throw ApiError.

export class ApiError extends Error {
  constructor(message, status, data) {
    super(message);
    this.status = status;
    this.data = data;
  }
}

const MESSAGES = {
  "not loged in": "登入已過期，請重新登入",
  "wrong account or password": "帳號或密碼錯誤",
  "Already registed": "這個帳號已經有人使用",
  "Same email used": "這個 Email 已經註冊過",
  "Already friend": "你們已經是好友了",
  "same invite found": "已經送出過邀請",
  "already invite": "已經送出過邀請",
  "You cannot invite yourself!": "不能加自己為好友",
  "no such user": "找不到這個帳號",
  "already have this tag": "你已經訂閱這個標籤",
  "You have voted before!": "你已經投過票了",
  "no such option on this post": "這個投票選項無效",
  "you pressed this good before": "你已經按過讚了",
  "you pressed this boo before": "你已經按過爛了",
  "you pressed this good message before": "你已經按過讚了",
  "file type not allowed": "只能上傳 PNG、JPEG 或 GIF 圖片",
  "block not found or not yours": "找不到這篇貼文，或它不是你的",
};

export function errorMessage(error, fallback = "發生錯誤，請稍後再試") {
  if (!error) return fallback;
  if (error instanceof ApiError) return error.message;
  // v1 errors are {code, message}; older endpoints use {error} or {msg}.
  if (typeof error === "object") return errorMessage(error.message ?? error.error ?? error.msg, fallback);
  return MESSAGES[error] ?? (typeof error === "string" && /[一-鿿]/.test(error) ? error : fallback);
}

export async function api(path, { method = "GET", body, query } = {}) {
  const url = query ? `${path}?${new URLSearchParams(query)}` : path;
  let response;
  try {
    response = await fetch(url, {
      method,
      credentials: "same-origin",
      headers: body === undefined ? {} : { "content-type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    throw new ApiError("網路連線失敗，請檢查網路後再試", 0);
  }
  let data = null;
  try {
    data = await response.json();
  } catch {
    // Not JSON (for example an nginx error page); handled below.
  }
  if (response.status === 429) throw new ApiError("嘗試次數太多，請稍候一分鐘再試", 429, data);
  if (response.status >= 500 || data === null) {
    throw new ApiError("伺服器暫時無法回應，請稍後再試", response.status, data);
  }
  if (!response.ok && data.error) throw new ApiError(errorMessage(data.error), response.status, data);
  return data;
}
