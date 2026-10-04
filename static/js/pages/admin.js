// Reviewing reports and suspending accounts (/admin, api/v1/admin.py): one card per
// reported thing; the 停權中 tab lists suspended accounts.
import { api, errorMessage } from "../lib/api.js";
import { confirmDialog } from "../lib/confirm.js";
import { $, busy, h } from "../lib/dom.js";
import { hydrateIcons } from "../lib/icons.js";
import { timeAgo } from "../lib/time.js";
import { toast, toastError } from "../lib/toast.js";

hydrateIcons();

const KINDS = { post: "貼文", comment: "留言", message: "聊天訊息", member: "帳號" };
const list = $("#reports");
let status = "open";

const DURATIONS = [
  [1, "1 天"],
  [3, "3 天"],
  [7, "7 天"],
  [30, "30 天"],
  [null, "永久"],
];

function untilText(until) {
  return until ? `至 ${until.slice(0, 16)}` : "永久";
}

/** Asks how long and why, then suspends `account`; resolves true when done. */
function suspendDialog(account) {
  return new Promise((resolve) => {
    const error = h("p", { class: "field__hint field__hint--error", role: "alert" });
    const reason = h("textarea", { class: "input", name: "reason", rows: "2", maxlength: "200", placeholder: "原因（對方登入時會看到）" });
    const send = h("button", { class: "btn btn--danger", type: "submit" }, "停權");
    let done = false;
    const form = h(
      "form",
      { novalidate: true },
      h("div", { class: "dialog__header" }, h("h2", { class: "dialog__title", id: "suspend-title" }, `停權 ${account}`)),
      h(
        "div",
        { class: "dialog__body" },
        h("p", { class: "dialog__message" }, "對方會立刻被登出，期間無法登入。貼文和留言不會刪除，需要的話請另外刪除。"),
        h(
          "fieldset",
          { class: "suspend__durations" },
          h("legend", { class: "field__label" }, "期間"),
          DURATIONS.map(([days, label]) =>
            h("label", null, h("input", { type: "radio", name: "days", value: days ?? "forever", checked: days === 7 }), label),
          ),
        ),
        reason,
        error,
      ),
      h(
        "div",
        { class: "dialog__footer" },
        h("button", { class: "btn btn--secondary", type: "button", onClick: () => dialog.close() }, "取消"),
        send,
      ),
    );
    const dialog = h("dialog", { class: "dialog", "aria-labelledby": "suspend-title" }, form);
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const picked = form.elements.days.value;
      send.disabled = true;
      try {
        await api(`/api/v1/admin/members/${encodeURIComponent(account)}/suspension`, {
          method: "PUT",
          body: { days: picked === "forever" ? null : Number(picked), reason: reason.value.trim() },
        });
      } catch (failure) {
        error.textContent = errorMessage(failure, "停權失敗");
        send.disabled = false;
        return;
      }
      toast(`已停權 ${account}`, { type: "success" });
      done = true;
      dialog.close();
    });
    dialog.addEventListener("close", () => {
      resolve(done);
      dialog.remove();
    });
    dialog.addEventListener("click", (event) => event.target === dialog && dialog.close());
    document.body.append(dialog);
    dialog.showModal();
  });
}

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
