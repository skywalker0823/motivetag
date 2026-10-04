// Reviewing reports (/admin, api/v1/admin.py): one card per reported thing.
import { api } from "../lib/api.js";
import { confirmDialog } from "../lib/confirm.js";
import { $, busy, h } from "../lib/dom.js";
import { hydrateIcons } from "../lib/icons.js";
import { timeAgo } from "../lib/time.js";
import { toast, toastError } from "../lib/toast.js";

hydrateIcons();

const KINDS = { post: "貼文", comment: "留言", message: "聊天訊息", member: "帳號" };
const list = $("#reports");
let status = "open";

function card(item) {
  const who = item.author.account ?? "（已刪除的帳號）";
  const actions =
    status === "open"
      ? h(
          "div",
          { class: "report-card__actions" },
          item.type !== "member" &&
            item.exists &&
            h(
              "button",
              { class: "btn btn--danger btn--sm", type: "button", onClick: (e) => decide(e.currentTarget, item, "remove") },
              "刪除內容",
            ),
          h(
            "button",
            { class: "btn btn--secondary btn--sm", type: "button", onClick: (e) => decide(e.currentTarget, item, "dismiss") },
            item.hidden ? "保留並重新顯示" : "保留（結案）",
          ),
        )
      : null;
  return h(
    "article",
    { class: "card report-card" },
    h(
      "div",
      { class: "report-card__head" },
      h("span", { class: "report-card__kind" }, KINDS[item.type] ?? item.type),
      h("span", null, `作者：${who}`),
      h("span", null, `${item.reports.length} 則檢舉（權重 ${item.weight}）`),
      item.hidden && h("span", { class: "report-card__flag" }, "已自動隱藏"),
      !item.exists && h("span", { class: "report-card__flag" }, "內容已不存在"),
    ),
    item.snapshot && h("p", { class: "report-card__snapshot" }, item.snapshot),
    item.image && h("p", { class: "admin-hint" }, "（貼文附有圖片）"),
    item.photo &&
      h("a", { href: item.photo, target: "_blank", rel: "noopener" }, h("img", { class: "report-card__photo", src: item.photo, alt: "被檢舉的聊天圖片", loading: "lazy" })),
    h(
      "ul",
      { class: "report-card__reports" },
      item.reports.map((r) =>
        h("li", null, `${r.reason_text} · ${r.reporter} · `, timeAgo(r.created_at), r.detail ? `：「${r.detail}」` : ""),
      ),
    ),
    actions,
  );
}

async function decide(button, item, action) {
  if (action === "remove") {
    const ok = await confirmDialog({
      title: `刪除這則${KINDS[item.type]}？`,
      message: "會永久刪除，無法復原。",
      confirmText: "刪除",
      danger: true,
    });
    if (!ok) return;
  }
  await busy(button, async () => {
    try {
      await api(`/api/v1/admin/reports/${item.type}/${item.id}`, { method: "POST", body: { action } });
      toast(action === "remove" ? "已刪除" : "已結案", { type: "success" });
      load();
    } catch (error) {
      toastError(error, "處理失敗");
    }
  });
}

async function load() {
  try {
    const result = await api("/api/v1/admin/reports", { query: { status } });
    list.replaceChildren(
      ...(result.data.length ? result.data.map(card) : [h("p", { class: "card admin-hint" }, "沒有檢舉 🎉")]),
    );
    document.title = `檢舉審核（${result.open}） - MotiveTag`;
  } catch (error) {
    toastError(error, "載入失敗");
  }
}

for (const tab of document.querySelectorAll("#status-tabs [data-status]")) {
  tab.addEventListener("click", () => {
    status = tab.dataset.status;
    for (const other of document.querySelectorAll("#status-tabs [data-status]")) {
      other.setAttribute("aria-pressed", String(other === tab));
    }
    load();
  });
}

load();
