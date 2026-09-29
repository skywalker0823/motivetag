// One-to-one chat, Messenger style (api/v1/chats.py): messages are stored and pushed to
// every open tab, so nobody has to "join" a room and nothing is lost while someone is
// offline. The topbar button lists conversations; each one opens a docked window.
import { api, errorMessage } from "../../lib/api.js";
import { $, h, img } from "../../lib/dom.js";
import { icon } from "../../lib/icons.js";
import { frameClass, levelBadge } from "../../lib/levels.js";
import { reportDialog } from "../../lib/report.js";
import { socket } from "../../lib/socket.js";
import { fromServer, fullDateTime, timeAgo } from "../../lib/time.js";
import { toast, toastError } from "../../lib/toast.js";
import { avatarUrl, DEFAULT_AVATAR, emit, me, on } from "./state.js";

const TYPING_SEND_MS = 3000; // at most one "typing" signal every 3 s
const TYPING_SHOW_MS = 5000; // the indicator goes away when the signals stop
const POLL_MS = 60000; // pushes do the work; this only catches what a reconnect missed
const MAX_WINDOWS = 3;
const phone = matchMedia("(max-width: 899px)");

const container = $("#chats");
const button = $("#chats-button");
const panel = $("#chats-panel");
const list = $("#chats-list");
const activeRow = $("#chats-active");
const count = $("#chats-count");

const conversations = new Map(); // account -> { partner, last, unread, online }
const windows = new Map(); // account -> window state, see createWindow()
const presence = new Map(); // account -> online?, kept current by awake_result pushes
let friends = []; // [{ account, id, online }] from friends.js
let baseTitle = document.title;

const chatUrl = (account, path) => `/api/v1/chats/${encodeURIComponent(account)}/${path}`;
const isOnline = (account) => presence.get(account) ?? conversations.get(account)?.online ?? false;

const hhmm = (date) => date?.toLocaleTimeString("zh-TW", { hour: "2-digit", minute: "2-digit", hour12: false }) ?? "";

function dayLabel(date) {
  const today = new Date();
  const yesterday = new Date(today.getTime() - 86400000);
  if (date.toDateString() === today.toDateString()) return "今天";
  if (date.toDateString() === yesterday.toDateString()) return "昨天";
  return date.toLocaleDateString("zh-TW", { month: "long", day: "numeric", weekday: "short" });
}

/* ---------- Conversation list and badges ---------- */

function totalUnread() {
  let total = 0;
  for (const c of conversations.values()) total += c.unread;
  return total;
}

function refreshBadges() {
  const total = totalUnread();
  count.hidden = total === 0;
  count.textContent = total > 99 ? "99+" : String(total);
  button.setAttribute("aria-label", total ? `聊天（${total} 則未讀）` : "聊天");
  document.title = (total ? `(${total}) ` : "") + baseTitle;
  emit("chat:unread", Object.fromEntries([...conversations].map(([account, c]) => [account, c.unread])));
  for (const win of windows.values()) {
    const unread = conversations.get(win.account)?.unread ?? 0;
    win.badge.hidden = unread === 0 || win.el.dataset.minimized !== "true";
    win.badge.textContent = String(unread);
  }
  if (!panel.hidden) renderList();
}

function avatarFor(memberId) {
  return img(memberId ? avatarUrl(memberId) : DEFAULT_AVATAR, DEFAULT_AVATAR, { class: "avatar avatar--sm" });
}

function conversationItem(c) {
  const account = c.partner.account;
  const mine = c.last.from === me.account;
  return h(
    "li",
    null,
    h(
      "button",
      {
        class: "chat-item",
        type: "button",
        dataset: { unread: String(c.unread > 0) },
        onClick: () => {
          setPanel(false);
          openChat(account);
        },
      },
      h("span", { class: "chat-item__avatar", dataset: { online: String(isOnline(account)) } }, avatarFor(c.partner.member_id)),
      h(
        "span",
        { class: "chat-item__body" },
        h("span", { class: "chat-item__name" }, account),
        h("span", { class: "chat-item__preview" }, (mine ? "你：" : "") + c.last.content),
      ),
      h(
        "span",
        { class: "chat-item__meta" },
        timeAgo(c.last.sent_at),
        c.unread ? h("span", { class: "chat-item__badge", "aria-label": `${c.unread} 則未讀` }, c.unread > 99 ? "99+" : String(c.unread)) : null,
      ),
    ),
  );
}

