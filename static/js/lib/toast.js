// Short status messages at the bottom of the screen, announced to screen readers.
import { h } from "./dom.js";
import { errorMessage } from "./api.js";

let region;

export function toast(message, { type = "info", timeout = 3500 } = {}) {
  if (!region) {
    region = h("div", { class: "toasts", role: "status", "aria-live": "polite" });
    document.body.append(region);
  }
  const el = h("div", { class: `toast toast--${type}` }, message);
  region.append(el);
  setTimeout(() => el.remove(), timeout);
}

export const toastError = (error, fallback) =>
  toast(errorMessage(error, fallback), { type: "error", timeout: 5000 });
