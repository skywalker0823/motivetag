// Member page entry point: loads who I am, then starts every panel.
import { api } from "../../lib/api.js";
import { $ } from "../../lib/dom.js";
import { hydrateIcons } from "../../lib/icons.js";
import { pullToRefresh } from "../../lib/pull-refresh.js";
import { socket } from "../../lib/socket.js";
import { toastError } from "../../lib/toast.js";
import { initChat, openChat } from "./chat.js";
import { initComposer } from "./composer.js";
import { initFeed, refreshFeed, resetFeed } from "./feed.js";
import { initFriends } from "./friends.js";
import { initNotifications } from "./notifications.js";
import { initProfile, showMember } from "./profile.js";
import { initSettings } from "./settings.js";
import { initSuggestions } from "./suggest.js";
import { bootstrap, me, on, showView } from "./state.js";
import { initTags } from "./tags.js";
import { initTour } from "./tour.js";
import { initVerify } from "./verify.js";

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

const phone = matchMedia("(max-width: 899px)");

/** On phones the top bar slides away while scrolling down and returns on the way up. */
function autoHideTopbar() {
  const topbar = $(".topbar");
  let lastY = window.scrollY;
  window.addEventListener(
    "scroll",
    () => {
      const y = window.scrollY;
      const busy = topbar.contains(document.activeElement) || !$("#notif-panel").hidden;
      if (!phone.matches || busy || y < 80) topbar.classList.remove("topbar--hidden");
      else if (y > lastY + 8) topbar.classList.add("topbar--hidden");
      else if (y < lastY - 8) topbar.classList.remove("topbar--hidden");
      if (Math.abs(y - lastY) > 8) lastY = y;
    },
    { passive: true },
  );
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
  initVerify(result.data);
  initSettings();
  initComposer();
  initFeed();
  initTags();
  const friends = initFriends();
  initSuggestions(friends.invite);
  initChat();
  initNotifications();
  initTour(result.data.first_signup);
  autoHideTopbar();
  pullToRefresh({
    onRefresh: refreshFeed,
    enabled: () => document.body.dataset.view === "feed" && !document.querySelector("dialog[open]"),
  });

  on("feed:tag", showFeedFor);
  on("member:show", (id) => id && showMember(id));
  on("chat:open", openChat);
  on("friend:invite", (account) => friends.invite(account).catch((e) => toastError(e)));
  on("friend:accept", ({ id, account }) => friends.accept(id, account));
}

start();
