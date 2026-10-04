// 會員 (GET /api/v1/admin/members): look someone up by account or e-mail, see their
// numbers, and change their level, confirm their e-mail, send them a notice, or
// suspend them.
import { api, errorMessage } from "../../lib/api.js";
import { confirmDialog } from "../../lib/confirm.js";
import { $, busy, h } from "../../lib/dom.js";
import { timeAgo } from "../../lib/time.js";
import { toast, toastError } from "../../lib/toast.js";
import { suspendDialog, untilText } from "./suspend.js";

const MAX_LEVEL = 50;
let lastQuery = "";

function fact(label, value) {
  return h("div", null, h("dt", null, label), h("dd", null, value));
}

function badge(text, kind = "") {
  return h("span", { class: `member-badge ${kind}` }, text);
}

/** A small dialog with one field; resolves the value, or null if cancelled. */
function ask({ title, label, input, confirmText, check }) {
  return new Promise((resolve) => {
    const error = h("p", { class: "field__hint field__hint--error", role: "alert" });
    let value = null;
    const form = h(
      "form",
      { novalidate: true },
      h("div", { class: "dialog__header" }, h("h2", { class: "dialog__title", id: "ask-title" }, title)),
      h("div", { class: "dialog__body" }, h("label", { class: "field__label" }, label, input), error),
      h(
        "div",
        { class: "dialog__footer" },
        h("button", { class: "btn btn--secondary", type: "button", onClick: () => dialog.close() }, "取消"),
        h("button", { class: "btn", type: "submit" }, confirmText),
      ),
    );
    const dialog = h("dialog", { class: "dialog", "aria-labelledby": "ask-title" }, form);
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      const problem = check(input.value);
      if (problem) {
        error.textContent = problem;
        return;
      }
      value = input.value.trim();
      dialog.close();
    });
    dialog.addEventListener("close", () => {
      resolve(value);
      dialog.remove();
    });
    document.body.append(dialog);
    dialog.showModal();
    input.focus();
  });
}

async function changeLevel(m) {
  const input = h("input", { class: "input", type: "number", min: "1", max: String(MAX_LEVEL), value: String(m.level), inputmode: "numeric" });
  const value = await ask({
    title: `調整 ${m.account} 的等級`,
    label: `等級（1–${MAX_LEVEL}，目前 Lv ${m.level}、${m.exp} exp）`,
    input,
    confirmText: "調整",
    check: (v) => (Number.isInteger(Number(v)) && v >= 1 && v <= MAX_LEVEL ? null : `請輸入 1–${MAX_LEVEL}`),
  });
  if (value === null) return false;
  await api(`/api/v1/admin/members/${encodeURIComponent(m.account)}/level`, { method: "PUT", body: { level: Number(value) } });
  toast(`${m.account} 現在是 Lv ${value}`, { type: "success" });
  return true;
}

async function sendNotice(m) {
  const input = h("textarea", { class: "input", rows: "3", maxlength: "300", placeholder: "對方會在通知鈴鐺看到，手機也會收到推播" });
  const value = await ask({
    title: `通知 ${m.account}`,
    label: "訊息",
    input,
    confirmText: "傳送",
    check: (v) => (v.trim() ? null : "請輸入訊息"),
  });
  if (value === null) return false;
  await api(`/api/v1/admin/members/${encodeURIComponent(m.account)}/notice`, { method: "POST", body: { message: value } });
  toast("已傳送通知", { type: "success" });
  return false;
}

async function verifyEmail(m) {
  const ok = await confirmDialog({ title: `把 ${m.account} 的 Email 設為已驗證？`, message: m.email, confirmText: "設為已驗證" });
  if (!ok) return false;
  await api(`/api/v1/admin/members/${encodeURIComponent(m.account)}/verify`, { method: "POST" });
  toast("已設為已驗證", { type: "success" });
  return true;
}

async function liftSuspension(m) {
  const ok = await confirmDialog({ title: `解除 ${m.account} 的停權？`, message: "對方可以馬上再登入。", confirmText: "解除" });
  if (!ok) return false;
  await api(`/api/v1/admin/members/${encodeURIComponent(m.account)}/suspension`, { method: "DELETE" });
  toast(`已解除 ${m.account} 的停權`, { type: "success" });
  return true;
}

function action(label, run, m, kind = "btn--secondary") {
  return h(
    "button",
    {
      class: `btn ${kind} btn--sm`,
      type: "button",
      onClick: (event) =>
        busy(event.currentTarget, async () => {
          try {
            if (await run(m)) loadMembers();
          } catch (error) {
            toastError(error, errorMessage(error, "操作失敗"));
          }
        }),
    },
    label,
  );
}

function memberCard(m) {
  return h(
    "article",
    { class: "card member-row" },
    h(
      "div",
      { class: "member-row__head" },
      h("strong", null, m.account),
      badge(`Lv ${m.level}`),
      m.online && badge("在線", "member-badge--online"),
      m.admin && badge("管理員"),
      m.demo && badge("示範"),
      !m.verified && badge("Email 未驗證", "member-badge--warn"),
      m.suspended && badge(`停權 ${untilText(m.suspended_until)}`, "member-badge--danger"),
    ),
    h(
      "dl",
      { class: "member-row__facts" },
      fact("Email", m.email),
      fact("加入", m.joined ?? "—"),
      fact("最後登入", m.last_signin ? timeAgo(m.last_signin) : "—"),
      fact("經驗", `${m.exp} exp・連續 ${m.streak} 天`),
      fact("貼文／留言", `${m.posts}／${m.comments}`),
      fact("好友", String(m.friends)),
      fact("被檢舉", `${m.reported} 次`),
    ),
    m.suspended_reason && h("p", { class: "admin-hint" }, `停權原因：${m.suspended_reason}`),
    h(
      "div",
      { class: "report-card__actions" },
      action("調整等級", changeLevel, m),
      action("傳通知", sendNotice, m),
      !m.verified && action("設為已驗證", verifyEmail, m),
      !m.admin && (m.suspended ? action("解除停權", liftSuspension, m) : action("停權", (x) => suspendDialog(x.account), m, "btn--danger")),
    ),
  );
}

export async function loadMembers() {
  const list = $("#members");
  try {
    const { data } = await api("/api/v1/admin/members", { query: { q: lastQuery } });
    list.replaceChildren(
      ...(data.length ? data.map(memberCard) : [h("p", { class: "card admin-hint" }, "找不到符合的會員")]),
    );
  } catch (error) {
    toastError(error, "載入失敗");
  }
}

export function initMembers() {
  const form = $("#member-search");
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    lastQuery = form.elements.q.value.trim();
    loadMembers();
  });
}
