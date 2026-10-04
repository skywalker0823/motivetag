// Account settings: the site's look, my personal card, members I blocked, and
// deleting the account (App Store Guideline 5.1.1(v)).
import { api, errorMessage } from "../../lib/api.js";
import { $, busy, debounce, h, img } from "../../lib/dom.js";
import { socket } from "../../lib/socket.js";
import { toast, toastError } from "../../lib/toast.js";
import * as push from "../../lib/push.js";
import { uploadImage } from "../../lib/upload.js";
import { genderIcon } from "../../lib/gender.js";
import { applyCard } from "./card.js";
import { showMyName } from "./profile.js";
import { avatarUrl, bootstrap, DEFAULT_AVATAR, me } from "./state.js";

// ---------- Look (api/v1/profile.py UI_CHOICES; colours in static/css/base.css) ----------

const UI_KEY = "motivetag:ui";
const ACCENTS = [
  ["sky", "天藍", "#1cbfff"],
  ["violet", "紫", "#a78bfa"],
  ["green", "綠", "#2ee59d"],
  ["pink", "粉紅", "#ff6fb5"],
  ["orange", "橘", "#ff9f43"],
  ["gold", "金", "#ffc940"],
];
let ui = { mode: null, accent: null, text: null, ...(bootstrap.settings?.ui ?? {}) };

/** Puts `ui` on <html> and keeps a copy for the other pages (templates/_head.html). */
function applyUi() {
  const html = document.documentElement;
  for (const key of ["mode", "accent", "text"]) {
    if (ui[key]) html.dataset[key] = ui[key];
    else delete html.dataset[key];
  }
  try {
    localStorage.setItem(UI_KEY, JSON.stringify(ui));
  } catch {
    // Private mode: only this page follows.
  }
}

async function saveUi(change) {
  const before = { ...ui };
  ui = { ...ui, ...change };
  applyUi();
  try {
    await api("/api/v1/me/ui", { method: "PUT", body: change });
  } catch (error) {
    ui = before;
    applyUi();
    showUiChoices();
    toastError(error, "外觀儲存失敗");
  }
}

function showUiChoices() {
  for (const key of ["mode", "text"]) {
    const value = ui[key] ?? (key === "mode" ? "dark" : "normal");
    for (const input of document.querySelectorAll(`input[name="ui-${key}"]`)) input.checked = input.value === value;
  }
  for (const swatch of $("#ui-accent").children) {
    swatch.setAttribute("aria-checked", String(swatch.dataset.value === (ui.accent ?? "sky")));
  }
}

function initLook() {
  applyUi();
  $("#ui-accent").replaceChildren(
    ...ACCENTS.map(([value, label, color]) =>
      swatch(color, {
        role: "radio",
        title: label,
        "aria-label": label,
        dataset: { value },
        onClick: () => {
          saveUi({ accent: value });
          showUiChoices();
        },
      }),
    ),
  );
  for (const key of ["mode", "text"]) {
    for (const input of document.querySelectorAll(`input[name="ui-${key}"]`)) {
      input.addEventListener("change", () => saveUi({ [key]: input.value }));
    }
  }
  showUiChoices();
}

// ---------- Personal card ----------

const CARD_SLOTS = [
  ["accent", "卡片主色"],
  ["cover_from", "封面左色"],
  ["cover_to", "封面右色"],
  ["name_color", "名字顏色"],
];
const PRESETS = ["#1cbfff", "#a78bfa", "#2ee59d", "#ff6fb5", "#ff9f43", "#ffc940", "#ff5a78", "#ffffff", "#8e97bd", "#1c2444"];
let card = { ...(bootstrap.settings?.card ?? {}) };
const coverLevel = bootstrap.settings?.cover_level ?? 5;

function showPreviewName() {
  $("#card-preview-name").replaceChildren(me.account, " ", genderIcon(me.gender) ?? "");
}

