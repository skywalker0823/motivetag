// My profile card (avatar, level, mood) and the dialog that shows another member.
import { api, errorMessage } from "../../lib/api.js";
import { $, h } from "../../lib/dom.js";
import { icon } from "../../lib/icons.js";
import { dateOnly, fromServer, relative } from "../../lib/time.js";
import { toast, toastError } from "../../lib/toast.js";
import { uploadImage } from "../../lib/upload.js";
import { avatarUrl, DEFAULT_AVATAR, emit, me } from "./state.js";

/** Level from experience points: Lv n needs 50·n(n−1)/2 exp. */
export function levelOf(exp) {
  const raw = ((((8 * Math.max(exp, 0)) / 50 + 1) ** 0.5 + 1) / 2);
  const level = Math.floor(raw);
  return { level, progress: raw - level, next: (50 * (level + 1) * level) / 2 };
}

export function initProfile(data) {
  $("#my-account").textContent = data.account;
  $("#my-email").textContent = data.email;
  $("#my-joined").textContent = `${dateOnly(data.first_signup)} 加入`;

  const avatar = $("#my-avatar");
  avatar.src = avatarUrl(data.member_id);
  avatar.addEventListener("error", () => (avatar.src = DEFAULT_AVATAR), { once: true });

  const { level, progress, next } = levelOf(data.exp ?? 0);
  $("#my-level").textContent = `Lv ${level}`;
  $("#my-exp").textContent = `${data.exp ?? 0} / ${next} exp`;
  $("#my-level-fill").style.width = `${Math.round(progress * 100)}%`;
  $("#my-level-bar").setAttribute("aria-valuenow", String(Math.round(progress * 100)));

  initAvatarUpload(avatar);
  initMood(data.mood ?? "");
}

function initAvatarUpload(avatar) {
  const input = $("#avatar-input");
  input.addEventListener("change", async () => {
    const file = input.files[0];
    input.value = "";
    if (!file) return;
    try {
      await uploadImage(file, "avatar", null);
      avatar.src = `${avatarUrl(me.id)}?t=${Date.now()}`; // skip the cached old avatar
      toast("大頭貼已更新", { type: "success" });
    } catch (error) {
      toastError(error, "圖片上傳失敗");
    }
  });
}

function initMood(initial) {
  const text = $("#mood-text");
  const input = $("#mood-input");
  let saved = initial;
  text.textContent = saved;

  const edit = () => {
    text.hidden = true;
    input.hidden = false;
    input.value = saved;
    input.focus();
  };
  const close = () => {
    text.hidden = false;
    input.hidden = true;
  };
  const save = async () => {
    const value = input.value.trim();
    close();
    if (!value || value === saved) return;
    text.textContent = value;
    try {
      const result = await api("/api/member", {
        method: "PATCH",
        body: { category: "mood", content: value },
      });
      if (result.error) throw result;
      saved = value;
    } catch (error) {
      text.textContent = saved;
      toastError(error, "心情更新失敗");
    }
  };

  text.addEventListener("click", edit);
  input.addEventListener("blur", save);
  input.addEventListener("keydown", (event) => {
    if (event.key === "Enter") input.blur();
    if (event.key === "Escape") {
      input.value = saved;
      input.blur();
    }
  });
}

// ---------- Another member's card ----------

const dialog = $("#member-dialog");

export async function showMember(memberId) {
  const avatar = $("#member-dialog-avatar");
  avatar.src = avatarUrl(memberId);
  avatar.onerror = () => {
    avatar.onerror = null;
    avatar.src = DEFAULT_AVATAR;
  };
  $("#member-dialog-name").textContent = "載入中…";
  $("#member-dialog-mood").textContent = "";
  $("#member-dialog-facts").replaceChildren();
  $("#member-dialog-tags").hidden = true;
  $("#member-dialog-actions").replaceChildren();
  dialog.showModal();

  let result;
  try {
    result = await api("/api/get_user_sp", { query: { member_id: memberId } });
  } catch (error) {
    $("#member-dialog-name").textContent = errorMessage(error);
    return;
  }
  const user = result.data;
  if (!user) {
    $("#member-dialog-name").textContent = "找不到這位成員";
    return;
  }
  $("#member-dialog-name").textContent = user.account;
  $("#member-dialog-mood").textContent = user.mood || "";
  const { level } = levelOf(user.exp ?? 0);
  const facts = [
    ["等級", `Lv ${level}（${user.exp ?? 0} exp）`],
    ["加入", dateOnly(user.first_signup)],
    ["上次上線", user.last_signin ? relative(fromServer(user.last_signin)) : "—"],
    ["年齡", user.age != null ? `${user.age} 歲` : "—"],
  ];
  $("#member-dialog-facts").replaceChildren(
    ...facts.flatMap(([term, value]) => [h("dt", null, term), h("dd", null, value)]),
  );
  const shared = result.shared_tags ?? [];
  const tags = $("#member-dialog-tags");
  tags.hidden = user.account === me.account || shared.length === 0;
  tags.replaceChildren(
    h("span", { class: "member-card__tags-label" }, "共同標籤"),
    ...shared.map((name) =>
      h(
        "button",
        {
          class: "chip chip--add",
          type: "button",
          title: `看 #${name} 的貼文`,
          onClick: () => {
            dialog.close();
            emit("feed:tag", name);
          },
        },
        `#${name}`,
      ),
    ),
  );
  $("#member-dialog-actions").replaceChildren(...friendActions(user.account, result.is_friend));
}

function friendActions(account, friendship) {
  if (account === me.account) return [];
  const chat = h(
    "button",
    {
      class: "btn btn--secondary",
      type: "button",
      onClick: () => {
        dialog.close();
        emit("chat:open", account);
      },
    },
    icon("comment"),
    "聊天",
  );
  if (!friendship) {
    return [
      h(
        "button",
        {
          class: "btn",
          type: "button",
          onClick: (event) => {
            event.currentTarget.disabled = true;
            event.currentTarget.textContent = "已送出邀請";
            emit("friend:invite", account);
          },
        },
        icon("user-plus"),
        "加好友",
      ),
    ];
  }
  if (String(friendship.status) === "0") return [chat];
  if (friendship.request_from === me.id) {
    return [h("button", { class: "btn btn--secondary", type: "button", disabled: true }, "已送出邀請")];
  }
  return [
    h(
      "button",
      {
        class: "btn",
        type: "button",
        onClick: () => {
          dialog.close();
          emit("friend:accept", { id: friendship.friend_ship_id, account });
        },
      },
      icon("check"),
      "接受邀請",
    ),
  ];
}

// Clicking the backdrop closes the dialog.
dialog.addEventListener("click", (event) => {
  if (event.target === dialog) dialog.close();
});