function renderList() {
  const online = friends.filter((f) => isOnline(f.account));
  activeRow.hidden = online.length === 0;
  activeRow.replaceChildren(
    ...online.map((f) =>
      h(
        "button",
        {
          class: "chat-active",
          type: "button",
          title: `和 ${f.account} 聊天`,
          onClick: () => {
            setPanel(false);
            openChat(f.account);
          },
        },
        h("span", { class: "chat-item__avatar", dataset: { online: "true" } }, avatarFor(f.id)),
        h("span", { class: "chat-active__name" }, f.account),
      ),
    ),
  );
  const items = [...conversations.values()].sort((a, b) => b.last.id - a.last.id);
  list.replaceChildren(
    ...(items.length
      ? items.map(conversationItem)
      : [h("li", { class: "empty" }, "還沒有對話。在好友清單按聊天圖示，就能傳訊息給朋友")]),
  );
}

async function loadConversations() {
  let result;
  try {
    result = await api("/api/v1/chats");
  } catch {
    return;
  }
  conversations.clear();
  for (const c of result.data ?? []) {
    conversations.set(c.partner.account, c);
    presence.set(c.partner.account, c.online);
  }
  for (const win of windows.values()) markRead(win);
  refreshBadges();
}

function setPanel(open) {
  panel.hidden = !open;
  button.setAttribute("aria-expanded", String(open));
  if (open) {
    renderList();
    loadConversations();
  }
}

/* ---------- Chat windows ---------- */

function windowVisible(win) {
  if (document.visibilityState !== "visible" || win.el.dataset.minimized === "true") return false;
  // On phones only the frontmost window shows.
  return !phone.matches || container.lastElementChild === win.el;
}

function nearBottom(win) {
  return win.log.scrollHeight - win.log.scrollTop - win.log.clientHeight < 80;
}

function scrollToBottom(win) {
  win.log.scrollTop = win.log.scrollHeight;
}

function bubble(win, message) {
  const mine = message.from === me.account;
  const sent = fromServer(message.sent_at);
  const el = h(
    "div",
    { class: `bubble${mine ? " bubble--mine" : ""}`, title: fullDateTime(sent), dataset: { id: String(message.id) } },
    h("span", { class: "bubble__text" }, message.content),
    h("time", { class: "bubble__time", dateTime: sent?.toISOString() ?? "" }, hhmm(sent)),
  );
  // Tapping their message offers to report it.
  if (!mine) el.addEventListener("click", () => offerReport(win, message, el));
  return el;
}

function offerReport(win, message, el) {
  const open = el.nextElementSibling?.classList.contains("chat__report");
  for (const old of win.body.querySelectorAll(".chat__report")) old.remove();
  if (open) return;
  el.after(
    h(
      "button",
      {
        class: "btn btn--ghost btn--sm chat__report",
        type: "button",
        onClick: async (event) => {
          event.currentTarget.remove();
          const result = await reportDialog({ type: "message", id: message.id, account: win.account });
          if (!result) return;
          el.remove();
          if (result.blocked) emit("member:blocked", { id: win.memberId, account: win.account });
        },
      },
      icon("flag", { size: "sm" }),
      "檢舉這則訊息",
    ),
  );
}

function separator(date) {
  return h("p", { class: "chat__day" }, dayLabel(date));
}

function updateReceipt(win) {
  const last = win.messages.at(-1);
  if (!last || last.from !== me.account || win.pending.size) {
    win.receipt.hidden = true;
    return;
  }
  win.receipt.hidden = false;
  win.receipt.textContent = last.read_at ? "已讀" : isOnline(win.account) ? "已送達" : "已送出，對方上線後會看到";
}

