// Pull-to-refresh for touch screens: drag down from the top of the page, let go
// past the line, and `onRefresh` runs while a spinner shows. The browser's own
// pull-to-reload is switched off in CSS (overscroll-behavior-y on the page).
import { h } from "./dom.js";
import { icon } from "./icons.js";

const THRESHOLD = 70; // px of (damped) pull that triggers a refresh
const MAX = 110;
// Touches that start here scroll or edit something else.
const IGNORE = "dialog, textarea, input, .chats, .tour, .popover";

/** `enabled()` is asked at the start of each pull; `onRefresh()` may return a promise. */
export function pullToRefresh({ onRefresh, enabled = () => true }) {
  const spinner = h("div", { class: "ptr", role: "status", "aria-label": "重新整理" }, icon("refresh"));
  document.body.append(spinner);
  let startY = null;
  let pull = 0;
  let running = false;

  function show(distance) {
    spinner.style.setProperty("--pull", `${distance}px`);
    spinner.style.setProperty("--turn", `${(distance / THRESHOLD) * 270}deg`);
    spinner.classList.toggle("is-ready", distance >= THRESHOLD);
    spinner.classList.toggle("is-pulling", distance > 0);
  }

  function reset() {
    startY = null;
    pull = 0;
    show(0);
  }

  window.addEventListener(
    "touchstart",
    (event) => {
      if (running || event.touches.length !== 1 || window.scrollY > 0) return;
      if (event.target.closest(IGNORE) || !enabled()) return;
      startY = event.touches[0].clientY;
    },
    { passive: true },
  );

  window.addEventListener(
    "touchmove",
    (event) => {
      if (startY === null) return;
      const dy = event.touches[0].clientY - startY;
      if (dy <= 0 || window.scrollY > 0) return reset();
      pull = Math.min(MAX, dy * 0.5); // resistance: the spinner moves half as far
      show(pull);
    },
    { passive: true },
  );

  async function release() {
    if (startY === null) return;
    const triggered = pull >= THRESHOLD;
    startY = null;
    if (!triggered) return show(0);
    running = true;
    spinner.classList.add("is-running");
    show(THRESHOLD);
    navigator.vibrate?.(10);
    try {
      await onRefresh();
    } finally {
      running = false;
      spinner.classList.remove("is-running");
      reset();
    }
  }

  window.addEventListener("touchend", release);
  window.addEventListener("touchcancel", reset);
}
