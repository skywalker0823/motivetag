// One post in the feed: author, text with clickable #tags, image, poll, reactions and
// comments. Everything arrives with the feed (see api_blocks.with_extras), so a post
// needs no requests of its own until the member acts. Actions update the screen
// first and roll back if the server refuses.
import { api } from "../../lib/api.js";
import { confirmDialog } from "../../lib/confirm.js";
import { h, img } from "../../lib/dom.js";
import { icon } from "../../lib/icons.js";
import { frameClass, levelBadge } from "../../lib/levels.js";
import { openLightbox } from "../../lib/lightbox.js";
import { reportDialog } from "../../lib/report.js";
import { timeAgo } from "../../lib/time.js";
import { toast, toastError } from "../../lib/toast.js";
import { ANON_AVATAR, avatarUrl, DEFAULT_AVATAR, emit, me } from "./state.js";

const VISIBILITY = {
  SECRET: ["私密", "pill pill--secret"],
  Anonymous: ["匿名", "pill pill--anon"],
};
const COLLAPSED_COMMENTS = 3;
// Same rule as module/tag_filter.py: letters, digits or _, ended by anything else.
const HASHTAG = /#([\p{L}\p{N}_]{1,30})/gu;

export function renderPost(post) {
  const anonymous = post.content_type === "Anonymous";
  const mine = post.member_id === me.id;
  const [visibilityLabel, visibilityClass] = VISIBILITY[post.content_type] ?? [];
  const score = h("span", { class: "post__score", title: "留言評分總和", hidden: true });

  const article = h("article", {
    class: "card post",
    dataset: { id: post.block_id, ...(post.member_id ? { author: post.member_id } : {}) },
  });
  const actions = renderActions(post);
  // Native append() would print a skipped part (null) as text, so go through h()'s rules.
  const parts = [
    h(
      "header",
      { class: "post__header" },
      h(
        "button",
        {
          class: "post__author",
          type: "button",
          disabled: anonymous,
          onClick: () => emit("member:show", post.member_id),
        },
        img(anonymous ? ANON_AVATAR : avatarUrl(post.member_id), DEFAULT_AVATAR, {
          class: `avatar${frameClass(post.level)}`,
          width: 40,
          height: 40,
        }),
        h(
          "span",
          { class: "post__who" },
          h(
            "span",
            { class: "post__name" },
            anonymous ? (mine ? "匿名（你）" : "匿名") : `@${post.account}`,
            " ",
            levelBadge(post.level),
          ),
          h(
            "span",
            { class: "post__meta" },
            timeAgo(post.build_time),
            visibilityLabel && h("span", { class: visibilityClass }, visibilityLabel),
          ),
        ),
      ),
      score,
      mine &&
        h(
          "button",
          {
            class: "icon-btn icon-btn--sm",
            type: "button",
            "aria-label": "刪除貼文",
            title: "刪除貼文",
            onClick: () => deletePost(post, article),
          },
          icon("trash"),
        ),
      !mine &&
        h(
          "button",
          {
            class: "icon-btn icon-btn--sm post__report",
            type: "button",
            "aria-label": "檢舉貼文",
            title: "檢舉",
            onClick: () => report("post", post.block_id, anonymous ? null : post.account, post.member_id, article),
          },
          icon("flag", { size: "sm" }),
        ),
    ),
    h("p", { class: "post__content" }, withHashtags(post.content)),
    post.block_img && renderImage(post, () => like(actions)),
    post.votes?.length ? renderPoll(post) : null,
    actions,
    renderComments(post, score),
  ];
  article.append(...parts.filter((part) => part instanceof Node));
  return article;
}

/** Reports something; it leaves my screen, and so does everything by someone I block. */
async function report(type, id, account, authorId, element) {
  const result = await reportDialog({ type, id, account });
  if (!result) return;
  element.remove();
  if (result.blocked) removeAuthor(authorId);
}

/** Takes a blocked member's posts and comments off the page (the server leaves them out from now on). */
export function removeAuthor(memberId) {
  if (!memberId) return;
  for (const el of document.querySelectorAll(`.post[data-author="${memberId}"], .comment[data-author="${memberId}"]`)) {
    el.remove();
  }
}

