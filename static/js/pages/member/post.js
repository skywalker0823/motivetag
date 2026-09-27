// One post in the feed: author, text with clickable #tags, image, poll, reactions and
// comments. `renderPost` returns the element and a loader for its comments, which the
// feed runs for all posts at once instead of one after another.
import { api } from "../../lib/api.js";
import { busy, h, img } from "../../lib/dom.js";
import { icon } from "../../lib/icons.js";
import { serverNow, timeAgo } from "../../lib/time.js";
import { toast, toastError } from "../../lib/toast.js";
import { ANON_AVATAR, avatarUrl, DEFAULT_AVATAR, emit, me } from "./state.js";

const VISIBILITY = {
  SECRET: ["私密", "pill pill--secret"],
  Anonymous: ["匿名", "pill pill--anon"],
};
const COLLAPSED_COMMENTS = 3;

export function renderPost(post) {
  const anonymous = post.content_type === "Anonymous";
  const mine = post.member_id === me.id;
  const [visibilityLabel, visibilityClass] = VISIBILITY[post.content_type] ?? [];
  const score = h("span", { class: "post__score", title: "留言評分總和", hidden: true });
  const comments = renderComments(post, score);

  const author = h(
    "button",
    {
      class: "post__author",
      type: "button",
      disabled: anonymous,
      onClick: () => emit("member:show", post.member_id),
    },
    anonymous
      ? img(ANON_AVATAR, ANON_AVATAR, { class: "avatar" })
      : img(avatarUrl(post.member_id), DEFAULT_AVATAR, { class: "avatar" }),
    h(
      "span",
      { style: { minWidth: "0" } },
      h("span", { class: "post__name" }, anonymous ? (mine ? "匿名（你）" : "匿名") : `@${post.account}`),
      h(
        "span",
        { class: "post__meta" },
        timeAgo(post.build_time),
        visibilityLabel && h("span", { class: visibilityClass }, visibilityLabel),
      ),
    ),
  );

  const article = h(
    "article",
    { class: "card post", dataset: { id: post.block_id } },
    h(
      "header",
      { class: "post__header" },
      author,
      score,
      mine &&
        h(
          "button",
          {
            class: "icon-btn icon-btn--sm",
            type: "button",
            "aria-label": "刪除貼文",
            title: "刪除貼文",
            onClick: (event) => deletePost(post, article, event.currentTarget),
          },
          icon("trash"),
        ),
    ),
    h("p", { class: "post__content" }, withHashtags(post.content)),
    post.block_img &&
      h("img", {
        class: "post__image",
        src: `/images/${post.block_img}`,
        alt: "貼文圖片",
        loading: "lazy",
        dataset: { role: "image" },
      }),
    post.votes?.length ? renderPoll(post) : null,
    renderActions(post),
    comments.section,
  );
  return { el: article, loadComments: comments.load };
}

