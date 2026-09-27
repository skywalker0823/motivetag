// Shows an image full size over the page; click, Esc or the button closes it.
import { h } from "./dom.js";
import { icon } from "./icons.js";

export function openLightbox(src, alt = "") {
  const dialog = h(
    "dialog",
    { class: "lightbox", "aria-label": alt || "圖片" },
    h("img", { src, alt }),
    h(
      "button",
      { class: "icon-btn lightbox__close", type: "button", "aria-label": "關閉", onClick: () => dialog.close() },
      icon("x"),
    ),
  );
  dialog.addEventListener("click", (event) => event.target.tagName !== "BUTTON" && dialog.close());
  dialog.addEventListener("close", () => dialog.remove());
  document.body.append(dialog);
  dialog.showModal();
}