/** Text with each #tag turned into a button that filters the feed by it. */
function withHashtags(text) {
  const parts = [];
  let last = 0;
  for (const match of text.matchAll(HASHTAG)) {
    parts.push(text.slice(last, match.index));
    const name = match[1];
    parts.push(
      h("button", { class: "hashtag", type: "button", onClick: () => emit("feed:tag", name) }, `#${name}`),
    );
    last = match.index + match[0].length;
  }
  parts.push(text.slice(last));
  return parts;
}

/** Double-tapping the image likes the post, as in most photo apps. */
function like(actions) {
  const button = actions.querySelector(".action");
  if (button.getAttribute("aria-pressed") !== "true") button.click();
}

const DOUBLE_TAP_MS = 250;

function renderImage(post, onDoubleTap) {
  const src = `/images/${post.block_img}`;
  const image = h("img", { src, alt: "貼文圖片", loading: "lazy", decoding: "async" });
  const frame = h("button", { class: "post__image", type: "button", "aria-label": "放大圖片（點兩下按讚）" }, image);
  let pending = null;
  frame.addEventListener("click", (event) => {
    if (event.detail === 0) return openLightbox(src, "貼文圖片"); // keyboard: no double tap
    if (pending) {
      clearTimeout(pending);
      pending = null;
      const heart = h("span", { class: "post__burst", "aria-hidden": "true" }, icon("like"));
      heart.addEventListener("animationend", () => heart.remove());
      frame.append(heart);
      onDoubleTap();
      return;
    }
    pending = setTimeout(() => {
      pending = null;
      openLightbox(src, "貼文圖片");
    }, DOUBLE_TAP_MS);
  });
  // The frame keeps its size while loading, so the feed does not jump.
  image.addEventListener("load", () => frame.classList.add("is-loaded"), { once: true });
  image.addEventListener("error", () => frame.remove(), { once: true });
  return frame;
}

async function deletePost(post, article) {
  const ok = await confirmDialog({
    title: "刪除這篇貼文？",
    message: "貼文、留言和投票都會一起刪除，無法復原。",
    confirmText: "刪除",
    danger: true,
  });
  if (!ok) return;
  article.classList.add("is-leaving");
  try {
    const result = await api("/api/blocks", { method: "DELETE", body: { block_id: post.block_id } });
    if (!result.ok) throw result;
    setTimeout(() => article.remove(), 200);
    toast("貼文已刪除");
  } catch (error) {
    article.classList.remove("is-leaving");
    toastError(error, "刪除失敗");
  }
}

// ---------- Likes ----------

const LABELS = { like: "讚", dislike: "爛" };

function pop(button) {
  button.classList.remove("pop");
  void button.offsetWidth; // restart the animation
  button.classList.add("pop");
}

/** 讚 and 爛: one of them at most; tapping the pressed one again takes it back. */
function renderActions(post) {
  let reaction = post.liked ? "like" : post.disliked ? "dislike" : null;
  let counts = { like: Number(post.good || 0), dislike: Number(post.bad || 0) };
  let latest = 0; // only the answer to the last tap counts
  const buttons = {};

  const show = () => {
    for (const [kind, button] of Object.entries(buttons)) {
      const on = reaction === kind;
      button.setAttribute("aria-pressed", String(on));
      button.title = on ? `再按一次取消${LABELS[kind]}` : LABELS[kind];
      button.querySelector("span").textContent = counts[kind] > 0 ? String(counts[kind]) : "";
    }
  };

  const choose = async (kind) => {
    const next = reaction === kind ? null : kind;
    const before = { reaction, counts: { ...counts } };
    if (reaction) counts[reaction] -= 1;
    if (next) counts[next] += 1;
    reaction = next;
    show();
    if (next) pop(buttons[next]);
    const request = ++latest;
    try {
      const { data } = await api(`/api/v1/posts/${post.block_id}/reaction`, { method: "PUT", body: { reaction: next } });
      if (request !== latest) return;
      reaction = data.reaction;
      counts = { like: data.good, dislike: data.bad };
    } catch (error) {
      if (request !== latest) return;
      ({ reaction, counts } = before);
      toastError(error);
    }
    show();
  };

  for (const kind of ["like", "dislike"]) {
    buttons[kind] = h(
      "button",
      { class: "action", type: "button", "aria-label": LABELS[kind], onClick: () => choose(kind) },
      icon(kind),
      h("span"),
    );
  }
  show();
  return h("footer", { class: "post__actions" }, buttons.like, buttons.dislike);
}

