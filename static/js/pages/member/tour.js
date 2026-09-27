// The first-visit tour of the member page, and the help button that replays it.
import { $ } from "../../lib/dom.js";
import { fromServer } from "../../lib/time.js";
import { startTour } from "../../lib/tour.js";
import { me, showView } from "./state.js";

const NEW_FOR_DAYS = 7; // members who joined this recently get the tour once
const doneKey = () => `motivetag:tour-done:${me.account}`;

// On phones only one panel shows at a time, so each step opens the one it talks about.
const STEPS = [
  {
    title: "歡迎來到 MotiveTag",
    text: "這裡用 #標籤 把興趣相同的人串在一起。花 30 秒看看怎麼玩，之後隨時可以按右上角的「?」再看一次。",
    before: () => showView("feed"),
  },
  {
    target: "#tag-add",
    title: "1. 訂閱標籤",
    text: "輸入你有興趣的主題，例如「咖啡」或「登山」。訂閱後，帶有這個標籤的貼文都會出現在你的動態。",
    before: () => showView("tags"),
  },
  {
    target: "#trend",
    title: "不知道訂閱什麼？",
    text: "看看熱門標籤：點名稱可以先看看貼文，按「+」直接訂閱。",
    before: () => showView("tags"),
  },
  {
    target: "#composer",
    title: "2. 發文",
    text: "在內容裡加上 #標籤，訂閱那個標籤的人就看得到。可以選公開、私密（只有自己）或匿名，也能附圖或發起投票。",
    before: () => showView("feed"),
  },
  {
    target: "#feed-tabs",
    title: "我的動態與探索",
    text: "「我的動態」是好友、你訂閱的標籤和你自己的貼文；「探索」是所有人最新的公開貼文。發文、按讚、留言都能獲得經驗值升級。",
    before: () => showView("feed"),
  },
  {
    target: "#friend-invite",
    title: "3. 交朋友、聊天",
    text: "輸入對方的帳號送出邀請，或在貼文上點頭像。好友上線時頭像旁會亮綠點，點一下就能開聊天室。",
    before: () => showView("friends"),
  },
  {
    target: "#help-button",
    title: "準備好了！",
    text: "先訂閱幾個標籤，或發一篇自我介紹吧。想再看一次教學，按這個「?」就好。",
    before: () => showView("feed"),
  },
];

function remember() {
  try {
    localStorage.setItem(doneKey(), "1");
  } catch {
    // Private mode: the tour may show again next time, which is harmless.
  }
}

function seen() {
  try {
    return localStorage.getItem(doneKey()) === "1";
  } catch {
    return true; // cannot remember, so do not show it on every visit
  }
}

export function showTour() {
  startTour(STEPS, { onEnd: remember });
}

/** Wires the help button; starts the tour for members who joined in the past week. */
export function initTour(firstSignup) {
  $("#help-button").addEventListener("click", showTour);
  const joined = fromServer(firstSignup);
  const isNew = joined && Date.now() - joined.getTime() < NEW_FOR_DAYS * 86400000;
  if (isNew && !seen()) showTour();
}
