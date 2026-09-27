// The feed: five posts at a time with infinite scroll, optionally filtered by a tag.
import { api, errorMessage } from "../../lib/api.js";
import { $, h } from "../../lib/dom.js";
import { renderPost } from "./post.js";

const PAGE = 5;
const feed = $("#feed");
const status = $("#feed-status");
const sentinel = $("#feed-sentinel");

let offset = 0;
let tag = null;
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

function finish() {
  done = true;
  const text = feed.children.length
    ? "沒有更多貼文了"
    : tag
      ? `還沒有人用 #${tag} 發文，來發第一篇吧！`
      : "動態還是空的。訂閱幾個標籤、加些好友，或發第一篇貼文吧！";
  setStatus(h("p", { class: "empty" }, text));
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
    const query = tag ? { page: offset, key: tag } : { page: offset };
    const result = await api("/api/blocks", { query });
    if (current !== generation) return;
    const posts = result.ok ? result.data : [];
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
  loadMore();
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
  resetFeed();
}
