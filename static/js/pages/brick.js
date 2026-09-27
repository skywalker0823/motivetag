// One discussion topic and its replies (/tag/<name>/<id>).
import { api, errorMessage } from "../lib/api.js";
import { $, busy, h } from "../lib/dom.js";
import { hydrateIcons } from "../lib/icons.js";
import { serverNow, timeAgo } from "../lib/time.js";
import { toastError } from "../lib/toast.js";

hydrateIcons();

const [, , rawTag, topicId] = location.pathname.split("/");
const tag = decodeURIComponent(rawTag ?? "");
const topicBox = $("#topic");
const replies = $("#replies");

$("#back").href = `/tag/${encodeURIComponent(tag)}`;
$("#back").lastChild.textContent = `回到 #${tag}`;

async function loadTopic() {
  try {
    const result = await api("/api/bricks", { query: { brick_id: topicId } });
    const topic = result.data?.[0];
    if (!topic) {
      topicBox.replaceChildren(h("p", { class: "empty" }, "找不到這個討論，可能已經被刪除了"));
      $("#reply-form").hidden = true;
      return;
    }
    document.title = `${topic.title} - #${tag} - MotiveTag`;
    topicBox.replaceChildren(
      h("h1", { class: "topic__title" }, topic.title),
      h(
        "p",
        { class: "topic__meta" },
        h("span", { class: "pill" }, topic.classifi || "閒聊"),
        h("span", null, topic.account ?? "已刪除的帳號"),
        timeAgo(topic.time),
        h("span", null, `${topic.popularity ?? 0} 瀏覽`),
      ),
      h("p", { class: "topic__body" }, topic.content),
    );
  } catch (error) {
    topicBox.replaceChildren(h("p", { class: "empty" }, errorMessage(error, "討論載入失敗")));
  }
}

async function loadReplies() {
  try {
    const result = await api("/api/get_brick_discuss", { query: { brick_id: topicId } });
    const rows = [...(result.data ?? [])].reverse(); // oldest first, like a conversation
    replies.replaceChildren(
      ...(rows.length
        ? rows.map((row) =>
            h(
              "li",
              { class: "reply" },
              h("div", { class: "reply__head" }, h("strong", null, row.account ?? "已刪除的帳號"), timeAgo(row.time)),
              h("p", null, row.content),
            ),
          )
        : [h("li", { class: "empty" }, "還沒有回覆")]),
    );
  } catch (error) {
    toastError(error, "回覆載入失敗");
  }
}

const form = $("#reply-form");
form.addEventListener("submit", (event) => {
  event.preventDefault();
  const content = form.elements.content.value.trim();
  if (!content) return form.elements.content.focus();
  busy(form.querySelector("[type=submit]"), async () => {
    try {
      const result = await api("/api/bricks", {
        method: "POST",
        body: { brick_id: topicId, content, time: serverNow() },
      });
      if (!result.ok) throw result;
      form.reset();
      await loadReplies();
    } catch (error) {
      toastError(error, "回覆失敗");
    }
  });
});

loadTopic();
loadReplies();