function showGender() {
  for (const input of document.querySelectorAll('input[name="gender"]')) input.checked = input.value === (me.gender ?? "");
  showPreviewName();
  showMyName();
}

function showCard() {
  applyCard($("#card-preview"), card);
  applyCard($("#profile"), card);
  for (const row of $("#card-colors").children) {
    const value = card[row.dataset.slot];
    for (const swatch of row.querySelectorAll(".swatch")) {
      swatch.setAttribute("aria-pressed", String(swatch.dataset.color === value));
    }
    row.querySelector(".color-input").value = value ?? "#1cbfff";
  }
  const locked = (me.level ?? 1) < coverLevel;
  $("#cover-pick").setAttribute("aria-disabled", String(locked));
  $("#cover-input").disabled = locked;
  $("#cover-lock").hidden = !locked;
  $("#cover-lock").textContent = `Lv ${coverLevel} 解鎖（你現在 Lv ${me.level ?? 1}）`;
  $("#cover-remove").hidden = !card.cover;
}

let unsaved = {}; // colours changed since the last save, sent together
const saveCard = debounce(async () => {
  const change = unsaved;
  unsaved = {};
  try {
    const { data } = await api("/api/v1/me/card", { method: "PUT", body: change });
    card = { ...data, ...unsaved }; // keep what changed while this was on its way
  } catch (error) {
    toastError(error, "卡片儲存失敗");
  }
}, 300);

function setColor(slot, value) {
  card = { ...card, [slot]: value };
  unsaved[slot] = value;
  showCard();
  saveCard();
}

/** A round colour button; CSS custom properties need setProperty, not h()'s style. */
function swatch(color, props) {
  const el = h("button", { class: "swatch", type: "button", ...props });
  el.style.setProperty("--swatch", color);
  return el;
}

function initCard() {
  $("#card-preview-avatar").src = avatarUrl(me.id);
  $("#card-preview-avatar").addEventListener("error", (e) => (e.target.src = DEFAULT_AVATAR), { once: true });
  showPreviewName();
  for (const input of document.querySelectorAll('input[name="gender"]')) {
    input.addEventListener("change", async () => {
      const before = me.gender;
      me.gender = input.value || null;
      showGender();
      try {
        await api("/api/v1/me/gender", { method: "PUT", body: { gender: me.gender } });
      } catch (error) {
        me.gender = before;
        showGender();
        toastError(error, "性別圖示儲存失敗");
      }
    });
  }
  $("#card-colors").replaceChildren(
    ...CARD_SLOTS.map(([slot, label]) =>
      h(
        "div",
        { class: "settings__row", dataset: { slot } },
        h("span", { class: "settings__label" }, label),
        h(
          "div",
          { class: "swatches" },
          PRESETS.map((color) =>
            swatch(color, {
              title: color,
              "aria-label": `${label} ${color}`,
              dataset: { color },
              onClick: () => setColor(slot, color),
            }),
          ),
          h("input", {
            class: "color-input",
            type: "color",
            "aria-label": `${label}：自訂顏色`,
            onInput: (event) => setColor(slot, event.target.value),
          }),
          h("button", { class: "btn btn--ghost btn--sm", type: "button", onClick: () => setColor(slot, null) }, "預設"),
        ),
      ),
    ),
  );

  const input = $("#cover-input");
  input.addEventListener("change", async () => {
    const file = input.files[0];
    input.value = "";
    if (!file) return;
    const label = $("#cover-pick");
    label.setAttribute("aria-busy", "true");
    try {
      await uploadImage(file, "cover");
      card = (await api("/api/v1/me/profile")).data.card;
      showCard();
      toast("封面照片已更新", { type: "success" });
    } catch (error) {
      toastError(error, "封面上傳失敗");
    } finally {
      label.removeAttribute("aria-busy");
    }
  });
  $("#cover-remove").addEventListener("click", (event) =>
    busy(event.currentTarget, async () => {
      try {
        card = (await api("/api/v1/me/card/cover", { method: "DELETE" })).data;
        showCard();
      } catch (error) {
        toastError(error, "移除失敗");
      }
    }),
  );
  showCard();
}

