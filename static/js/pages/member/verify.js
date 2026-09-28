// The "please confirm your e-mail" banner, and the messages after clicking the link.
import { api, errorMessage } from "../../lib/api.js";
import { $ } from "../../lib/dom.js";
import { toast, toastError } from "../../lib/toast.js";

const RESEND_WAIT = 60; // seconds; the server enforces the same (RESEND_AFTER)
const banner = $("#verify-banner");
const resend = $("#verify-resend");

function countdown(seconds) {
  resend.disabled = true;
  const tick = () => {
    if (seconds <= 0) {
      resend.disabled = false;
      resend.textContent = "重寄";
      return;
    }
    resend.textContent = `${seconds} 秒後可重寄`;
    seconds -= 1;
    setTimeout(tick, 1000);
  };
  tick();
}

/** `me` is the signed-in member from the page (email, email_verified). */
export function initVerify(me) {
  const params = new URLSearchParams(location.search);
  if (params.has("verified") || params.has("verify")) {
    history.replaceState(null, "", location.pathname);
    if (params.has("verified")) toast("Email 驗證完成！", { type: "success" });
    else toastError("驗證連結無效或已過期，請按「重寄」拿新的連結");
  }
  if (me.email_verified !== false) return;

  banner.hidden = false;
  $("#verify-email").textContent = me.email;
  resend.addEventListener("click", async () => {
    resend.disabled = true;
    try {
      await api("/api/v1/email/verification", { method: "POST" });
      toast("已重寄驗證信，請到信箱查看（也看看垃圾信匣）", { type: "success" });
      countdown(RESEND_WAIT);
    } catch (error) {
      if (error.data?.error?.code === "already_verified") {
        banner.hidden = true;
        return toast("你的 Email 已經驗證過了", { type: "success" });
      }
      toastError(error, errorMessage(error, "寄信失敗，請稍後再試"));
      resend.disabled = false;
    }
  });
}
