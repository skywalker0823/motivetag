// Landing page: sign in, sign up (with a live account-name check) and the hero text.
import { api, errorMessage } from "../lib/api.js";
import { $, busy, debounce } from "../lib/dom.js";
import { hydrateIcons } from "../lib/icons.js";
import { serverNow } from "../lib/time.js";

const ACCOUNT = /^[\p{L}\p{N}_]{3,20}$/u;
const RESERVED = new Set(["api", "tag", "images", "healthz", "js", "css", "img"]);

// Someone already signed in goes straight to their page.
api("/api/member")
  .then((me) => me.ok && me.data && location.replace(`/${encodeURIComponent(me.data.account)}`))
  .catch(() => {});

hydrateIcons();

// ---------- Tabs ----------

const tabs = [$("#tab-signin"), $("#tab-signup")];

function selectTab(tab) {
  for (const t of tabs) {
    const selected = t === tab;
    t.setAttribute("aria-selected", String(selected));
    t.tabIndex = selected ? 0 : -1;
    document.getElementById(t.getAttribute("aria-controls")).hidden = !selected;
  }
  document.getElementById(tab.getAttribute("aria-controls")).querySelector("input").focus();
}

for (const tab of tabs) {
  tab.addEventListener("click", () => selectTab(tab));
  tab.addEventListener("keydown", (event) => {
    if (event.key === "ArrowRight" || event.key === "ArrowLeft") {
      const next = tabs[(tabs.indexOf(tab) + 1) % tabs.length];
      next.focus();
      selectTab(next);
    }
  });
}

// ---------- Sign in ----------

const signinForm = $("#panel-signin");

async function signIn(account, password) {
  const result = await api("/api/member", {
    method: "PUT",
    body: { account, password, time: serverNow() },
  });
  if (!result.ok) throw new Error(errorMessage(result.error, "帳號或密碼錯誤"));
  location.assign(`/${encodeURIComponent(result.data.account)}`);
}

function showError(form, message) {
  form.querySelector("[data-error]").textContent = message;
}

signinForm.addEventListener("submit", (event) => {
  event.preventDefault();
  const { account, password } = signinForm.elements;
  showError(signinForm, "");
  if (!account.value || !password.value) {
    showError(signinForm, "請輸入帳號和密碼");
    (account.value ? password : account).focus();
    return;
  }
  busy(signinForm.querySelector("[type=submit]"), () =>
    signIn(account.value.trim(), password.value).catch((error) =>
      showError(signinForm, errorMessage(error, error.message)),
    ),
  );
});

$("#guest").addEventListener("click", (event) =>
  busy(event.currentTarget, () =>
    signIn("guest", "guest").catch(() => showError(signinForm, "訪客帳號目前無法使用")),
  ),
);

// ---------- Sign up ----------

const signupForm = $("#panel-signup");
const accountInput = signupForm.elements.account;
const accountHint = $("#account-hint");
const defaultHint = accountHint.textContent;

function setAccountHint(text, state) {
  accountHint.textContent = text;
  accountHint.className = `field__hint${state ? ` field__hint--${state}` : ""}`;
  accountInput.setAttribute("aria-invalid", String(state === "error"));
}

function accountProblem(name) {
  if (!ACCOUNT.test(name) || RESERVED.has(name.toLowerCase())) {
    return "帳號需為 3–20 個字母、數字或底線";
  }
  return null;
}

const checkAccount = debounce(async (name) => {
  if (name !== accountInput.value.trim()) return; // typed on since
  try {
    const result = await api("/api/member", { query: { account_check: name } });
    if (name !== accountInput.value.trim()) return;
    if (result.ok) setAccountHint("這個帳號已經有人使用", "error");
    else setAccountHint(`可以使用，你的頁面會是 motivetag.com/${name}`, "ok");
  } catch {
    setAccountHint(defaultHint);
  }
}, 400);

accountInput.addEventListener("input", () => {
  const name = accountInput.value.trim();
  if (!name) return setAccountHint(defaultHint);
  const problem = accountProblem(name);
  if (problem) return setAccountHint(problem, "error");
  setAccountHint("檢查中…");
  checkAccount(name);
});

signupForm.elements.birthday.max = serverNow().slice(0, 10);

signupForm.addEventListener("submit", (event) => {
  event.preventDefault();
  const { account, password, email, birthday } = signupForm.elements;
  const name = account.value.trim();
  const problem =
    accountProblem(name) ??
    (password.value.length < 8 ? "密碼至少 8 個字元" : null) ??
    (!email.checkValidity() || !email.value ? "請輸入正確的 Email" : null) ??
    (!birthday.value ? "請選擇生日" : null);
  showError(signupForm, problem ?? "");
  if (problem) return;

  busy(signupForm.querySelector("[type=submit]"), async () => {
    try {
      const result = await api("/api/member", {
        method: "POST",
        body: {
          account: name,
          password: password.value,
          email: email.value.trim(),
          birthday: birthday.value,
          first_signup: serverNow().slice(0, 10),
        },
      });
      if (!result.ok) throw new Error(errorMessage(result.error, "註冊失敗，請稍後再試"));
      await signIn(name, password.value);
    } catch (error) {
      showError(signupForm, errorMessage(error, error.message));
    }
  });
});

// ---------- Hero ----------

const typed = $("#typed");
const words = ["#任何事", "#攝影", "#咖啡", "#同好", "新朋友"];
if (!matchMedia("(prefers-reduced-motion: reduce)").matches) {
  let index = 0;
  setInterval(() => {
    index = (index + 1) % words.length;
    typed.textContent = words[index];
  }, 2200);
}
