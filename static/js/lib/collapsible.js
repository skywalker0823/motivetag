// Cards that fold down to their title bar. Each card with data-collapse-key gets a
// disclosure button in its title; the choice is remembered in this browser. A folded
// card still shows what needs attention: a badge (a count that wants action, such as
// friend requests) and a short note (such as "3 位上線").
import { h } from "./dom.js";
import { icon } from "./icons.js";

const storageKey = (key) => `motivetag:collapsed:${key}`;

function remembered(key) {
  try {
    return localStorage.getItem(storageKey(key)) === "1";
  } catch {
    return false;
  }
}

function remember(key, collapsed) {
  try {
    if (collapsed) localStorage.setItem(storageKey(key), "1");
    else localStorage.removeItem(storageKey(key));
  } catch {
    // Private mode: the card simply opens again next time.
  }
}

function setCollapsed(card, button, collapsed) {
  card.classList.toggle("is-collapsed", collapsed);
  button.setAttribute("aria-expanded", String(!collapsed));
}

/** Turns every `.card[data-collapse-key]` under `root` into a collapsible card. */
export function initCollapsibles(root = document) {
  for (const card of root.querySelectorAll(".card[data-collapse-key]")) {
    const key = card.dataset.collapseKey;
    const title = card.querySelector(":scope > .card__title");
    // Everything below the title moves into a body the button controls.
    const body = h("div", { class: "card__body", id: `card-body-${key}` });
    body.append(...[...card.children].filter((child) => child !== title));
    card.append(body);

    const button = h(
      "button",
      { class: "card__toggle", type: "button", "aria-controls": body.id },
      ...title.childNodes,
      h("span", { class: "card__note", "data-card-note": "" }),
      h("span", { class: "card__badge", "data-card-badge": "", hidden: true }),
      icon("chevron-down", { size: "sm" }),
    );
    title.replaceChildren(button);
    setCollapsed(card, button, remembered(key));
    button.addEventListener("click", () => {
      const collapsed = !card.classList.contains("is-collapsed");
      setCollapsed(card, button, collapsed);
      remember(key, collapsed);
    });
  }
}

function card(key) {
  return document.querySelector(`.card[data-collapse-key="${key}"]`);
}

/** A red count in the card's title (0 or less hides it), seen even when folded. */
export function setCardBadge(key, count, label = "") {
  const badge = card(key)?.querySelector("[data-card-badge]");
  if (!badge) return;
  badge.hidden = !(count > 0);
  badge.textContent = count > 99 ? "99+" : String(count);
  badge.setAttribute("aria-label", label || `${count} 則待處理`);
}

/** Short muted text next to the title, e.g. "3 位上線"; empty hides it. */
export function setCardNote(key, text, { live = false } = {}) {
  const note = card(key)?.querySelector("[data-card-note]");
  if (!note) return;
  note.textContent = text || "";
  note.classList.toggle("card__note--live", live);
}

/** Opens a card without remembering it (the tour points at things inside cards). */
export function expandCard(key) {
  const found = card(key);
  if (!found) return;
  found.classList.remove("is-collapsed");
  found.querySelector(".card__toggle")?.setAttribute("aria-expanded", "true");
}
