// Short status messages at the bottom of the screen, announced to screen readers.
import { errorMessage } from "./api.js";
import { h } from "./dom.js";
import { icon } from "./icons.js";

const ICONS = { success: "check", error: "x", info: "bell" };
let region;

/** `action` ({ label, onClick }) adds a button, for example "回覆" on a chat message. */
export function toast(message, { type = "info", timeout = 3500, action } = {}) {
  if (!region) {
    region = h("div", { class: "toasts", role: "status", "aria-live": "polite" });
    document.body.append(region);
  }
  const close = () => {
    el.classList.add("toast--leaving");
    setTimeout(() => el.remove(), 200);
  };
  const el = h(
    "div",
    { class: `toast toast--${type}` },
    h("span", { class: "toast__icon" }, icon(ICONS[type] ?? "bell", { size: "sm" })),
    h("span", { class: "toast__text" }, message),
    action &&
      h(
        "button",
        {
          class: "btn btn--ghost btn--sm toast__action",
          type: "button",
          onClick: () => {
            close();
            action.onClick();
          },
        },
        action.label,
      ),
    h("button", { class: "toast__close", type: "button", "aria-label": "關閉訊息", onClick: close }, icon("x", { size: "sm" })),
  );
  region.append(el);
  while (region.children.length > 3) region.firstChild.remove();
  setTimeout(close, timeout);
}

export const toastError = (error, fallback) =>
  toast(errorMessage(error, fallback), { type: "error", timeout: 5000 });