function updateHeader(win) {
  const online = isOnline(win.account);
  win.status.textContent = online ? "上線中" : "離線";
  win.avatarWrap.dataset.online = String(online);
  if (win.memberId && !win.avatarSet) {
    const avatar = avatarFor(win.memberId);
    avatar.className += frameClass(win.level);
    win.avatarWrap.replaceChildren(avatar);
    win.levelSlot.replaceChildren(levelBadge(win.level) ?? "");
    win.avatarSet = true;
  }
  updateReceipt(win);
}

function renderAll(win) {
  const nodes = [];
  let day = null;
  for (const message of win.messages) {
    const date = fromServer(message.sent_at);
    const key = date?.toDateString();
    if (date && key !== day) {
      nodes.push(separator(date));
      day = key;
    }
    nodes.push(bubble(win, message));
  }
  win.lastDay = day;
  win.ids = new Set(win.messages.map((m) => m.id));
  win.body.replaceChildren(...nodes, ...win.pending.keys());
  win.older.hidden = !win.more;
  win.empty.hidden = win.messages.length > 0 || win.pending.size > 0;
  updateReceipt(win);
}

/** Adds a message that arrived (pushed, or the answer to my send). */
function addMessage(win, message) {
  if (!win.loaded) {
    win.queue.push(message);
    return;
  }
  if (win.ids.has(message.id)) return;
  const stick = nearBottom(win) || message.from === me.account;
  if (win.messages.length && message.id < win.messages.at(-1).id) {
    win.messages.push(message);
    win.messages.sort((a, b) => a.id - b.id);
    renderAll(win);
  } else {
    win.messages.push(message);
    win.ids.add(message.id);
    const date = fromServer(message.sent_at);
    const first = win.body.querySelector(".bubble--pending, .bubble--failed");
    const nodes = [];
    if (date && date.toDateString() !== win.lastDay) {
      nodes.push(separator(date));
      win.lastDay = date.toDateString();
    }
    nodes.push(bubble(win, message));
    // Messages still being sent stay last.
    if (first) first.before(...nodes);
    else win.body.append(...nodes);
    win.empty.hidden = true;
    updateReceipt(win);
  }
  if (stick) scrollToBottom(win);
}

function note(win, text, retry) {
  win.body.append(
    h("p", { class: "chat__note" }, text, retry && h("button", { class: "btn btn--ghost btn--sm", type: "button", onClick: retry }, "重試")),
  );
}

async function loadHistory(win) {
  let result;
  try {
    result = await api(chatUrl(win.account, "messages"));
  } catch (error) {
    note(win, errorMessage(error, "訊息載入失敗"), () => {
      win.body.replaceChildren();
      loadHistory(win);
    });
    return;
  }
  // Keep older pages already shown; the newest page replaces what it covers.
  const byId = new Map(win.messages.map((m) => [m.id, m]));
  for (const message of result.data) byId.set(message.id, message);
  for (const message of win.queue.splice(0)) if (!byId.has(message.id)) byId.set(message.id, message);
  win.messages = [...byId.values()].sort((a, b) => a.id - b.id);
  if (!win.loaded) win.more = result.more;
  win.loaded = true;
  win.memberId = result.partner.member_id;
  win.level = result.partner.level;
  presence.set(win.account, result.online);
  setCanSend(win, result.can_send, result.blocked);
  renderAll(win);
  updateHeader(win);
  scrollToBottom(win);
  markRead(win);
}

async function loadOlder(win) {
  if (win.loadingOlder || !win.more || !win.messages.length) return;
  win.loadingOlder = true;
  try {
    const result = await api(chatUrl(win.account, "messages"), { query: { before: win.messages[0].id } });
    const height = win.log.scrollHeight;
    win.messages = [...result.data, ...win.messages];
    win.more = result.more;
    renderAll(win);
    win.log.scrollTop += win.log.scrollHeight - height; // stay where the reader was
  } catch (error) {
    toastError(error, "更早的訊息載入失敗");
  } finally {
    win.loadingOlder = false;
  }
}

