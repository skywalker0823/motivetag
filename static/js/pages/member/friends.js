// Friends: invitations both ways, the friend list and who is online right now.
import { api, errorMessage } from "../../lib/api.js";
import { confirmDialog } from "../../lib/confirm.js";
import { $, busy, h, img } from "../../lib/dom.js";
import { icon } from "../../lib/icons.js";
import { socket } from "../../lib/socket.js";
import { toast, toastError } from "../../lib/toast.js";
import { notify } from "./notifications.js";
import { avatarUrl, DEFAULT_AVATAR, emit, me } from "./state.js";

// The server pushes changes (online, offline, calling); this re-check is only a fallback.
const PRESENCE_MS = 30000;
let relations = [];
const presence = new Map(); // account -> "on" | "off" | "on_calling"

const lists = {
  incoming: $("#friends-incoming"),
  friends: $("#friends-list"),
  outgoing: $("#friends-outgoing"),
};

function other(relation) {
  return relation.req_from === me.account
    ? { account: relation.req_to, id: relation.req_to_id }
    : { account: relation.req_from, id: relation.req_from_id };
}

function person({ account, id }, status) {
  return h(
    "button",
    {
      class: "person",
      type: "button",
      dataset: { account, online: String(presence.get(account)?.startsWith("on") ?? false) },
      onClick: () => emit("member:show", id),
    },
    h("span", { class: "person__avatar" }, img(avatarUrl(id), DEFAULT_AVATAR, { class: "avatar avatar--sm" })),
    h("span", { class: "person__name" }, account),
    status && h("span", { class: "person__status" }, status),
  );
}

const empty = (text) => h("li", { class: "empty" }, text);

function render() {
  const incoming = relations.filter((r) => String(r.status) === "1" && r.req_to === me.account);
  const outgoing = relations.filter((r) => String(r.status) === "1" && r.req_from === me.account);
  const friends = relations.filter((r) => String(r.status) === "0");

  lists.incoming.closest(".friend-group").hidden = incoming.length === 0;
  lists.incoming.replaceChildren(
    ...incoming.map((r) => {
      const who = other(r);
      return h(
        "li",
        null,
        person(who),
        h(
          "button",
          { class: "btn btn--sm", type: "button", onClick: (e) => busy(e.currentTarget, () => accept(r.friend_ship_id, who.account)) },
          "接受",
        ),
        h(
          "button",
          { class: "btn btn--secondary btn--sm", type: "button", onClick: (e) => busy(e.currentTarget, () => decline(r.friend_ship_id, who.account)) },
          "拒絕",
        ),
      );
    }),
  );

  lists.friends.replaceChildren(
    ...(friends.length
      ? friends.map((r) => {
          const who = other(r);
          const state = presence.get(who.account);
          return h(
            "li",
            null,
            person(who, state === "on_calling" ? "想跟你聊天" : state === "on" ? "上線中" : ""),
            h(
              "button",
              {
                class: "icon-btn icon-btn--sm",
                type: "button",
                "aria-label": `和 ${who.account} 聊天`,
                title: "聊天",
                dataset: { chat: who.account, calling: String(state === "on_calling") },
                onClick: () => emit("chat:open", who.account),
              },
              icon("comment", { size: "sm" }),
            ),
            h(
              "button",
              {
                class: "icon-btn icon-btn--sm",
                type: "button",
                "aria-label": `刪除好友 ${who.account}`,
                title: "刪除好友",
                onClick: (e) => busy(e.currentTarget, () => remove(r.friend_ship_id, who.account)),
              },
              icon("user-x", { size: "sm" }),
            ),
          );
        })
      : [empty("還沒有好友，輸入帳號送出邀請吧")]),
  );

  lists.outgoing.closest(".friend-group").hidden = outgoing.length === 0;
  lists.outgoing.replaceChildren(...outgoing.map((r) => h("li", null, person(other(r), "等待中"))));

  const calling = friends.some((r) => presence.get(other(r).account) === "on_calling");
  $("#tab-friends-badge").hidden = incoming.length === 0 && !calling;
  $("#tab-friends-badge").textContent = incoming.length ? String(incoming.length) : "";
}

export async function loadFriends() {
  try {
    const result = await api("/api/friend");
    relations = Array.isArray(result.ok) ? result.ok : [];
  } catch (error) {
    toastError(error, "好友清單載入失敗");
  }
  render();
}

async function invite(account) {
  if (account === me.account) throw new Error("不能加自己為好友");
  const check = await api("/api/friend", { query: { who: account } });
  if (check.error) throw check;
  const result = await api("/api/friend", { method: "POST", body: { who: account } });
  if (result.error) throw result;
  if (result.ok === "FAST") {
    // They had already invited me: accepting is what I meant.
    await accept(result.data[0].friend_ship_id, account);
    return;
  }
  toast(`已送出好友邀請給 ${account}`, { type: "success" });
  notify(account, "friend_invite");
  await loadFriends();
}

async function accept(id, account) {
  try {
    const result = await api("/api/friend", { method: "PATCH", body: { friend_ship_id: id } });
    if (!result.data_changed) throw result;
    toast(`你和 ${account} 成為好友了`, { type: "success" });
    notify(account, "friend_accept");
  } catch (error) {
    toastError(error, "接受邀請失敗");
  }
  await loadFriends();
}

async function decline(id, account) {
  try {
    const result = await api("/api/friend", { method: "DELETE", body: { friend_ship_id: id } });
    if (result.error) throw result;
    notify(account, "friend_decline");
  } catch (error) {
    toastError(error, "操作失敗");
  }
  await loadFriends();
}

async function remove(id, account) {
  const ok = await confirmDialog({
    title: `刪除好友 ${account}？`,
    message: "之後要再成為好友，需要重新送出邀請。",
    confirmText: "刪除好友",
    danger: true,
  });
  if (!ok) return;
  try {
    const result = await api("/api/friend", { method: "DELETE", body: { friend_ship_id: id } });
    if (result.error) throw result;
    toast(`已刪除好友 ${account}`);
  } catch (error) {
    toastError(error, "刪除好友失敗");
  }
  await loadFriends();
}

function askPresence() {
  const friends = relations.filter((r) => String(r.status) === "0").map((r) => other(r).account);
  if (!friends.length) return;
  socket.emit("awake", {
    type: "awake_call",
    account: me.account,
    check_who_is_awake_too: Object.fromEntries(friends.map((f) => [f, "off"])),
  });
}

export function initFriends() {
  const form = $("#friend-invite");
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    const account = form.elements.account.value.trim();
    if (!account) return form.elements.account.focus();
    busy(form.querySelector("[type=submit]"), async () => {
      try {
        await invite(account);
        form.reset();
      } catch (error) {
        toastError(error, errorMessage(error, error.message));
      }
    });
  });

  socket.on("awake_result", (states) => {
    let changed = false;
    for (const [account, state] of Object.entries(states)) {
      if (presence.get(account) !== state) changed = true;
      presence.set(account, state);
    }
    if (changed) render();
  });
  setInterval(() => document.visibilityState === "visible" && askPresence(), PRESENCE_MS);
  socket.io.on("reconnect", askPresence);
  document.addEventListener("visibilitychange", () => document.visibilityState === "visible" && askPresence());

  loadFriends().then(askPresence);
  return { invite, accept };
}
