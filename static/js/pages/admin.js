// The /admin page (api/v1/admin.py): sections 總覽, 檢舉, 會員, 公告 and 紀錄. This file
// holds the reports (one card per reported thing; the 停權中 tab lists suspended
// accounts) and switches sections; the others live in ./admin/.
import { api } from "../lib/api.js";
import { confirmDialog } from "../lib/confirm.js";
import { $, busy, h } from "../lib/dom.js";
import { hydrateIcons } from "../lib/icons.js";
import { timeAgo } from "../lib/time.js";
import { toast, toastError } from "../lib/toast.js";
import { initAnnounce } from "./admin/announce.js";
import { loadLogs } from "./admin/logs.js";
import { initMembers, loadMembers } from "./admin/members.js";
import { loadStats } from "./admin/stats.js";
import { suspendDialog, untilText } from "./admin/suspend.js";

hydrateIcons();

const KINDS = { post: "貼文", comment: "留言", message: "聊天訊息", member: "帳號" };
const list = $("#reports");
let status = "open";

function suspendButton(account) {
  return h(
    "button",
    {
      class: "btn btn--secondary btn--sm",
      type: "button",
      onClick: async () => {
        if (await suspendDialog(account)) load();
      },
    },
    "停權帳號",
  );
}

function card(item) {
  const who = item.author.account ?? "（已刪除的帳號）";
  const canSuspend = item.author.account && !item.author.admin && !item.author.suspended;
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
          canSuspend && suspendButton(item.author.account),
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
      item.author.suspended && h("span", { class: "report-card__flag" }, `已停權（${untilText(item.author.suspended_until)}）`),
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

function suspensionRow(row) {
  return h(
    "article",
    { class: "card suspension-row" },
    h(
      "div",
      null,
      h("strong", null, row.account),
      h("p", { class: "admin-hint" }, untilText(row.until), row.reason ? ` · ${row.reason}` : ""),
    ),
    h(
      "button",
      {
        class: "btn btn--secondary btn--sm",
        type: "button",
        onClick: async (e) => {
          const ok = await confirmDialog({ title: `解除 ${row.account} 的停權？`, message: "對方可以馬上再登入。", confirmText: "解除" });
          if (!ok) return;
          await busy(e.currentTarget, async () => {
            try {
              await api(`/api/v1/admin/members/${encodeURIComponent(row.account)}/suspension`, { method: "DELETE" });
              toast(`已解除 ${row.account} 的停權`, { type: "success" });
              load();
            } catch (error) {
              toastError(error, "解除失敗");
            }
          });
        },
      },
      "解除停權",
    ),
  );
}

/** Suspending someone without a report: type the account name. */
function suspendForm() {
  const input = h("input", { class: "input", name: "account", placeholder: "帳號名稱", autocomplete: "off", required: true });
  return h(
    "form",
    {
      class: "card suspend-form",
      onSubmit: async (event) => {
        event.preventDefault();
        const account = input.value.trim();
        if (account && (await suspendDialog(account))) load();
      },
    },
    input,
    h("button", { class: "btn btn--danger btn--sm", type: "submit" }, "停權帳號"),
  );
}

async function loadSuspensions() {
  const result = await api("/api/v1/admin/suspensions");
  list.replaceChildren(
    suspendForm(),
    ...(result.data.length ? result.data.map(suspensionRow) : [h("p", { class: "card admin-hint" }, "沒有停權中的帳號")]),
  );
}

async function load() {
  if (status === "suspended") {
    try {
      await loadSuspensions();
    } catch (error) {
      toastError(error, "載入失敗");
    }
    return;
  }
  try {
    const result = await api("/api/v1/admin/reports", { query: { status } });
    list.replaceChildren(
      ...(result.data.length ? result.data.map(card) : [h("p", { class: "card admin-hint" }, "沒有檢舉 🎉")]),
    );
    $("#reports-count").textContent = result.open ? String(result.open) : "";
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

// ---------- Sections ----------

const SECTIONS = {
  overview: () => loadStats($("#overview")),
  reports: load,
  members: loadMembers,
  announce: () => {},
  logs: () => loadLogs($("#logs")),
};

function showSection(name) {
  if (!(name in SECTIONS)) name = "overview";
  for (const tab of document.querySelectorAll("#admin-nav [data-section]")) {
    tab.setAttribute("aria-current", String(tab.dataset.section === name));
  }
  for (const section of document.querySelectorAll(".admin-section[data-section]")) {
    section.hidden = section.dataset.section !== name;
  }
  SECTIONS[name]();
}

for (const tab of document.querySelectorAll("#admin-nav [data-section]")) {
  tab.addEventListener("click", () => {
    history.replaceState(null, "", `#${tab.dataset.section}`);
    showSection(tab.dataset.section);
  });
}

initMembers();
initAnnounce();
showSection(location.hash.slice(1));
// The open-report count on the 檢舉 tab, whichever section opens first.
api("/api/v1/admin/reports")
  .then((result) => ($("#reports-count").textContent = result.open ? String(result.open) : ""))
  .catch(() => {});