function setCanSend(win, canSend, blocked = false) {
  win.form.hidden = !canSend;
  win.blocked.hidden = canSend;
  win.blocked.textContent = blocked ? "你已封鎖對方，解除封鎖後才能傳訊息" : "你們目前不是好友，無法傳訊息";
}

/** Tells the server I have seen their messages, when this window is really in view. */
function markRead(win) {
  if (!win.loaded || !windowVisible(win)) return;
  const conversation = conversations.get(win.account);
  const unseen = win.messages.filter((m) => m.from === win.account && !m.read_at);
  if (conversation?.unread) {
    conversation.unread = 0;
    refreshBadges();
  }
  if (!unseen.length) return;
  for (const message of unseen) message.read_at = "seen";
  api(chatUrl(win.account, "read"), { method: "POST", body: { up_to: unseen.at(-1).id } }).catch(() => {});
}

async function send(win, content, retrying) {
  const temp =
    retrying ??
    h("div", { class: "bubble bubble--mine bubble--pending" }, h("span", { class: "bubble__text" }, content), h("span", { class: "bubble__time" }, "傳送中"));
  temp.className = "bubble bubble--mine bubble--pending";
  temp.lastChild.textContent = "傳送中";
  temp.onclick = null;
  win.pending.set(temp, content);
  if (!retrying) win.body.append(temp);
  win.empty.hidden = true;
  updateReceipt(win);
  scrollToBottom(win);
  try {
    const result = await api(chatUrl(win.account, "messages"), { method: "POST", body: { content } });
    win.pending.delete(temp);
    temp.remove();
    addMessage(win, result.data);
    notePartnerMessage(result.data);
  } catch (error) {
    temp.className = "bubble bubble--mine bubble--failed";
    temp.lastChild.textContent = "傳送失敗，點一下重試";
    temp.title = errorMessage(error);
    temp.onclick = () => send(win, content, temp);
    const code = error.data?.error?.code;
    if (code === "not_friends" || code === "blocked") setCanSend(win, false);
    toastError(error, "訊息傳送失敗");
  }
  updateReceipt(win);
}

