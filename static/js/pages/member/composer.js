// Writing a post: visibility (public, secret, anonymous), optional image and poll.
import { api, errorMessage } from "../../lib/api.js";
import { $, busy, h } from "../../lib/dom.js";
import { icon } from "../../lib/icons.js";
import { serverNow } from "../../lib/time.js";
import { toast, toastError } from "../../lib/toast.js";
import { IMAGE_TYPES, uploadImage } from "../../lib/upload.js";
import { prependPost } from "./feed.js";

const form = $("#composer");
const text = $("#composer-text");
const hint = $("#composer-hint");
const fileInput = $("#composer-file");
const imageBox = $("#composer-image");
const preview = $("#composer-image-preview");
const pollEditor = $("#poll-editor");
const pollOptions = $("#poll-options");
const pollToggle = $("#poll-toggle");

const HINTS = {
  PUBLIC: "",
  SECRET: "私密貼文只有你看得到，而且不能加 #標籤。",
  Anonymous: "匿名貼文不會顯示你是誰，只有訂閱 #Anonymous 的人看得到。",
};

let image = null;

const visibility = () => form.elements.visibility.value;

function setHint(message, error = false) {
  hint.textContent = message;
  hint.className = `composer__hint${error ? " composer__hint--error" : ""}`;
}

function autosize() {
  text.style.height = "auto";
  text.style.height = `${text.scrollHeight}px`;
}

// ---------- Image ----------

function setImage(file) {
  if (preview.src) URL.revokeObjectURL(preview.src);
  image = file;
  imageBox.hidden = !file;
  preview.src = file ? URL.createObjectURL(file) : "";
}

fileInput.addEventListener("change", () => {
  const file = fileInput.files[0];
  fileInput.value = "";
  if (!file) return;
  if (!IMAGE_TYPES.includes(file.type)) return toastError("file type not allowed");
  if (file.size > 5 * 1024 * 1024) return toastError("圖片不能超過 5 MB");
  setImage(file);
});
$("#composer-image-remove").addEventListener("click", () => setImage(null));

// ---------- Poll ----------

function addOption() {
  if (pollOptions.children.length >= 5) return;
  const row = h(
    "div",
    { class: "input-group" },
    h("input", {
      class: "input",
      placeholder: `選項 ${pollOptions.children.length + 1}`,
      maxlength: "40",
      "aria-label": `投票選項 ${pollOptions.children.length + 1}`,
    }),
    h(
      "button",
      {
        class: "icon-btn",
        type: "button",
        "aria-label": "移除這個選項",
        onClick: () => {
          if (pollOptions.children.length > 2) row.remove();
          $("#poll-add").hidden = pollOptions.children.length >= 5;
        },
      },
      icon("x"),
    ),
  );
  pollOptions.append(row);
  $("#poll-add").hidden = pollOptions.children.length >= 5;
}

function setPoll(open) {
  pollEditor.hidden = !open;
  pollToggle.setAttribute("aria-pressed", String(open));
  pollOptions.replaceChildren();
  if (open) {
    addOption();
    addOption();
    pollOptions.querySelector("input").focus();
  }
}

pollToggle.addEventListener("click", () => setPoll(pollEditor.hidden));
$("#poll-add").addEventListener("click", addOption);

// ---------- Submit ----------

function problem(content, type, options) {
  if (!content) return "寫點什麼再發佈吧";
  if (type === "SECRET" && content.includes("#")) return HINTS.SECRET;
  if (!pollEditor.hidden && options.length < 2) return "投票至少需要 2 個選項";
  return null;
}

form.addEventListener("change", (event) => {
  if (event.target.name !== "visibility") return;
  form.dataset.visibility = visibility();
  setHint(HINTS[visibility()]);
});

text.addEventListener("input", autosize);
text.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) form.requestSubmit();
});

form.addEventListener("submit", (event) => {
  event.preventDefault();
  const content = text.value.trim();
  const type = visibility();
  const options = [...pollOptions.querySelectorAll("input")].map((i) => i.value.trim()).filter(Boolean);
  const error = problem(content, type, options);
  if (error) {
    setHint(error, true);
    text.focus();
    return;
  }

  busy(form.querySelector("[type=submit]"), async () => {
    try {
      const result = await api("/api/blocks", {
        method: "POST",
        body: {
          type,
          content,
          time: serverNow(),
          tags: type === "Anonymous" ? "Anonymous" : null,
          vote_box: pollEditor.hidden ? [] : options,
        },
      });
      if (!result.ok) throw result;
      const post = result.data[0];
      if (image) {
        try {
          await uploadImage(image, "block", post.block_id);
          post.block_img = `block_${post.block_id}`;
        } catch (uploadError) {
          toastError(uploadError, "貼文已發佈，但圖片上傳失敗");
        }
      }
      prependPost(post);
      text.value = "";
      autosize();
      setImage(null);
      setPoll(false);
      setHint(HINTS[type]);
      toast("已發佈", { type: "success" });
    } catch (submitError) {
      setHint(errorMessage(submitError, "發佈失敗，請稍後再試"), true);
    }
  });
});

export function initComposer() {
  form.dataset.visibility = visibility();
}
