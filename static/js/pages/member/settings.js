// Account settings. For now: deleting the account (App Store Guideline 5.1.1(v)).
import { api, errorMessage } from "../../lib/api.js";
import { $, busy } from "../../lib/dom.js";
import { socket } from "../../lib/socket.js";
import { me } from "./state.js";

export function initSettings() {
  const dialog = $("#settings-dialog");
  const form = $("#delete-account");
  const errorBox = form.querySelector("[data-error]");

  $("#settings-open").addEventListener("click", () => {
    form.reset();
    errorBox.textContent = "";
    dialog.showModal();
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