function createWindow(account) {
  const body = h("div", { class: "chat__body" });
  const older = h("button", { class: "btn btn--ghost btn--sm chat__older", type: "button", hidden: true }, "載入更早的訊息");
  const empty = h("p", { class: "chat__note", hidden: true }, `還沒有訊息，跟 ${account} 打聲招呼吧 👋`);
  const receipt = h("p", { class: "chat__receipt", hidden: true, "aria-live": "polite" });
  const typing = h("p", { class: "chat__typing", hidden: true, "aria-live": "polite" }, h("span", { class: "chat__dots", "aria-hidden": "true" }, h("i"), h("i"), h("i")), `${account} 正在輸入…`);
  const log = h("div", { class: "chat__messages", role: "log", "aria-label": `和 ${account} 的對話` }, older, empty, body, receipt, typing);
  const input = h("textarea", {
    class: "input chat__input",
    rows: "1",
    placeholder: "輸入訊息…",
    "aria-label": "訊息",
    maxlength: "1000",
    enterkeyhint: "send",
  });
  const form = h("form", { class: "chat__form" }, input, h("button", { class: "icon-btn", type: "submit", "aria-label": "送出" }, icon("send")));
  const blocked = h("p", { class: "chat__blocked", hidden: true }, "你們目前不是好友，無法傳訊息");
  const avatarWrap = h("span", { class: "chat-item__avatar", dataset: { online: "false" } }, avatarFor(null));
  const status = h("span", { class: "chat__status" });
  const levelSlot = h("span");
  const badge = h("span", { class: "chat__badge", hidden: true });
  const minimize = h("button", { class: "icon-btn icon-btn--sm", type: "button", "aria-label": "縮小" }, icon("minus", { size: "sm" }));
  const el = h(
    "section",
    { class: "chat", "aria-label": `和 ${account} 聊天`, dataset: { minimized: "false" } },
    h(
      "header",
      { class: "chat__header" },
      h(
        "button",
        { class: "chat__who", type: "button", title: "看個人資料", onClick: () => emit("member:show", win.memberId) },
        avatarWrap,
        h("span", { class: "chat__name" }, h("strong", null, account, " ", levelSlot), status),
        badge,
      ),
      minimize,
      h("button", { class: "icon-btn icon-btn--sm", type: "button", "aria-label": "關閉聊天", onClick: () => close(account) }, icon("x", { size: "sm" })),
    ),
    log,
    form,
    blocked,
  );

  const win = {
    account,
    el,
    log,
    body,
    older,
    empty,
    receipt,
    typing,
    input,
    form,
    blocked,
    avatarWrap,
    status,
    badge,
    levelSlot,
    level: null,
    memberId: conversations.get(account)?.partner.member_id ?? null,
    avatarSet: false,
    messages: [],
    ids: new Set(),
    queue: [],
    pending: new Map(), // bubble element -> text, while sending
    loaded: false,
    more: false,
    lastDay: null,
    lastTypingSent: 0,
    typingTimer: null,
  };

  const setMinimized = (value) => {
    el.dataset.minimized = String(value);
    if (!value) {
      scrollToBottom(win);
      markRead(win);
    }
    refreshBadges();
  };
  minimize.addEventListener("click", () => setMinimized(el.dataset.minimized !== "true"));
  el.querySelector(".chat__header").addEventListener("dblclick", () => setMinimized(el.dataset.minimized !== "true"));
  older.addEventListener("click", () => loadOlder(win));
  log.addEventListener("scroll", () => log.scrollTop < 40 && loadOlder(win), { passive: true });
  el.addEventListener("focusin", () => markRead(win));
  el.addEventListener("pointerdown", () => markRead(win));

  const submit = () => {
    const content = input.value.trim();
    if (!content) return;
    input.value = "";
    autosize();
    send(win, content);
  };
  const autosize = () => {
    input.style.height = "auto";
    input.style.height = `${Math.min(input.scrollHeight, 120)}px`;
  };
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    submit();
    input.focus();
  });
  input.addEventListener("keydown", (event) => {
    // Enter sends, Shift+Enter starts a new line; never while an IME is composing (注音).
    if (event.key === "Enter" && !event.shiftKey && !event.isComposing && event.keyCode !== 229) {
      event.preventDefault();
      submit();
    }
  });
  input.addEventListener("input", () => {
    autosize();
    const now = Date.now();
    if (input.value.trim() && now - win.lastTypingSent > TYPING_SEND_MS && isOnline(account)) {
      win.lastTypingSent = now;
      socket.emit("chat:typing", { to: account });
    }
  });
  return win;
}

function close(account) {
  const win = windows.get(account);
  if (!win) return;
  clearTimeout(win.typingTimer);
  win.el.remove();
  windows.delete(account);
}

/** Someone I blocked: close our window and drop the conversation from the list. */
export function forgetChat(account) {
  close(account);
  conversations.delete(account);
  refreshBadges();
}

export function openChat(account, { focus = true } = {}) {
  if (!account || account === me.account) return null;
  let win = windows.get(account);
  if (!win) {
    win = createWindow(account);
    windows.set(account, win);
    // Desktop shows a few windows side by side; the oldest gives way.
    for (const other of windows.keys()) {
      if (windows.size <= MAX_WINDOWS) break;
      if (other !== account) close(other);
    }
    updateHeader(win);
    loadHistory(win);
  }
  win.el.dataset.minimized = "false";
  container.append(win.el); // to the front (the visible one on phones)
  if (focus) win.input.focus({ preventScroll: true });
  markRead(win);
  refreshBadges();
  return win;
}

