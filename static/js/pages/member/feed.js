// The feed: five posts at a time with infinite scroll, optionally filtered by a tag.
import { api } from "../../lib/api.js";
import { $ } from "../../lib/dom.js";
import { toastError } from "../../lib/toast.js";
import { renderPost } from "./post.js";

const PAGE = 5;
const feed = $("#feed");
const spinner = $("#feed-spinner");
const end = $("#feed-end");
const sentinel = $("#feed-sentinel");

let offset = 0;
let tag = null;
let loading = false;
let done = false;
let generation = 0; // bumps on reset so a late response from an old query is dropped

function show(posts) {
  const rendered = posts.map(renderPost);
  feed.append(...rendered.map((post) => post.el));
  for (const post of rendered) post.loadComments(); // all at once, not one by one
}

function finish() {
  done = true;
  end.hidden = false;
  if (feed.children.length) end.textContent = "沒有更多貼文了";
  else if (tag) end.textContent = `還沒有人用 #${tag} 發文，來發第一篇吧！`;
  else end.textContent = "動態還是空的。訂閱幾個標籤、加些好友，或發第一篇貼文吧！";
}

function nearBottom() {
  return sentinel.getBoundingClientRect().top < window.innerHeight + 600;
}

export async function loadMore() {
  if (loading || done) return;
  loading = true;
  spinner.hidden = false;
  const current = generation;
  try {
    const query = tag ? { page: offset, key: tag } : { page: offset };
    const result = await api("/api/blocks", { query });
    if (current !== generation) return;
    const posts = result.ok ? result.data : [];
    show(posts);
    offset += PAGE;
    if (posts.length < PAGE) finish();
  } catch (error) {
    if (current === generation) toastError(error, "動態載入失敗");
  } finally {
    if (current === generation) {
      loading = false;
      spinner.hidden = true;
      if (!done && nearBottom()) loadMore(); // the page is still short: keep filling it
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
  feed.replaceChildren();
  end.hidden = true;
  $("#feed-filter").hidden = !tag;
  $("#feed-filter-tag").textContent = tag ? `#${tag}` : "";
  loadMore();
}

/** Put a post I just wrote at the top. */
export function prependPost(post) {
  const rendered = renderPost(post);
  feed.prepend(rendered.el);
  rendered.loadComments();
  if (done && feed.children.length === 1) end.textContent = "沒有更多貼文了";
}

export function initFeed() {
  new IntersectionObserver((entries) => entries[0].isIntersecting && loadMore(), {
    rootMargin: "600px 0px",
  }).observe(sentinel);
  $("#feed-filter-clear").addEventListener("click", () => resetFeed());
  resetFeed();
}
