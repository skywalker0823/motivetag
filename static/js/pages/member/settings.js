// Account settings: members I blocked, and deleting the account (App Store
// Guideline 5.1.1(v)).
import { api, errorMessage } from "../../lib/api.js";
import { $, busy, h, img } from "../../lib/dom.js";
import { socket } from "../../lib/socket.js";
import { toast, toastError } from "../../lib/toast.js";
import { avatarUrl, DEFAULT_AVATAR, me } from "./state.js";

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

export function initSettings() {
  const dialog = $("#settings-dialog");
  const form = $("#delete-account");
  const errorBox = form.querySelector("[data-error]");

  $("#settings-open").addEventListener("click", () => {
    form.reset();
    errorBox.textContent = "";
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
