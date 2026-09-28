// "邀請朋友": share my personal invite link (the system share sheet on phones,
// otherwise copied). Whoever signs up through it becomes my friend.
import { api } from "../../lib/api.js";
import { $ } from "../../lib/dom.js";
import { toast, toastError } from "../../lib/toast.js";

const TEXT = "我在 MotiveTag 用 #標籤 找興趣相同的朋友，一起來吧！";
let link = null;

async function myLink() {
  link ??= (await api("/api/v1/invites/mine")).url;
  return link;
}

async function share() {
  let url;
  try {
    url = await myLink();
  } catch (error) {
    return toastError(error, "邀請連結暫時無法取得");
  }
  if (navigator.share) {
    try {
      await navigator.share({ title: "MotiveTag", text: TEXT, url });
      return;
    } catch (error) {
      if (error.name === "AbortError") return; // closed the share sheet
    }
  }
  try {
    await navigator.clipboard.writeText(`${TEXT} ${url}`);
    toast("已複製邀請連結，貼給朋友就好", { type: "success" });
  } catch {
    window.prompt("複製這個邀請連結：", url); // no clipboard access (old browser, http)
  }
}

export function initInvite() {
  $("#invite-share").addEventListener("click", share);
}
