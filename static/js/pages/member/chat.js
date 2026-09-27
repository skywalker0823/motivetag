// One-to-one chat windows over Socket.IO (see api/blueprints/api_chat.py).
import { $, h } from "../../lib/dom.js";
import { icon } from "../../lib/icons.js";
import { socket } from "../../lib/socket.js";
import { toast } from "../../lib/toast.js";
import { notify } from "./notifications.js";
import { me } from "./state.js";

const container = $("#chats");
const windows = new Map(); // account -> { el, messages, input, room }
const pending = []; // accounts waiting for their init_result, in request order

function bubble(win, text, kind) {
  win.messages.append(h("p", { class: `bubble${kind ? ` bubble--${kind}` : ""}` }, text));
  win.messages.scrollTop = win.messages.scrollHeight;
}

function close(account) {
  const win = windows.get(account);
  if (!win) return;
  if (win.room) socket.emit("left", { room: win.room, account });
  win.el.remove();
  windows.delete(account);
}

export function openChat(account) {
  const existing = windows.get(account);
  if (existing) {
    existing.el.dataset.minimized = "false";
    container.append(existing.el); // bring to front (and visible on phones)
    existing.input.focus();
    return;
  }

  const messages = h("div", { class: "chat__messages", role: "log", "aria-label": `和 ${account} 的對話` });
  const input = h("input", { class: "input", placeholder: "輸入訊息…", "aria-label": "訊息", maxlength: "1000", autocomplete: "off" });
  const form = h(
    "form",
    { class: "chat__form" },
    input,
    h("button", { class: "icon-btn", type: "submit", "aria-label": "送出" }, icon("send")),
  );
  const el = h(
    "section",
    { class: "chat", "aria-label": `和 ${account} 聊天`, dataset: { minimized: "false" } },
    h(
      "header",
      { class: "chat__header" },
      h("span", null, account),
      h(
        "button",
        {
          class: "icon-btn icon-btn--sm",
          type: "button",
          "aria-label": "縮小",
          onClick: () => (el.dataset.minimized = String(el.dataset.minimized !== "true")),
        },
        icon("minus", { size: "sm" }),
      ),
      h("button", { class: "icon-btn icon-btn--sm", type: "button", "aria-label": "關閉聊天", onClick: () => close(account) }, icon("x", { size: "sm" })),
    ),
    messages,
    form,
  );

  const win = { el, messages, input, room: null };
  windows.set(account, win);
  container.append(el);
  bubble(win, "連線中…", "system");

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    const content = input.value.trim();
    if (!content) return;
    if (!win.room) return toast("聊天室還沒連上，請稍候");
    socket.emit("send", { type: "message", to: account, content, room: win.room });
    input.value = "";
  });

  pending.push(account);
  socket.emit("init_room", { account });
  input.focus();
}

export function initChat() {
  socket.on("init_result", (result) => {
    const account = pending.shift();
    const win = windows.get(account);
    if (!win) return;
    if (result.ok) {
      win.room = result.room;
      bubble(win, result.ok === "JOINED" ? "已加入聊天" : `等待 ${account} 加入…`, "system");
    } else {
      bubble(win, `${account} 目前不在線上，已通知他`, "system");
      notify(account, `${me.account} 想找你聊天，但你不在線上`);
    }
  });

  socket.on("message", (data) => {
    const partner = data.to === me.account ? data.from : data.to;
    const win = windows.get(partner);
    if (!win) return;
    if (data.content === `${data.from} JOINED!`) {
      if (data.from !== me.account) bubble(win, `${data.from} 加入了聊天`, "system");
      return;
    }
    if (data.content === `${data.from} 離開了QQ!`) {
      bubble(win, `${data.from} 離開了聊天`, "system");
      return;
    }
    bubble(win, data.content, data.from === me.account ? "mine" : null);
  });

  window.addEventListener("pagehide", () => socket.emit("logout", { account: me.account }));
}
