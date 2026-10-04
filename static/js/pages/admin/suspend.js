// The 停權 dialog (api/v1/admin.py PUT /admin/members/<account>/suspension), shared by
// report cards, the 停權中 tab and the member list.
import { api, errorMessage } from "../../lib/api.js";
import { h } from "../../lib/dom.js";
import { toast } from "../../lib/toast.js";

const DURATIONS = [
  [1, "1 天"],
  [3, "3 天"],
  [7, "7 天"],
  [30, "30 天"],
  [null, "永久"],
];

export function untilText(until) {
  return until ? `至 ${until.slice(0, 16)}` : "永久";
}

/** Asks how long and why, then suspends `account`; resolves true when done. */
export function suspendDialog(account) {
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

