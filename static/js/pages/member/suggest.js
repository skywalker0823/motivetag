// "可能合得來的人": members who subscribe to the same tags, one tap from an invitation.
import { api } from "../../lib/api.js";
import { $, busy, h, img } from "../../lib/dom.js";
import { setCardNote } from "../../lib/collapsible.js";
import { icon } from "../../lib/icons.js";
import { toastError } from "../../lib/toast.js";
import { avatarUrl, DEFAULT_AVATAR, emit, on } from "./state.js";

const SHOW_TAGS = 3;
const list = $("#suggested");

function sharedText(tags) {
  const shown = tags.slice(0, SHOW_TAGS).map((t) => `#${t}`).join(" ");
  return tags.length > SHOW_TAGS ? `${shown} +${tags.length - SHOW_TAGS}` : shown;
}

function row(person, invite) {
  const add = h(
    "button",
    {
      class: "btn btn--sm",
      type: "button",
      onClick: (event) =>
        busy(event.currentTarget, async () => {
          try {
            await invite(person.account);
            add.replaceWith(h("span", { class: "person__status" }, "已邀請"));
          } catch (error) {
            toastError(error, "邀請失敗");
          }
        }),
    },
    icon("user-plus", { size: "sm" }),
    "加好友",
  );
  return h(
    "li",
    null,
    h(
      "button",
      { class: "person person--stacked", type: "button", onClick: () => emit("member:show", person.member_id) },
      h("span", { class: "person__avatar" }, img(avatarUrl(person.member_id), DEFAULT_AVATAR, { class: "avatar avatar--sm" })),
      h(
        "span",
        { class: "person__text" },
        h("span", { class: "person__name" }, person.account),
        h("span", { class: "person__shared", title: person.shared.map((t) => `#${t}`).join(" ") }, `共同：${sharedText(person.shared)}`),
      ),
    ),
    add,
  );
}

async function load(invite) {
  try {
    const result = await api("/api/v1/members/suggested");
    const people = result.data ?? [];
    setCardNote("suggested", people.length ? `${people.length} 人` : "");
    list.replaceChildren(
      ...(people.length
        ? people.map((person) => row(person, invite))
        : [h("li", { class: "empty" }, "多訂閱幾個標籤，就會在這裡看到興趣相同的人")]),
    );
  } catch {
    list.replaceChildren(h("li", { class: "empty" }, "推薦暫時無法載入"));
  }
}

/** `invite(account)` sends a friend request (from friends.js) and throws on failure. */
export function initSuggestions(invite) {
  load(invite);
  // New tags mean new people in common.
  on("tags:changed", () => load(invite));
}