/* ---------- Pushed events ---------- */

/** Keeps the conversation list current for a message sent or received anywhere. */
function notePartnerMessage(message) {
  const mine = message.from === me.account;
  const partner = mine ? message.to : message.from;
  let conversation = conversations.get(partner);
  const known = conversation?.last?.id >= message.id;
  if (!conversation) {
    conversation = { partner: { account: partner, member_id: windows.get(partner)?.memberId ?? null }, online: isOnline(partner), unread: 0, last: message };
    conversations.set(partner, conversation);
    if (!conversation.partner.member_id) loadConversations(); // fetches the avatar id
  }
  if (!known) {
    conversation.last = message;
    if (!mine) conversation.unread += 1;
  }
  return { partner, mine, known };
}

function onMessage(message) {
  const { partner, mine, known } = notePartnerMessage(message);
  let win = windows.get(partner);
  if (win) {
    // My own message from this tab: its send() is about to add it.
    const sending = mine && [...win.pending.values()].includes(message.content);
    if (!sending) addMessage(win, message);
    if (!mine) hideTyping(win);
  } else if (!mine && !known) {
    if (!phone.matches) win = openChat(partner, { focus: false });
    else toast(`${partner}：${message.content}`, { action: { label: "回覆", onClick: () => openChat(partner) } });
  }
  if (win) markRead(win);
  refreshBadges();
}

function onRead(receipt) {
  if (receipt.by === me.account) {
    // I read them in another tab.
    const win = windows.get(receipt.partner);
    for (const message of win?.messages ?? []) {
      if (message.from === receipt.partner && message.id <= receipt.up_to) message.read_at ??= receipt.read_at;
    }
    loadConversations();
    return;
  }
  const win = windows.get(receipt.by);
  for (const message of win?.messages ?? []) {
    if (message.from === me.account && message.id <= receipt.up_to) message.read_at ??= receipt.read_at;
  }
  const conversation = conversations.get(receipt.by);
  if (conversation?.last.from === me.account && conversation.last.id <= receipt.up_to) conversation.last.read_at = receipt.read_at;
  if (win) updateReceipt(win);
}

function hideTyping(win) {
  clearTimeout(win.typingTimer);
  win.typing.hidden = true;
}

function onTyping({ from }) {
  const win = windows.get(from);
  if (!win) return;
  const stick = nearBottom(win);
  win.typing.hidden = false;
  if (stick) scrollToBottom(win);
  clearTimeout(win.typingTimer);
  win.typingTimer = setTimeout(() => hideTyping(win), TYPING_SHOW_MS);
}

function onPresence(states) {
  for (const [account, state] of Object.entries(states)) presence.set(account, String(state).startsWith("on"));
  for (const win of windows.values()) updateHeader(win);
  if (!panel.hidden) renderList();
}

function catchUp() {
  loadConversations();
  for (const win of windows.values()) if (win.loaded) loadHistory(win);
}

export function initChat() {
  baseTitle = document.title;
  socket.on("chat:message", onMessage);
  socket.on("chat:read", onRead);
  socket.on("chat:typing", onTyping);
  socket.on("awake_result", onPresence);
  socket.io.on("reconnect", catchUp); // pushes sent while disconnected were missed

  on("friends:changed", (list) => {
    friends = list;
    for (const f of list) if (!presence.has(f.account)) presence.set(f.account, f.online);
    if (!panel.hidden) renderList();
  });

  button.addEventListener("click", () => setPanel(panel.hidden));
  document.addEventListener("click", (event) => {
    if (!panel.hidden && !event.target.closest(".chats-menu")) setPanel(false);
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !panel.hidden) {
      setPanel(false);
      button.focus();
    }
  });
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState !== "visible") return;
    loadConversations();
  });
  setInterval(() => document.visibilityState === "visible" && loadConversations(), POLL_MS);

  window.addEventListener("pagehide", () => socket.emit("logout", {}));
  loadConversations();
}
