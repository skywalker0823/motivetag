// Phone and computer notifications (api/v1/push.py): the service worker (/sw.js)
// receives them; this module asks for permission and hands the subscription to the
// server. On iPhone this only works after "加入主畫面" and opening it from there.
import { api, ApiError } from "./api.js";

export const supported = () => "serviceWorker" in navigator && "PushManager" in window && "Notification" in window;

/** iPhone or iPad in Safari, not opened from the home screen: no notifications yet. */
export const needsHomeScreen = () =>
  /iPhone|iPad|iPod/.test(navigator.userAgent) && !matchMedia("(display-mode: standalone)").matches;

function keyBytes(base64url) {
  const base64 = base64url.replace(/-/g, "+").replace(/_/g, "/").padEnd(Math.ceil(base64url.length / 4) * 4, "=");
  return Uint8Array.from(atob(base64), (c) => c.charCodeAt(0));
}

/** Registers the service worker (which also lets the site be installed as an app). */
export function registerWorker() {
  if (!("serviceWorker" in navigator)) return Promise.resolve(null);
  return navigator.serviceWorker.register("/sw.js").catch(() => null);
}

async function currentSubscription() {
  const registration = await registerWorker();
  return registration ? registration.pushManager.getSubscription() : null;
}

/** Whether this browser currently gets notifications. */
export async function isOn() {
  if (!supported() || Notification.permission !== "granted") return false;
  return Boolean(await currentSubscription());
}

/** Asks for permission and subscribes; throws ApiError with a readable message. */
export async function turnOn() {
  if (!supported()) throw new ApiError("這個瀏覽器不支援通知");
  const { data } = await api("/api/v1/push/key");
  const permission = await Notification.requestPermission();
  if (permission !== "granted") throw new ApiError("通知權限被拒絕了，可以到瀏覽器或手機的設定裡開啟");
  const registration = await registerWorker();
  if (!registration) throw new ApiError("無法啟用通知，請稍後再試");
  await navigator.serviceWorker.ready;
  const subscription =
    (await registration.pushManager.getSubscription()) ??
    (await registration.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: keyBytes(data.key) }));
  await api("/api/v1/push/subscriptions", { method: "POST", body: subscription.toJSON() });
}

export async function turnOff() {
  const subscription = await currentSubscription();
  if (!subscription) return;
  await api("/api/v1/push/subscriptions", { method: "DELETE", body: { endpoint: subscription.endpoint } }).catch(() => {});
  await subscription.unsubscribe();
}

/** Keeps the server's copy fresh: browsers sometimes renew a subscription on their own. */
export async function refresh() {
  if (!(await isOn())) return;
  const subscription = await currentSubscription();
  api("/api/v1/push/subscriptions", { method: "POST", body: subscription.toJSON() }).catch(() => {});
}