// ---------- Poll ----------

function renderPoll(post) {
  const box = h("div", { class: "poll", role: "group", "aria-label": "投票" });
  let options = post.votes.map((option) => ({ ...option }));

  const showResults = () => {
    const total = options.reduce((sum, option) => sum + option.count, 0);
    box.replaceChildren(
      ...options.map((option) => {
        const percent = total ? Math.round((option.count / total) * 100) : 0;
        return h(
          "div",
          { class: `poll__option${option.mine ? " poll__option--mine" : ""}` },
          h("span", { class: "poll__fill", style: { width: `${percent}%` } }),
          h("span", { class: "poll__label" }, option.option_name, option.mine && icon("check", { size: "sm" })),
          h("span", { class: "poll__percent" }, `${percent}%`),
        );
      }),
      h("div", { class: "poll__footer" }, h("span", null, `${total} 票`)),
    );
  };

  const vote = async (option) => {
    const before = options;
    options = options.map((o) => (o === option ? { ...o, count: o.count + 1, mine: true } : o));
    showResults();
    try {
      const result = await api("/api/vote", {
        method: "POST",
        body: { vote_option_id: option.vote_option_id, block_id: post.block_id },
      });
      if (result.data) options = result.data; // the server's counts, including others' votes
      if (result.error && !result.data) throw result;
      showResults();
    } catch (error) {
      options = before;
      showChoices();
      toastError(error, "投票失敗");
    }
  };

  const showChoices = () =>
    box.replaceChildren(
      ...options.map((option) =>
        h(
          "button",
          { class: "poll__option", type: "button", onClick: () => vote(option) },
          h("span", { class: "poll__label" }, option.option_name),
        ),
      ),
      h(
        "div",
        { class: "poll__footer" },
        h("span", null, "選一個投票"),
        h("button", { class: "btn btn--ghost btn--sm", type: "button", onClick: showResults }, "看結果"),
      ),
    );

  if (options.some((option) => option.mine)) showResults();
  else showChoices();
  return box;
}

// ---------- Comments ----------

function renderComments(post, score) {
  const list = h("ul", { class: "comments__list" });
  const more = h("button", { class: "btn btn--ghost btn--sm comments__more", type: "button", hidden: true });
  let total = 0;

  const setScore = (value) => {
    total = value;
    score.textContent = value > 0 ? `評分 +${value}` : `評分 ${value}`;
    score.dataset.sign = value > 0 ? "up" : value < 0 ? "down" : "";
    score.hidden = value === 0;
  };

  const comments = post.comments ?? [];
  list.append(...comments.map(renderComment));
  setScore(comments.reduce((sum, c) => sum + Number(c.given_score || 0), 0));
  const hiddenCount = comments.length - COLLAPSED_COMMENTS;
  if (hiddenCount > 0) {
    [...list.children].slice(0, hiddenCount).forEach((item) => (item.hidden = true));
    more.hidden = false;
    more.textContent = `查看較早的 ${hiddenCount} 則留言`;
  }
  more.addEventListener("click", () => {
    for (const item of list.children) item.hidden = false;
    more.hidden = true;
  });

  // Score each comment gives the post: −5 … +5.
  let rating = 0;
  const output = h("output", null, "0");
  const setRating = (value) => {
    rating = Math.max(-5, Math.min(5, value));
    output.textContent = rating > 0 ? `+${rating}` : String(rating);
    output.dataset.sign = rating > 0 ? "up" : rating < 0 ? "down" : "";
  };
  const stepper = h(
    "span",
    { class: "stepper", role: "group", "aria-label": "給這篇貼文評分" },
    h("span", { class: "stepper__label" }, "評分"),
    h(
      "button",
      { class: "icon-btn icon-btn--sm", type: "button", "aria-label": "降低評分", onClick: () => setRating(rating - 1) },
      icon("minus", { size: "sm" }),
    ),
    output,
    h(
      "button",
      { class: "icon-btn icon-btn--sm", type: "button", "aria-label": "提高評分", onClick: () => setRating(rating + 1) },
      icon("plus", { size: "sm" }),
    ),
  );

  const input = h("input", {
    class: "input",
    name: "message",
    placeholder: "留言…",
    maxlength: "500",
    autocomplete: "off",
    enterkeyhint: "send",
    "aria-label": "留言內容",
  });
  const send = h("button", { class: "btn btn--sm", type: "submit" }, "送出");
  const form = h("form", { class: "comment-form" }, input, stepper, send);
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const message = input.value.trim();
    if (!message) return input.focus();
    const given = rating;
    // Shown at once, confirmed (or taken back) when the server answers.
    const pending = renderComment({
      comment_id: null,
      member_id: me.id,
      account: me.account,
      content: message,
      build_time: null,
      nice_comment: 0,
      given_score: given,
      liked: false,
      level: me.level,
    });
    pending.classList.add("is-pending");
    list.append(pending);
    input.value = "";
    setRating(0);
    setScore(total + given);
    try {
      const result = await api("/api/message", {
        method: "POST",
        body: { block_id: post.block_id, message, score: given },
      });
      if (!result.ok) throw result;
      pending.replaceWith(renderComment(result.comment));
    } catch (error) {
      pending.remove();
      setScore(total - given);
      if (!input.value) input.value = message;
      setRating(given);
      toastError(error, "留言失敗");
    }
  });

  return h("section", { class: "comments", "aria-label": "留言" }, more, list, form);
}