async function loadBlocked() {
  const list = $("#blocked-members");
  let blocked = [];
  try {
    blocked = (await api("/api/v1/blocks")).data;
  } catch (error) {
    toastError(error, "封鎖名單載入失敗");
  }
  list.replaceChildren(
    ...(blocked.length
      ? blocked.map((member) =>
          h(
            "li",
            null,
            h(
              "span",
              { class: "person" },
              h("span", { class: "person__avatar" }, img(avatarUrl(member.member_id), DEFAULT_AVATAR, { class: "avatar avatar--sm" })),
              h("span", { class: "person__name" }, member.account),
            ),
            h(
              "button",
              {
                class: "btn btn--secondary btn--sm",
                type: "button",
                onClick: (event) =>
                  busy(event.currentTarget, async () => {
                    try {
                      await api(`/api/v1/blocks/${encodeURIComponent(member.account)}`, { method: "DELETE" });
                      toast(`已解除封鎖 ${member.account}`);
                      loadBlocked();
                    } catch (error) {
                      toastError(error, "解除封鎖失敗");
                    }
                  }),
              },
              "解除封鎖",
            ),
          ),
        )
      : [h("li", { class: "empty" }, "沒有封鎖任何人")]),
  );
}

// ---------- Phone notifications ----------

async function showPush() {
  const button = $("#push-toggle");
  const state = $("#push-state");
  if (push.needsHomeScreen()) {
    button.hidden = true;
    state.textContent = "iPhone 請先在 Safari 按「分享 → 加入主畫面」，再從主畫面打開 MotiveTag 開啟通知。";
    return;
  }
  if (!push.supported()) {
    button.hidden = true;
    state.textContent = "這個瀏覽器不支援通知。";
    return;
  }
  const on = await push.isOn();
  button.hidden = false;
  button.textContent = on ? "關閉通知" : "開啟通知";
  button.className = on ? "btn btn--secondary btn--sm" : "btn btn--sm";
  state.textContent = on ? "這台裝置已開啟通知" : Notification.permission === "denied" ? "通知被封鎖了，請到瀏覽器設定允許 motivetag.com 的通知" : "";
}

function initPush() {
  $("#push-toggle").addEventListener("click", (event) =>
    busy(event.currentTarget, async () => {
      try {
        if (await push.isOn()) {
          await push.turnOff();
          toast("已關閉這台裝置的通知");
        } else {
          await push.turnOn();
          toast("已開啟通知", { type: "success" });
        }
      } catch (error) {
        toastError(error, "通知設定失敗");
      }
      showPush();
    }),
  );
  // Registered on every visit: it is also what lets the site be installed as an app.
  push.registerWorker().then(() => push.refresh());
}

export function initSettings() {
  initPush();
  initLook();
  initCard();
  const dialog = $("#settings-dialog");
  const form = $("#delete-account");
  const errorBox = form.querySelector("[data-error]");

  $("#settings-open").addEventListener("click", () => {
    form.reset();
    errorBox.textContent = "";
    showUiChoices();
    showCard(); // the level may have changed since the page loaded
    showGender();
    showPush();
    dialog.showModal();
    loadBlocked();
  });
  dialog.addEventListener("click", (event) => event.target === dialog && dialog.close());

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    const password = form.elements.password.value;
    if (!password) {
      errorBox.textContent = "請輸入密碼";
      form.elements.password.focus();
      return;
    }
    busy(form.querySelector("[type=submit]"), async () => {
      try {
        await api("/api/v1/account", { method: "DELETE", body: { password } });
        socket.emit("logout", { account: me.account });
        location.assign("/?deleted=1");
      } catch (error) {
        errorBox.textContent = errorMessage(error, "刪除失敗，請稍後再試");
        form.elements.password.select();
      }
    });
  });
}
