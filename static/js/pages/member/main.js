// Member page entry point: loads who I am, then starts every panel.
import { api } from "../../lib/api.js";
import { $ } from "../../lib/dom.js";
import { hydrateIcons } from "../../lib/icons.js";
import { socket } from "../../lib/socket.js";
import { toastError } from "../../lib/toast.js";
import { initChat, openChat } from "./chat.js";
import { initComposer } from "./composer.js";
import { initFeed, resetFeed } from "./feed.js";
import { initFriends } from "./friends.js";
import { initNotifications } from "./notifications.js";
import { initProfile, showMember } from "./profile.js";
import { initSettings } from "./settings.js";
import { bootstrap, me, on, showView } from "./state.js";
import { initTags } from "./tags.js";
import { initTour } from "./tour.js";

hydrateIcons();

function initTopbar() {
  const search = $("#tag-search");
  search.addEventListener("submit", (event) => {
    event.preventDefault();
    const tag = search.elements.tag.value.trim().replace(/^#+/, "");
    if (tag) showFeedFor(tag);
  });
  $("#refresh").addEventListener("click", () => {
    search.reset();
    resetFeed();
    window.scrollTo({ top: 0, behavior: "smooth" });
  });
  $("#signout").addEventListener("click", async () => {
    try {
      await api("/api/member", { method: "DELETE" });
    } finally {
      socket.emit("logout", { account: me.account });
      location.assign("/");
    }
  });
  for (const tab of document.querySelectorAll(".tabbar [data-tab]")) {
    tab.addEventListener("click", () => {
      // Tapping the tab you are on scrolls back to the top, as in most apps.
      if (document.body.dataset.view === tab.dataset.tab) window.scrollTo({ top: 0, behavior: "smooth" });
      else showView(tab.dataset.tab);
    });
  }
}

function showFeedFor(tag) {
  $("#tag-search-input").value = tag;
  showView("feed");
  resetFeed(tag);
}

async function start() {
  let result = bootstrap.me ? { ok: true, data: bootstrap.me } : null;
  try {
    result ??= await api("/api/member");
  } catch (error) {
    toastError(error, "載入失敗，請重新整理");
    return;
  }
  if (!result.ok || !result.data) {
    location.replace("/"); // signed out, or the session expired
    return;
  }
  me.id = result.data.member_id;
  me.account = result.data.account;
  document.title = `${me.account} - MotiveTag`;

  initTopbar();
  initProfile(result.data);
  initSettings();
  initComposer();
  initFeed();
  initTags();
  const friends = initFriends();
  initChat();
  initNotifications();
  initTour(result.data.first_signup);

  on("feed:tag", showFeedFor);
  on("member:show", (id) => id && showMember(id));
  on("chat:open", openChat);
  on("friend:invite", (account) => friends.invite(account).catch((e) => toastError(e)));
  on("friend:accept", ({ id, account }) => friends.accept(id, account));
}

start();