function renderComment(comment) {
  const given = Number(comment.given_score || 0);
  const likes = h("span", null, comment.nice_comment ? String(comment.nice_comment) : "");
  const like = h(
    "button",
    {
      class: "comment__like",
      type: "button",
      "aria-pressed": String(Boolean(comment.liked)),
      "aria-label": "讚這則留言",
      disabled: comment.comment_id === null,
    },
    icon("like"),
    likes,
  );
  let latest = 0;
  like.addEventListener("click", async () => {
    // A second tap takes the like back.
    const liked = like.getAttribute("aria-pressed") !== "true";
    const before = Number(likes.textContent || 0);
    const count = Math.max(before + (liked ? 1 : -1), 0);
    like.setAttribute("aria-pressed", String(liked));
    likes.textContent = count ? String(count) : "";
    const request = ++latest;
    try {
      const { data } = await api(`/api/v1/comments/${comment.comment_id}/like`, { method: "PUT", body: { liked } });
      if (request !== latest) return;
      like.setAttribute("aria-pressed", String(data.liked));
      likes.textContent = data.likes ? String(data.likes) : "";
    } catch (error) {
      if (request !== latest) return;
      like.setAttribute("aria-pressed", String(!liked));
      likes.textContent = before ? String(before) : "";
      toastError(error);
    }
  });
  const mine = comment.member_id === me.id;
  const item = h(
    "li",
    { class: "comment", dataset: { author: comment.member_id } },
    h(
      "button",
      {
        class: "comment__avatar",
        type: "button",
        "aria-label": `查看 ${comment.account}`,
        onClick: () => emit("member:show", comment.member_id),
      },
      img(avatarUrl(comment.member_id), DEFAULT_AVATAR, {
        class: `avatar avatar--sm${frameClass(comment.level)}`,
        width: 32,
        height: 32,
      }),
    ),
    h(
      "div",
      { class: "comment__body" },
      h(
        "div",
        { class: "comment__head" },
        h("span", { class: "comment__name" }, comment.account),
        levelBadge(comment.level),
        given !== 0 &&
          h(
            "span",
            { class: "post__score", dataset: { sign: given > 0 ? "up" : "down" } },
            given > 0 ? `+${given}` : String(given),
          ),
        timeAgo(comment.build_time),
      ),
      h("p", { class: "comment__text" }, comment.content),
      like,
      !mine &&
        comment.comment_id !== null &&
        h(
          "button",
          {
            class: "comment__like comment__report",
            type: "button",
            "aria-label": "檢舉留言",
            title: "檢舉",
            onClick: () => report("comment", comment.comment_id, comment.account, comment.member_id, item),
          },
          icon("flag", { size: "sm" }),
        ),
    ),
  );
  return item;
}
