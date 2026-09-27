// A guided tour: dims the page, highlights one element at a time and explains it.
// Framework-free like the rest of lib/; the page supplies the steps.
import { h } from "./dom.js";

const GAP = 12; // between the highlighted element and the card
const PAD = 6; // around the highlighted element

/**
 * Runs `steps` one after another. A step is
 * `{ target?: selector, title, text, before?: () => void }`: `before` can switch
 * the view so the target is visible; a step without a target (or whose target is
 * not on screen) shows the card in the middle.
 * Calls `onEnd(finished)` when the tour is completed (true) or skipped (false).
 */
export function startTour(steps, { onEnd } = {}) {
  let index = 0;
  let target = null;
  const returnFocus = document.activeElement;

  const spot = h("div", { class: "tour__spot", "aria-hidden": "true" });
  const count = h("span", { class: "tour__count" });
  const title = h("h2", { class: "tour__title", id: "tour-title" });
  const text = h("p", { class: "tour__text", id: "tour-text" });
  const back = h("button", { class: "btn btn--ghost btn--sm", type: "button", onClick: () => go(index - 1) }, "上一步");
  const next = h("button", { class: "btn btn--sm", type: "button", onClick: () => go(index + 1) });
  const skip = h("button", { class: "tour__skip", type: "button", onClick: () => end(false) }, "略過");
  const card = h(
    "div",
    {
      class: "tour__card",
      role: "dialog",
      "aria-modal": "true",
      "aria-labelledby": "tour-title",
      "aria-describedby": "tour-text",
      tabindex: "-1",
    },
    h("div", { class: "tour__head" }, count, skip),
    title,
    text,
    h("div", { class: "tour__actions" }, back, next),
  );
  const root = h("div", { class: "tour" }, spot, card);

  function visible(element) {
    if (!element) return false;
    const rect = element.getBoundingClientRect();
    return rect.width > 0 && rect.height > 0;
  }

  function place() {
    const view = { width: document.documentElement.clientWidth, height: window.innerHeight };
    const cardWidth = Math.min(340, view.width - 32);
    card.style.width = `${cardWidth}px`;
    if (!target) {
      root.classList.add("tour--center");
      card.style.left = `${(view.width - cardWidth) / 2}px`;
      card.style.top = `${Math.max(16, (view.height - card.offsetHeight) / 2)}px`;
      return;
    }
    root.classList.remove("tour--center");
    const rect = target.getBoundingClientRect();
    Object.assign(spot.style, {
      left: `${rect.left - PAD}px`,
      top: `${rect.top - PAD}px`,
      width: `${rect.width + PAD * 2}px`,
      height: `${rect.height + PAD * 2}px`,
    });
    // Below the element if it fits, else above, else over the bottom of the screen.
    const below = rect.bottom + PAD + GAP;
    const above = rect.top - PAD - GAP - card.offsetHeight;
    let top = below;
    if (below + card.offsetHeight > view.height - 16) top = above >= 16 ? above : view.height - card.offsetHeight - 16;
    const left = Math.min(Math.max(16, rect.left + rect.width / 2 - cardWidth / 2), view.width - cardWidth - 16);
    card.style.left = `${left}px`;
    card.style.top = `${Math.max(16, top)}px`;
  }

  function go(to) {
    if (to >= steps.length) return end(true);
    index = Math.max(0, to);
    const step = steps[index];
    step.before?.();
    const element = step.target ? document.querySelector(step.target) : null;
    target = visible(element) ? element : null;
    count.textContent = `${index + 1} / ${steps.length}`;
    title.textContent = step.title;
    text.textContent = step.text;
    back.hidden = index === 0;
    next.textContent = index === steps.length - 1 ? "開始使用" : "下一步";
    target?.scrollIntoView({ block: "center", behavior: "instant" });
    requestAnimationFrame(place);
    card.focus();
  }

  function onKey(event) {
    if (event.key === "Escape") return end(false);
    if (event.key === "ArrowRight") return go(index + 1);
    if (event.key === "ArrowLeft" && index > 0) return go(index - 1);
    if (event.key === "Tab") {
      // Keep keyboard focus inside the card while the tour is open.
      const buttons = [...card.querySelectorAll("button:not([hidden])")];
      const at = buttons.indexOf(document.activeElement);
      event.preventDefault();
      buttons[(at + (event.shiftKey ? buttons.length - 1 : 1)) % buttons.length].focus();
    }
  }

  function end(finished) {
    root.remove();
    document.removeEventListener("keydown", onKey, true);
    window.removeEventListener("resize", place);
    window.removeEventListener("scroll", place, true);
    returnFocus?.focus?.();
    onEnd?.(finished);
  }

  document.body.append(root);
  document.addEventListener("keydown", onKey, true);
  window.addEventListener("resize", place);
  window.addEventListener("scroll", place, true);
  go(0);
}
