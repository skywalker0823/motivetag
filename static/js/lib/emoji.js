// An emoji picker for any text field: emojiButton(field) returns a 😀 button that opens
// a small panel and inserts the chosen emoji at the cursor. No library and nothing
// downloaded: the emoji are text, drawn by the phone's or computer's own font.
import { h } from "./dom.js";
import { icon } from "./icons.js";

const RECENT_KEY = "motivetag:emoji-recent";
const RECENT_MAX = 16;

const GROUPS = [
  ["表情", "😀 😃 😄 😁 😆 😅 🤣 😂 🙂 😉 😊 😇 🥰 😍 🤩 😘 😋 😜 🤪 😝 🤗 🤭 🤔 🤐 😐 😑 😶 😏 😒 🙄 😬 😌 😔 😪 😴 😷 🤒 🤧 🥵 🥶 🥴 😵 🤯 🥳 😎 🤓 😕 😟 🙁 😮 😲 😳 🥺 😦 😨 😰 😥 😢 😭 😱 😖 😣 😞 😓 😩 😫 🥱 😤 😡 😠 🤬 😈 💀 💩 🤡 👻 👽 🤖"],
  ["手勢", "👍 👎 👌 ✌️ 🤞 🤟 🤘 🤙 👈 👉 👆 👇 ☝️ ✋ 🤚 🖐️ 🖖 👋 👏 🙌 👐 🤲 🤝 🙏 ✍️ 💪 🫶 🫡 🙇 🤷 🤦 🙋 🙆 🙅"],
  ["愛心", "❤️ 🧡 💛 💚 💙 💜 🖤 🤍 🤎 💔 ❣️ 💕 💞 💓 💗 💖 💘 💝 💯 ✨ 🌟 ⭐ 🔥 💥 💫 💤 💬 🎉 🎊 🎁 🏆 🥇"],
  ["動物", "🐶 🐱 🐭 🐹 🐰 🦊 🐻 🐼 🐨 🐯 🦁 🐮 🐷 🐸 🐵 🐔 🐧 🐦 🐤 🦆 🦉 🐺 🐴 🦄 🐝 🦋 🐌 🐢 🐍 🐙 🐬 🐳 🐟 🌸 🌹 🌻 🌷 🌱 🌳 🍀 🍁"],
  ["食物", "🍎 🍊 🍋 🍌 🍉 🍇 🍓 🍒 🍑 🥭 🍍 🥑 🍅 🌽 🥕 🍞 🧀 🍳 🍔 🍟 🍕 🌭 🌮 🍜 🍝 🍣 🍱 🍛 🍙 🥟 🍤 🍦 🍰 🎂 🍩 🍪 🍫 🍿 ☕ 🧋 🍵 🍺 🍻 🥂 🍷"],
  ["活動", "⚽ 🏀 🏈 ⚾ 🎾 🏐 🏓 🏸 🥊 🏋️ 🚴 🏊 🧘 🎮 🎲 🎯 🎳 🎸 🎹 🎤 🎧 🎬 📷 🎨 📚 ✏️ 💻 📱 ✈️ 🚗 🚲 🏖️ ⛰️ 🏕️ 🌈 ☀️ 🌙 ☔ ❄️ ⛄"],
].map(([name, list]) => [name, list.split(" ")]);

function recent() {
  try {
    return JSON.parse(localStorage.getItem(RECENT_KEY) || "[]").slice(0, RECENT_MAX);
  } catch {
    return [];
  }
}

function remember(emoji) {
  try {
    const list = [emoji, ...recent().filter((e) => e !== emoji)].slice(0, RECENT_MAX);
    localStorage.setItem(RECENT_KEY, JSON.stringify(list));
  } catch {
    // Private mode: no recent row, nothing else changes.
  }
}

/** Puts `text` where the cursor is (replacing a selection) and tells listeners. */
function insert(field, text) {
  const start = field.selectionStart ?? field.value.length;
  const end = field.selectionEnd ?? field.value.length;
  const max = Number(field.getAttribute("maxlength")) || Infinity;
  if (field.value.length - (end - start) + text.length > max) return;
  field.setRangeText(text, start, end, "end");
  field.dispatchEvent(new Event("input", { bubbles: true })); // counters, autosize, typing
}

let open = null; // the panel on screen, if any

function close() {
  if (!open) return;
  open.panel.remove();
  open.button.setAttribute("aria-expanded", "false");
  open = null;
}

document.addEventListener("click", (event) => {
  // composedPath() still holds a tab the click just re-rendered away.
  const path = event.composedPath();
  if (open && !path.includes(open.panel) && !path.includes(open.button)) close();
});
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && open) {
    const { button } = open;
    close();
    button.focus();
  }
});

function panelFor(field, button) {
  let tab = recent().length ? "最近" : GROUPS[0][0];
  const grid = h("div", { class: "emoji-panel__grid", role: "listbox", "aria-label": "表情符號" });
  const tabs = h("div", { class: "emoji-panel__tabs", role: "tablist" });
  const panel = h("div", { class: "emoji-panel", role: "dialog", "aria-label": "選擇表情符號" }, tabs, grid);

  const groups = () => (recent().length ? [["最近", recent()], ...GROUPS] : GROUPS);
  const render = () => {
    tabs.replaceChildren(
      ...groups().map(([name, list]) =>
        h(
          "button",
          {
            type: "button",
            role: "tab",
            "aria-selected": String(name === tab),
            title: name,
            onClick: () => {
              tab = name;
              render();
            },
          },
          list[0],
        ),
      ),
    );
    const list = groups().find(([name]) => name === tab)?.[1] ?? GROUPS[0][1];
    grid.replaceChildren(
      ...list.map((emoji) =>
        h(
          "button",
          {
            type: "button",
            role: "option",
            "aria-label": emoji,
            onClick: () => {
              insert(field, emoji);
              remember(emoji);
              // Phones would pop the keyboard up over the panel; computers keep typing.
              if (!matchMedia("(pointer: coarse)").matches) field.focus();
            },
          },
          emoji,
        ),
      ),
    );
  };
  render();
  return panel;
}

/** A 😀 button for `field` (an <input> or <textarea>). */
export function emojiButton(field, { size } = {}) {
  const button = h(
    "button",
    {
      class: `icon-btn${size === "sm" ? " icon-btn--sm" : ""} emoji-button`,
      type: "button",
      "aria-label": "插入表情符號",
      title: "表情符號",
      "aria-expanded": "false",
    },
    icon("smile", size === "sm" ? { size: "sm" } : {}),
  );
  button.addEventListener("click", () => {
    const wasOpen = open?.button === button;
    close();
    if (wasOpen) return;
    const panel = panelFor(field, button);
    document.body.append(panel);
    place(panel, button);
    button.setAttribute("aria-expanded", "true");
    open = { panel, button };
  });
  return button;
}

/** Next to the button on computers (above it if there is no room below); a sheet at the bottom on phones. */
function place(panel, button) {
  if (matchMedia("(max-width: 599px)").matches) {
    panel.classList.add("emoji-panel--sheet");
    return;
  }
  const rect = button.getBoundingClientRect();
  const width = panel.offsetWidth;
  const height = panel.offsetHeight;
  const left = Math.min(Math.max(8, rect.right - width), innerWidth - width - 8);
  const below = rect.bottom + 6 + height < innerHeight;
  panel.style.left = `${left}px`;
  panel.style.top = `${below ? rect.bottom + 6 : Math.max(8, rect.top - height - 6)}px`;
}
