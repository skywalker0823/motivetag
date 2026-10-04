// 公告 (POST /api/v1/admin/announcements): one bell notification for every member.
import { api } from "../../lib/api.js";
import { confirmDialog } from "../../lib/confirm.js";
import { $, busy } from "../../lib/dom.js";
import { toast, toastError } from "../../lib/toast.js";

export function initAnnounce() {
  const form = $("#announce-form");
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const message = form.elements.message.value.trim();
    if (!message) return;
    const ok = await confirmDialog({ title: "發布這則公告？", message, confirmText: "發布" });
    if (!ok) return;
    await busy(form.querySelector('[type="submit"]'), async () => {
      try {
        const { data } = await api("/api/v1/admin/announcements", { method: "POST", body: { message } });
        toast(`已通知 ${data.sent} 位會員`, { type: "success" });
        form.reset();
      } catch (error) {
        toastError(error, "發布失敗");
      }
    });
  });
}