/** Text with each #tag turned into a button that filters the feed by it. */
function withHashtags(text) {
  const parts = [];
  let last = 0;
  for (const match of text.matchAll(/#\S+/g)) {
    parts.push(text.slice(last, match.index));
    const name = match[0].slice(1).split("#")[0];
    parts.push(
      name
        ? h("button", { class: "hashtag", type: "button", onClick: () => emit("feed:tag", name) }, match[0])
        : match[0],
    );
    last = match.index + match[0].length;
  }
  parts.push(text.slice(last));
  return parts;
}

async function deletePost(post, article, button) {
  if (!confirm("確定要刪除這篇貼文嗎？刪除後無法復原。")) return;
  await busy(button, async () => {
    try {
      const result = await api("/api/blocks", { method: "DELETE", body: { block_id: post.block_id } });
      if (!result.ok) throw result;
      article.remove();
      toast("貼文已刪除");
    } catch (error) {
      toastError(error, "刪除失敗");
    }
  });
}

// ---------- Likes ----------

function renderActions(post) {
  const reaction = (kind, method, label, count) => {
    const counter = h("span", null, count || "");
    return h(
      "button",
      {
        class: "action",
        type: "button",
        "aria-label": label,
        title: label,
        "aria-pressed": "false",
        onClick: async (event) => {
          const button = event.currentTarget;
          if (button.getAttribute("aria-pressed") === "true") return;
          try {
            const result = await api("/api/blocks", { method, body: { block_id: post.block_id } });
            if (!result.ok) throw result;
            counter.textContent = String(Number(counter.textContent || 0) + 1);
            button.setAttribute("aria-pressed", "true");
          } catch (error) {
            if (String(error.error ?? "").includes("before")) button.setAttribute("aria-pressed", "true");
            toastError(error);
          }
        },
      },
      icon(kind),
      counter,
    );
  };
  return h(
    "footer",
    { class: "post__actions" },
    reaction("like", "PATCH", "讚", post.good),
    reaction("dislike", "PUT", "爛", post.bad),
  );
}

// ---------- Poll ----------

function renderPoll(post) {
  const box = h("div", { class: "poll", "aria-label": "投票" });
  const options = post.votes;

  const showResults = (votes) => {
    const total = votes.length;
    const mine = votes.find((vote) => vote.member_id === me.id)?.vote_option_id;
    box.replaceChildren(
      ...options.map((option) => {
        const count = votes.filter((vote) => vote.vote_option_id === option.vote_option_id).length;
        const percent = total ? Math.round((count / total) * 100) : 0;
        return h(
          "div",
          { class: `poll__option${option.vote_option_id === mine ? " poll__option--mine" : ""}` },
          h("span", { class: "poll__fill", style: { width: `${percent}%` } }),
          h("span", null, option.option_name, option.vote_option_id === mine ? "（你的選擇）" : ""),
          h("span", null, `${percent}%`),
        );
      }),
      h("div", { class: "poll__footer" }, h("span", null, `${total} 票`)),
    );
  };

  const loadResults = async () => {
    const result = await api("/api/vote", { query: { block_id: post.block_id } });
    showResults(result.data ?? []);
  };

  const vote = async (option, button) => {
    await busy(button, async () => {
      try {
        const result = await api("/api/vote", {
          method: "POST",
          body: { vote_option_id: option.vote_option_id, block_id: post.block_id },
        });
        if (result.error && !String(result.error).includes("voted before")) throw result;
        await loadResults();
      } catch (error) {
        toastError(error, "投票失敗");
      }
    });
  };

  const showChoices = () =>
    box.replaceChildren(
      ...options.map((option) =>
        h(
          "button",
          { class: "poll__option", type: "button", onClick: (event) => vote(option, event.currentTarget) },
          h("span", null, option.option_name),
        ),
      ),
      h(
        "div",
        { class: "poll__footer" },
        h("span", null, "選一個投票"),
        h("button", { class: "btn btn--ghost btn--sm", type: "button", onClick: loadResults }, "看結果"),
      ),
    );

  showChoices();
  // Members who already voted see the results straight away.
  api("/api/vote", { query: { block_id: post.block_id } })
    .then((result) => {
      const votes = result.data ?? [];
      if (votes.some((v) => v.member_id === me.id)) showResults(votes);
    })
    .catch(() => {});
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

  const collapse = () => {
    const items = [...list.children];
    const hiddenCount = items.length - COLLAPSED_COMMENTS;
    items.forEach((item, index) => (item.hidden = hiddenCount > 0 && index < hiddenCount));
    more.hidden = hiddenCount <= 0;
    more.textContent = `查看較早的 ${hiddenCount} 則留言`;
  };
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
    "aria-label": "留言內容",
  });
  const send = h("button", { class: "btn btn--sm", type: "submit" }, "送出");
  const form = h("form", { class: "comment-form" }, input, stepper, send);
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    const message = input.value.trim();
    if (!message) return input.focus();
    busy(send, async () => {
      try {
        const result = await api("/api/message", {
          method: "POST",
          body: { block_id: post.block_id, message, time: serverNow(), score: rating },
        });
        if (!result.ok) throw result;
        list.append(
          renderComment({
            comment_id: result.ok["LAST_INSERT_ID()"],
            member_id: result.member_id,
            account: result.account,
            content: message,
            build_time: null,
            nice_comment: 0,
            given_score: rating,
          }),
        );
        setScore(total + rating);
        input.value = "";
        setRating(0);
      } catch (error) {
        toastError(error, "留言失敗");
      }
    });
  });

  const section = h("section", { class: "comments", "aria-label": "留言" }, more, list, form);

  const load = async () => {
    try {
      const result = await api("/api/message", { query: { block_id: post.block_id } });
      const comments = result.ok || [];
      list.replaceChildren(...comments.map(renderComment));
      setScore(comments.reduce((sum, c) => sum + Number(c.given_score || 0), 0));
      collapse();
    } catch {
      // The post stays usable without its old comments.
    }
  };
  return { section, load };
}

function renderComment(comment) {
  const given = Number(comment.given_score || 0);
  const likes = h("span", null, comment.nice_comment ? String(comment.nice_comment) : "");
  const like = h(
    "button",
    {
      class: "comment__like",
      type: "button",
      "aria-pressed": "false",
      "aria-label": "讚這則留言",
      onClick: async () => {
        if (like.getAttribute("aria-pressed") === "true") return;
        try {
          const result = await api("/api/message", {
            method: "PATCH",
            body: { message_id: comment.comment_id },
          });
          if (!result.ok) throw result;
          likes.textContent = String(Number(likes.textContent || 0) + 1);
          like.setAttribute("aria-pressed", "true");
        } catch (error) {
          if (String(error.error ?? "").includes("before")) like.setAttribute("aria-pressed", "true");
          toastError(error);
        }
      },
    },
    icon("like"),
    likes,
  );
  return h(
    "li",
    { class: "comment" },
    h(
      "button",
      {
        class: "comment__avatar",
        type: "button",
        "aria-label": `查看 ${comment.account}`,
        onClick: () => emit("member:show", comment.member_id),
      },
      img(avatarUrl(comment.member_id), DEFAULT_AVATAR, { class: "avatar avatar--sm" }),
    ),
    h(
      "div",
      { class: "comment__body" },
      h(
        "div",
        { class: "comment__head" },
        h("span", { class: "comment__name" }, comment.account),
        given !== 0 &&
          h("span", { class: "post__score", dataset: { sign: given > 0 ? "up" : "down" } }, given > 0 ? `+${given}` : String(given)),
        comment.build_time ? timeAgo(comment.build_time) : h("time", null, "剛剛"),
      ),
      h("p", { class: "comment__text" }, comment.content),
      like,
    ),
  );
}

