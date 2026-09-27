// Who is signed in, and a small event bus so the panels can talk to each other
// without reaching into each other's DOM (the shape a React context would take).

export const me = { id: null, account: null };

const bus = new EventTarget();

export function emit(name, detail) {
  bus.dispatchEvent(new CustomEvent(name, { detail }));
}

export function on(name, handler) {
  bus.addEventListener(name, (event) => handler(event.detail));
}

/** On phones, switch the visible panel (feed, tags, friends or me). */
export function showView(view) {
  document.body.dataset.view = view;
  for (const tab of document.querySelectorAll(".tabbar [data-tab]")) {
    if (tab.dataset.tab === view) tab.setAttribute("aria-current", "page");
    else tab.removeAttribute("aria-current");
  }
  window.scrollTo({ top: 0 });
}

export const avatarUrl = (memberId) => `/images/avatar_${memberId}`;
export const DEFAULT_AVATAR = "/img/user-regular-24.png";
export const ANON_AVATAR = "/img/ghost-regular-24.png";
