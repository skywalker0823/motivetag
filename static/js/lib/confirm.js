// A styled replacement for window.confirm(): resolves true when the member confirms.
import { h } from "./dom.js";

export function confirmDialog({ title, message = "", confirmText = "確定", danger = false }) {
  return new Promise((resolve) => {
    const confirmButton = h(
      "button",
      { class: `btn${danger ? " btn--danger" : ""}`, type: "submit", value: "yes" },
      confirmText,
    );
    const dialog = h(
      "dialog",
      { class: "dialog dialog--confirm", "aria-labelledby": "confirm-title" },
      h(
        "form",
        { method: "dialog" },
        h("div", { class: "dialog__header" }, h("h2", { class: "dialog__title", id: "confirm-title" }, title)),
        message && h("div", { class: "dialog__body" }, h("p", { class: "dialog__message" }, message)),
        h(
          "div",
          { class: "dialog__footer" },
          h("button", { class: "btn btn--secondary", type: "submit", value: "no" }, "取消"),
          confirmButton,
        ),
      ),
    );
    dialog.addEventListener("close", () => {
      resolve(dialog.returnValue === "yes");
      dialog.remove();
    });
    dialog.addEventListener("click", (event) => event.target === dialog && dialog.close("no"));
    document.body.append(dialog);
    dialog.showModal();
    // Destructive actions start on "取消", so Enter does not delete by accident.
    (danger ? dialog.querySelector('[value="no"]') : confirmButton).focus();
  });
}
