// My profile card (avatar, level, mood) and the dialog that shows another member.
import { api, errorMessage } from "../../lib/api.js";
import { $, h } from "../../lib/dom.js";
import { icon } from "../../lib/icons.js";
import { frameClass, levelBadge, levelOf } from "../../lib/levels.js";
import { blockMember, reportDialog } from "../../lib/report.js";
import { applyCard } from "./card.js";
import { socket } from "../../lib/socket.js";
import { dateOnly, fromServer, relative } from "../../lib/time.js";
import { toast, toastError } from "../../lib/toast.js";
import { uploadImage } from "../../lib/upload.js";
import { avatarUrl, bootstrap, DEFAULT_AVATAR, emit, me } from "./state.js";

const PERKS = bootstrap.levels?.perks ?? []; // [[level, what it unlocks], …]

/** The level card: level, exp towards the next one and what the next levels unlock. */
function showLevel(exp) {
  const { level, progress, next } = levelOf(exp);
  me.level = level;
  $("#my-level").replaceChildren(levelBadge(level));
  $("#my-exp").textContent = `${exp} / ${next} exp`;
  $("#my-level-fill").style.width = `${Math.round(progress * 100)}%`;
  $("#my-level-bar").setAttribute("aria-valuenow", String(Math.round(progress * 100)));
  const upcoming = PERKS.find(([at]) => at > level);
  $("#my-level-next").textContent = upcoming
    ? `再 ${next - exp} exp 升 Lv ${level + 1}${upcoming[0] === level + 1 ? `・解鎖：${upcoming[1]}` : `・Lv ${upcoming[0]} 解鎖：${upcoming[1]}`}`
    : `再 ${next - exp} exp 升 Lv ${level + 1}`;
  $("#my-avatar").className = `avatar avatar--lg${frameClass(level)}`;
}

const ACTIONS = {
  daily_visit: "每日登入",
  streak_week: "連續登入 7 天",
  post: "發文",
  comment: "留言",
  like_given: "按讚",
  like_received: "貼文被按讚",
  comment_received: "貼文收到留言",
  comment_like_received: "留言被按讚",
  friend_made: "交到新朋友",
};

/** Exp pushed by the server (module/levels.py award()): update the card, cheer level-ups. */
function onExp({ exp, level, gained, action, level_up }) {
  showLevel(exp);
  if (level_up) {
    const perk = PERKS.find(([at]) => at === level);
    toast(`🎉 升到 Lv ${level}！${perk ? `解鎖：${perk[1]}` : ""}`, { type: "success", timeout: 6000 });
  } else if (["like_received", "comment_received", "comment_like_received", "friend_made"].includes(action)) {
    toast(`${ACTIONS[action]} +${gained} exp`);
  }
}

export function initProfile(data) {
  $("#my-account").textContent = data.account;
  $("#my-email").textContent = data.email;
  $("#my-joined").textContent = `${dateOnly(data.first_signup)} 加入`;

  const avatar = $("#my-avatar");
  avatar.src = avatarUrl(data.member_id);
  avatar.addEventListener("error", () => (avatar.src = DEFAULT_AVATAR), { once: true });

  showLevel(data.exp ?? 0);
  applyCard($("#profile"), bootstrap.settings?.card);
  socket.on("exp", onExp);
  if (data.visit?.gained) {
    const streak = data.visit.streak > 1 ? `連續登入 ${data.visit.streak} 天，` : "";
    toast(`${streak}每日登入 +${data.visit.gained} exp`);
  }

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
  avatar.className = "avatar avatar--lg";
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
  applyCard(dialog, null);
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
  $("#member-dialog-name").replaceChildren(user.account, " ", levelBadge(levelOf(user.exp ?? 0).level));
  $("#member-dialog-mood").textContent = user.mood || "";
  applyCard(dialog, result.card);
  const { level } = levelOf(user.exp ?? 0);
  avatar.className = `avatar avatar--lg${frameClass(level)}`;
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
  $("#member-dialog-actions").replaceChildren(
    ...(result.blocked ? [] : friendActions(user.account, result.is_friend)),
    ...safetyActions(memberId, user.account, result.blocked),
  );
}

/** Report and block (or unblock) someone else, at the end of their card. */
function safetyActions(memberId, account, blocked) {
  if (account === me.account) return [];
  const report = h(
    "button",
    {
      class: "btn btn--ghost btn--sm",
      type: "button",
      onClick: async () => {
        dialog.close();
        await reportDialog({ type: "member", id: memberId });
      },
    },
    icon("flag", { size: "sm" }),
    "檢舉",
  );
  const toggle = h(
    "button",
    {
      class: "btn btn--ghost btn--sm",
      type: "button",
      onClick: async () => {
        dialog.close();
        if (blocked) {
          try {
            await api(`/api/v1/blocks/${encodeURIComponent(account)}`, { method: "DELETE" });
            toast(`已解除封鎖 ${account}`);
          } catch (error) {
            toastError(error, "解除封鎖失敗");
          }
        } else if (await blockMember(account)) {
          emit("member:blocked", { id: memberId, account });
        }
      },
    },
    icon("ban", { size: "sm" }),
    blocked ? "解除封鎖" : "封鎖",
  );
  return [h("span", { class: "member-card__safety" }, report, toggle)];
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

