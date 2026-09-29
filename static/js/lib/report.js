// "檢舉" dialog for posts, comments, chat messages and members (api/v1/reports.py).
// Resolves { reported, blocked } once the member has sent it, or null if they cancel.
import { api, errorMessage } from "./api.js";
import { confirmDialog } from "./confirm.js";
import { h } from "./dom.js";
import { toast } from "./toast.js";

const REASONS = [
  ["spam", "垃圾訊息或廣告"],
  ["harassment", "騷擾或霸凌"],
  ["sexual", "色情或性騷擾"],
  ["violence", "暴力或威脅"],
  ["hate", "仇恨言論"],
  ["scam", "詐騙"],
  ["other", "其他"],
];
const WHAT = { post: "貼文", comment: "留言", message: "訊息", member: "帳號" };

/**
 * type: post | comment | message | member; id: its id; account: the author, when the
 * member may also block them (never for anonymous posts).
 */
export function reportDialog({ type, id, account }) {
  return new Promise((resolve) => {
    const error = h("p", { class: "field__hint field__hint--error", role: "alert" });
    const detail = h("textarea", { class: "input", name: "detail", rows: "3", maxlength: "500", placeholder: "補充說明（選填）" });
    const alsoBlock =
      account &&
      type !== "member" &&
      h("label", { class: "report__block" }, h("input", { type: "checkbox", name: "block" }), `同時封鎖 ${account}`);
    const send = h("button", { class: "btn btn--danger", type: "submit" }, "送出檢舉");
    let result = null;
    const form = h(
      "form",
      { class: "report", novalidate: true },
      h("div", { class: "dialog__header" }, h("h2", { class: "dialog__title", id: "report-title" }, `檢舉這則${WHAT[type]}`)),
      h(
        "div",
        { class: "dialog__body" },
        h("p", { class: "dialog__message" }, "你檢舉的內容會立刻從你的畫面消失，我們會在 24 小時內處理。"),
        h(
          "fieldset",
          { class: "report__reasons" },
          h("legend", { class: "field__label" }, "原因"),
          REASONS.map(([value, label]) => h("label", null, h("input", { type: "radio", name: "reason", value, required: true }), label)),
        ),
        detail,
        alsoBlock,
        error,
      ),
      h(
        "div",
        { class: "dialog__footer" },
        h("button", { class: "btn btn--secondary", type: "button", onClick: () => dialog.close() }, "取消"),
        send,
      ),
    );
    const dialog = h("dialog", { class: "dialog", "aria-labelledby": "report-title" }, form);

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const reason = form.elements.reason.value;
      if (!reason) {
        error.textContent = "請選擇原因";
        return;
      }
      send.disabled = true;
      try {
        await api("/api/v1/reports", { method: "POST", body: { type, id, reason, detail: detail.value.trim() || undefined } });
      } catch (failure) {
        // Already reported: it still leaves my view, so treat it as done.
        if (failure.data?.error?.code !== "already_reported") {
          error.textContent = errorMessage(failure, "檢舉失敗，請稍後再試");
          send.disabled = false;
          return;
        }
      }
      let blocked = false;
      if (alsoBlock?.querySelector("input").checked) {
        try {
          await api(`/api/v1/blocks/${encodeURIComponent(account)}`, { method: "PUT" });
          blocked = true;
        } catch {
          // The report went through; blocking can be retried from their card.
        }
      }
      toast(blocked ? `已檢舉並封鎖 ${account}` : "已收到檢舉，謝謝你", { type: "success" });
      result = { reported: true, blocked };
      dialog.close();
    });
    dialog.addEventListener("close", () => {
      resolve(result);
      dialog.remove();
    });
    dialog.addEventListener("click", (event) => event.target === dialog && dialog.close());
    document.body.append(dialog);
    dialog.showModal();
  });
}

/** Asks, then blocks `account`; resolves true when blocked. */
export async function blockMember(account) {
  const ok = await confirmDialog({
    title: `封鎖 ${account}？`,
    message: "你們的好友關係會解除，你不會再看到對方的貼文和留言，雙方也無法再傳訊息或送出好友邀請。對方不會收到通知。之後可以在「帳號設定」解除封鎖。",
    confirmText: "封鎖",
    danger: true,
  });
  if (!ok) return false;
  try {
    await api(`/api/v1/blocks/${encodeURIComponent(account)}`, { method: "PUT" });
  } catch (error) {
    toast(errorMessage(error, "封鎖失敗"), { type: "error" });
    return false;
  }
  toast(`已封鎖 ${account}`, { type: "success" });
  return true;
}
