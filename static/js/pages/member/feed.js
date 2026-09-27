// The feed with infinite scroll: my feed (friends, my tags, me), explore (everyone's
// public posts) or one tag.
import { api, errorMessage } from "../../lib/api.js";
import { $, busy, h } from "../../lib/dom.js";
import { icon } from "../../lib/icons.js";
import { toastError } from "../../lib/toast.js";
import { renderPost } from "./post.js";
import { on } from "./state.js";
import { subscribe, suggestedTags } from "./tags.js";

const PAGE = 10; // FEED_PAGE in data/data.py
const feed = $("#feed");
const status = $("#feed-status");
const sentinel = $("#feed-sentinel");

let offset = 0;
let tag = null;
let mode = "mine"; // or "explore"
let loading = false;
let done = false;
let generation = 0; // bumps on reset so a late response from an old query is dropped
const shown = new Set(); // post ids on screen: offsets shift when new posts arrive

function skeleton() {
  return h(
    "div",
    { class: "card post post--skeleton", "aria-hidden": "true" },
    h("div", { class: "post__header" }, h("span", { class: "sk sk--avatar" }), h("span", { class: "sk sk--line", style: { width: "40%" } })),
    h("span", { class: "sk sk--line" }),
    h("span", { class: "sk sk--line", style: { width: "70%" } }),
  );
}

function setStatus(...children) {
  status.replaceChildren(...children);
}

/** My feed is empty: offer tags to subscribe to in one tap, and the explore feed. */
function emptyMine() {
  const chips = h("div", { class: "chips chips--center" });
  const box = h(
    "div",
    { class: "card empty-feed" },
    h("p", { class: "empty-feed__title" }, "你的動態還是空的"),
    h("p", { class: "empty-feed__text" }, "動態會出現好友、你訂閱的標籤和你自己的貼文。先訂閱幾個感興趣的標籤吧："),
    chips,
    h(
      "button",
      { class: "btn btn--secondary", type: "button", onClick: () => setMode("explore") },
      icon("globe", { size: "sm" }),
      "看看大家在聊什麼",
    ),
  );
  suggestedTags().then((names) => {
    chips.replaceChildren(
      ...names.map((name) =>
        h(
          "button",
          {
            class: "chip chip--add",
            type: "button",
            "aria-label": `訂閱 #${name}`,
            onClick: (event) => busy(event.currentTarget, () => subscribe(name).catch((e) => toastError(e, "訂閱失敗"))),
          },
          `#${name}`,
          icon("plus", { size: "sm" }),
        ),
      ),
    );
  });
  return box;
}

function finish() {
  done = true;
  if (!feed.children.length && !tag && mode === "mine") return setStatus(emptyMine());
  const text = feed.children.length
    ? "沒有更多貼文了"
    : tag
      ? `還沒有人用 #${tag} 發文，來發第一篇吧！`
      : "還沒有人發文，來發第一篇吧！";
  setStatus(h("p", { class: "empty" }, text));
}

function fetchPage() {
  if (tag) return api("/api/blocks", { query: { page: offset, key: tag } });
  if (mode === "explore") return api("/api/v1/posts/explore", { query: { offset } });
  return api("/api/blocks", { query: { page: offset } });
}

function nearBottom() {
  return sentinel.getBoundingClientRect().top < window.innerHeight + 800;
}

export async function loadMore() {
  if (loading || done) return;
  loading = true;
  const current = generation;
  setStatus(...(feed.children.length ? [skeleton()] : [skeleton(), skeleton(), skeleton()]));
  try {
    const result = await fetchPage();
    if (current !== generation) return;
    const posts = Array.isArray(result.data) ? result.data : [];
    offset += PAGE;
    const fresh = posts.filter((post) => !shown.has(post.block_id));
    for (const post of fresh) shown.add(post.block_id);
    feed.append(...fresh.map(renderPost));
    setStatus();
    if (posts.length < PAGE) finish();
  } catch (error) {
    if (current !== generation) return;
    setStatus(
      h(
        "div",
        { class: "empty" },
        h("p", null, errorMessage(error, "動態載入失敗")),
        h("button", { class: "btn btn--secondary btn--sm", type: "button", onClick: () => loadMore() }, "再試一次"),
      ),
    );
  } finally {
    if (current === generation) {
      loading = false;
      if (!done && status.childElementCount === 0 && nearBottom()) loadMore(); // page still short
    }
  }
}

/** Start over: the whole feed, or only posts tagged `newTag`. */
export function resetFeed(newTag = null) {
  generation += 1;
  tag = newTag;
  offset = 0;
  loading = false;
  done = false;
  shown.clear();
  feed.replaceChildren();
  $("#feed-filter").hidden = !tag;
  $("#feed-filter-tag").textContent = tag ? `#${tag}` : "";
  $("#feed-tabs").hidden = Boolean(tag);
  loadMore();
}

/** Switch between my feed and explore (and leave a tag filter). */
export function setMode(newMode) {
  mode = newMode;
  for (const button of document.querySelectorAll("#feed-tabs [data-mode]")) {
    button.setAttribute("aria-pressed", String(button.dataset.mode === mode));
  }
  resetFeed();
}

/** Put a post I just wrote at the top. */
export function prependPost(post) {
  shown.add(post.block_id);
  feed.prepend(renderPost(post));
  if (done && feed.children.length === 1) setStatus(h("p", { class: "empty" }, "沒有更多貼文了"));
}

export function initFeed() {
  new IntersectionObserver((entries) => entries[0].isIntersecting && loadMore(), {
    rootMargin: "800px 0px",
  }).observe(sentinel);
  $("#feed-filter-clear").addEventListener("click", () => resetFeed());
  for (const button of document.querySelectorAll("#feed-tabs [data-mode]")) {
    button.addEventListener("click", () => button.dataset.mode !== mode && setMode(button.dataset.mode));
  }
  // A new or dropped tag changes what my feed holds.
  on("tags:changed", () => mode === "mine" && !tag && resetFeed());
  resetFeed();
}
