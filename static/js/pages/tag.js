// A tag's discussion board: its topics, subscribing, and starting a new topic.
import { api, errorMessage } from "../lib/api.js";
import { $, busy, h } from "../lib/dom.js";
import { hydrateIcons, icon } from "../lib/icons.js";
import { serverNow, timeAgo } from "../lib/time.js";
import { toast, toastError } from "../lib/toast.js";

hydrateIcons();

const tag = decodeURIComponent(location.pathname.split("/")[2] ?? "");
const topics = $("#topics");
const subscribeButton = $("#subscribe");
let memberTagId = null;

document.title = `#${tag} - MotiveTag`;
$("#tag-title").textContent = `#${tag}`;

function topicUrl(id) {
  return `/tag/${encodeURIComponent(tag)}/${id}`;
}

async function loadTopics() {
  try {
    const result = await api("/api/tag_page", { query: { keyword: tag } });
    const rows = result.data ?? [];
    if (!rows.length) {
      topics.replaceChildren(h("p", { class: "empty" }, `#${tag} 還沒有討論，來發起第一個吧！`));
      return;
    }
    topics.replaceChildren(
      h(
        "ol",
        { class: "topic-list" },
        ...rows.map((row) =>
          h(
            "li",
            null,
            h(
              "a",
              {
                class: "topic-row",
                href: topicUrl(row.brick_id),
                // Counts the visit; keepalive lets it finish while the page changes.
                onClick: () =>
                  fetch("/api/tag_page", {
                    method: "PATCH",
                    keepalive: true,
                    headers: { "content-type": "application/json" },
                    body: JSON.stringify({ brick_id: row.brick_id }),
                  }).catch(() => {}),
              },
              h("span", { class: "pill" }, row.classifi || "閒聊"),
              h(
                "span",
                { style: { minWidth: "0" } },
                h("span", { class: "topic-row__title", style: { display: "block" } }, row.title),
                h("span", { class: "topic-row__meta" }, `${row.account ?? "已刪除的帳號"} · `, timeAgo(row.time)),
              ),
              h(
                "span",
                { class: "topic-row__stats" },
                h("span", null, `${row.feedbacks ?? 0} 回覆`),
                h("span", null, `${row.popularity ?? 0} 瀏覽`),
              ),
            ),
          ),
        ),
      ),
    );
  } catch (error) {
    topics.replaceChildren(h("p", { class: "empty" }, errorMessage(error, "討論載入失敗")));
  }
}

// ---------- Subscribe ----------

function showSubscribed() {
  subscribeButton.replaceChildren(icon(memberTagId ? "check" : "plus"), memberTagId ? "已訂閱" : "訂閱");
  subscribeButton.setAttribute("aria-pressed", String(Boolean(memberTagId)));
  subscribeButton.title = memberTagId ? "再按一次取消訂閱" : `訂閱後 #${tag} 的貼文會出現在你的動態`;
}

async function loadSubscription() {
  try {
    const result = await api("/api/member_tags");
    memberTagId = (result.tag ?? []).find((t) => t.name === tag)?.member_tag_id ?? null;
  } catch {
    // Unknown: keep the button in its default state.
  }
  showSubscribed();
}

subscribeButton.addEventListener("click", () =>
  busy(subscribeButton, async () => {
    try {
      if (memberTagId) {
        const result = await api("/api/member_tags", { method: "DELETE", body: { tag: memberTagId } });
        if (!result.ok) throw result;
        memberTagId = null;
        toast(`已取消訂閱 #${tag}`);
      } else {
        const result = await api("/api/member_tags", { method: "PATCH", body: { tag } });
        if (!result.ok) throw result;
        memberTagId = result.member_tag_id;
        toast(`已訂閱 #${tag}`, { type: "success" });
      }
    } catch (error) {
      toastError(error);
    }
    showSubscribed();
  }),
);

// ---------- New topic ----------

const dialog = $("#topic-dialog");
const form = $("#topic-form");

$("#new-topic").addEventListener("click", () => {
  form.reset();
  form.querySelector("[data-error]").textContent = "";
  dialog.showModal();
});
for (const button of dialog.querySelectorAll("[data-close]")) {
  button.addEventListener("click", () => dialog.close());
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  const title = form.elements.title.value.trim();
  const content = form.elements.content.value.trim();
  const error = form.querySelector("[data-error]");
  if (!title || !content) {
    error.textContent = "請填寫標題和內容";
    return;
  }
  busy(form.querySelector("[type=submit]"), async () => {
    try {
      // A topic needs the tag to exist; subscribing creates it if it is new.
      if (!memberTagId) {
        const sub = await api("/api/member_tags", { method: "PATCH", body: { tag } });
        if (sub.ok) memberTagId = sub.member_tag_id;
        showSubscribed();
      }
      const result = await api("/api/tag_page", {
        method: "POST",
        body: { title, content, classifi: form.elements.category.value, tag_name: tag, time: serverNow() },
      });
      if (!result.ok) throw result;
      dialog.close();
      toast("討論已發佈", { type: "success" });
      loadTopics();
    } catch (submitError) {
      error.textContent = errorMessage(submitError, "發佈失敗，請稍後再試");
    }
  });
});

loadTopics();
loadSubscription();
