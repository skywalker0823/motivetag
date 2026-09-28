// My subscribed tags and the trending list.
import { api } from "../../lib/api.js";
import { $, busy, h } from "../../lib/dom.js";
import { setCardNote } from "../../lib/collapsible.js";
import { icon } from "../../lib/icons.js";
import { toast, toastError } from "../../lib/toast.js";
import { emit } from "./state.js";

const list = $("#my-tags");
const trend = $("#trend");
const subscribed = new Map(); // tag name -> member_tag_id
let hotTags = null; // the last trending list from /api/tag

const tagUrl = (name) => `/tag/${encodeURIComponent(name)}`;

function renderChips() {
  setCardNote("tags", subscribed.size ? `${subscribed.size} 個` : "");
  if (!subscribed.size) {
    list.replaceChildren(h("li", { class: "empty" }, "還沒有訂閱任何標籤"));
    return;
  }
  list.replaceChildren(
    ...[...subscribed].map(([name, id]) =>
      h(
        "li",
        { class: `chip${name === "Anonymous" ? " chip--anon" : ""}` },
        h("a", { href: tagUrl(name), title: `#${name} 的討論區` }, `#${name}`),
        h(
          "button",
          {
            class: "chip__remove",
            type: "button",
            "aria-label": `取消訂閱 #${name}`,
            onClick: () => unsubscribe(name, id),
          },
          icon("x", { size: "sm" }),
        ),
      ),
    ),
  );
}

export async function subscribe(name) {
  const result = await api("/api/member_tags", { method: "PATCH", body: { tag: name } });
  if (!result.ok) throw result;
  subscribed.set(name, result.member_tag_id);
  renderChips();
  loadTrend();
  emit("tags:changed");
  toast(`已訂閱 #${name}`, { type: "success" });
}

async function unsubscribe(name, id) {
  try {
    const result = await api("/api/member_tags", { method: "DELETE", body: { tag: id } });
    if (!result.ok) throw result;
    subscribed.delete(name);
    renderChips();
    loadTrend();
    emit("tags:changed");
  } catch (error) {
    toastError(error, "取消訂閱失敗");
  }
}

async function loadTrend() {
  try {
    const result = await api("/api/tag");
    hotTags = result.hot_tags ?? [];
    trend.replaceChildren(
      ...hotTags.map((tag) =>
        h(
          "li",
          null,
          h(
            "button",
            {
              class: `trend__name${tag.name === "Anonymous" ? " trend__name--anon" : ""}`,
              type: "button",
              title: `看 #${tag.name} 的貼文`,
              onClick: () => emit("feed:tag", tag.name),
            },
            `#${tag.name}`,
          ),
          h("span", { class: "trend__count", title: "訂閱與使用次數" }, tag.popularity),
          subscribed.has(tag.name)
            ? h("span", { class: "icon-btn icon-btn--sm", title: "已訂閱", style: { color: "var(--success)" } }, icon("check", { size: "sm" }))
            : h(
                "button",
                {
                  class: "icon-btn icon-btn--sm",
                  type: "button",
                  "aria-label": `訂閱 #${tag.name}`,
                  title: "訂閱",
                  onClick: (event) =>
                    busy(event.currentTarget, () => subscribe(tag.name).catch((e) => toastError(e))),
                },
                icon("plus", { size: "sm" }),
              ),
        ),
      ),
    );
  } catch {
    trend.replaceChildren(h("li", { class: "empty" }, "熱門標籤暫時無法載入"));
  }
}

/** Up to `count` trending tag names I have not subscribed to, for the empty feed. */
export async function suggestedTags(count = 6) {
  if (!hotTags) {
    try {
      hotTags = (await api("/api/tag")).hot_tags ?? [];
    } catch {
      return [];
    }
  }
  return hotTags
    .map((tag) => tag.name)
    .filter((name) => !subscribed.has(name) && name !== "Anonymous")
    .slice(0, count);
}

export async function initTags() {
  const form = $("#tag-add");
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    const name = form.elements.tag.value.trim().replace(/^#+/, "");
    if (!name) return form.elements.tag.focus();
    if (/\s/.test(name)) return toastError("標籤不能包含空白");
    busy(form.querySelector("[type=submit]"), async () => {
      try {
        await subscribe(name);
        form.reset();
      } catch (error) {
        toastError(error, "訂閱失敗");
      }
    });
  });

  try {
    const result = await api("/api/member_tags");
    for (const tag of result.tag ?? []) subscribed.set(tag.name, tag.member_tag_id);
  } catch (error) {
    toastError(error, "標籤載入失敗");
  }
  renderChips();
  loadTrend();
}
