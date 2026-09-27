// A tiny hyperscript helper so views are built as trees, much like JSX:
//   h("button", { class: "btn", onClick: save }, "儲存")
// Text children become text nodes, never HTML, so user content cannot inject markup.

export function h(tag, props, ...children) {
  const el = document.createElement(tag);
  for (const [key, value] of Object.entries(props ?? {})) {
    if (value === undefined || value === null || value === false) continue;
    if (key === "class") el.className = value;
    else if (key === "dataset") Object.assign(el.dataset, value);
    else if (key === "style") Object.assign(el.style, value);
    else if (key.startsWith("on") && typeof value === "function") {
      el.addEventListener(key.slice(2).toLowerCase(), value);
    } else if (key in el && typeof value !== "string") el[key] = value;
    else el.setAttribute(key, value === true ? "" : value);
  }
  append(el, children);
  return el;
}

function append(el, children) {
  for (const child of children) {
    if (child === null || child === undefined || child === false) continue;
    if (Array.isArray(child)) append(el, child);
    else el.append(child instanceof Node ? child : String(child));
  }
}

export const $ = (selector, root = document) => root.querySelector(selector);

/** Disable a button and show its spinner while `task` runs. */
export async function busy(button, task) {
  if (button.getAttribute("aria-busy") === "true") return undefined;
  button.setAttribute("aria-busy", "true");
  button.disabled = true;
  try {
    return await task();
  } finally {
    button.removeAttribute("aria-busy");
    button.disabled = false;
  }
}

/** An <img> that falls back to `fallback` when the image is missing. */
export function img(src, fallback, props = {}) {
  const el = h("img", { src, alt: "", loading: "lazy", decoding: "async", ...props });
  el.addEventListener("error", () => el.src !== fallback && (el.src = fallback), { once: true });
  return el;
}

export function debounce(fn, ms) {
  let timer;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), ms);
  };
}
