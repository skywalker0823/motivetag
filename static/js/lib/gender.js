// The gender a member chose to show next to their name (帳號設定 → 個人卡片).
import { h } from "./dom.js";
import { icon } from "./icons.js";

export const GENDERS = {
  male: "男",
  female: "女",
  nonbinary: "非二元",
};

/** A small coloured icon, or nothing when the member shows none (or is anonymous). */
export function genderIcon(gender) {
  if (!GENDERS[gender]) return null;
  return h(
    "span",
    { class: `gender gender--${gender}`, title: GENDERS[gender], role: "img", "aria-label": `性別：${GENDERS[gender]}` },
    icon(gender, { size: "sm" }),
  );
}
