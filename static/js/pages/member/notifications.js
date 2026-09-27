// The bell: polls for new notifications and marks them read when the panel opens.
import { api } from "../../lib/api.js";
import { $, h } from "../../lib/dom.js";
import { timeAgo } from "../../lib/time.js";

const POLL_MS = 15000;
const button = $("#notif-button");
const panel = $("#notif-panel");
const list = $("#notif-list");
const count = $("#notif-count");
let unread = [];

async function poll() {
  try {
    const result = await api("/api/notifi");
    unread = result.data ?? [];
  } catch {
    return;
  }
  count.hidden = unread.length === 0;
  count.textContent = unread.length > 99 ? "99+" : String(unread.length);
  button.setAttribute("aria-label", unread.length ? `通知（${unread.length} 則未讀）` : "通知");
}

function render() {
  list.replaceChildren(
    ...(unread.length
      ? [...unread].reverse().map((n) => h("li", null, n.content, timeAgo(n.send_time)))
      : [h("li", { class: "empty" }, "沒有新的通知")]),
  );
}

function setOpen(open) {
  panel.hidden = !open;
  button.setAttribute("aria-expanded", String(open));
  if (!open) return;
  render();
  if (unread.length) {
    // Seen: the server deletes them, the badge clears, the list stays until closed.
    api("/api/notifi", { method: "DELETE" }).catch(() => {});
    unread = [];
    count.hidden = true;
  }
}

/**
 * Sends `account` a notification. The server writes the text for each `type`:
 * friend_invite, friend_accept, friend_decline or chat_missed.
 */
export function notify(account, type) {
  return api("/api/notifi", { method: "POST", body: { who: account, type } }).catch(() => {});
}

export function initNotifications() {
  button.addEventListener("click", () => setOpen(panel.hidden));
  document.addEventListener("click", (event) => {
    if (!panel.hidden && !event.target.closest(".notifications")) setOpen(false);
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !panel.hidden) {
      setOpen(false);
      button.focus();
    }
  });
  poll();
  setInterval(() => document.visibilityState === "visible" && poll(), POLL_MS);
}
