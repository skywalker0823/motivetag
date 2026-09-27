// The database stores Taipei wall-clock times, and Flask sends them labelled "GMT"
// ("Sun, 27 Sep 2026 10:30:00 GMT" means 10:30 in Taipei). These helpers turn them
// into real instants and format them in the viewer's language, without moment.js.

const TAIPEI_OFFSET_MS = 8 * 60 * 60 * 1000;
const relativeFormat = new Intl.RelativeTimeFormat("zh-TW", { numeric: "auto" });
const serverFormat = new Intl.DateTimeFormat("sv-SE", {
  timeZone: "Asia/Taipei",
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
  hour: "2-digit",
  minute: "2-digit",
  second: "2-digit",
  hour12: false,
});

const WALL_CLOCK = /^(\d{4})-(\d{2})-(\d{2})[ T](\d{2}):(\d{2})(?::(\d{2}))?$/;

/** A DATETIME from the API ("…GMT" or "YYYY-MM-DD HH:mm:ss", both Taipei time) as a Date. */
export function fromServer(value) {
  if (!value) return null;
  const parts = WALL_CLOCK.exec(value);
  const asUtc = parts
    ? Date.UTC(+parts[1], parts[2] - 1, +parts[3], +parts[4], +parts[5], +(parts[6] ?? 0))
    : new Date(value).getTime();
  return Number.isNaN(asUtc) ? null : new Date(asUtc - TAIPEI_OFFSET_MS);
}

/** Now, in the "YYYY-MM-DD HH:mm:ss" Taipei form the API stores. */
export function serverNow() {
  return serverFormat.format(new Date());
}

const UNITS = [
  ["year", 365 * 24 * 3600],
  ["month", 30 * 24 * 3600],
  ["week", 7 * 24 * 3600],
  ["day", 24 * 3600],
  ["hour", 3600],
  ["minute", 60],
];

/** "3 分鐘前", "昨天"… for a Date. */
export function relative(date) {
  if (!date) return "";
  const seconds = (date.getTime() - Date.now()) / 1000;
  for (const [unit, size] of UNITS) {
    if (Math.abs(seconds) >= size) return relativeFormat.format(Math.round(seconds / size), unit);
  }
  return "剛剛";
}

/** Full local date and time, for tooltips. */
export function fullDateTime(date) {
  return date
    ? date.toLocaleString("zh-TW", { dateStyle: "medium", timeStyle: "short" })
    : "";
}

/** A DATE column (birthday, sign-up day) as "2000年1月1日". */
export function dateOnly(value) {
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? ""
    : date.toLocaleDateString("zh-TW", { timeZone: "UTC", dateStyle: "long" });
}

/** A <time> element showing relative time, with the full time on hover. */
export function timeAgo(value) {
  const date = value ? fromServer(value) : new Date();
  const el = document.createElement("time");
  if (date) {
    el.dateTime = date.toISOString();
    el.title = fullDateTime(date);
    el.dataset.relative = "";
  }
  el.textContent = relative(date);
  return el;
}

// Keeps every relative time on the page current ("剛剛" becomes "1 分鐘前").
setInterval(() => {
  if (document.visibilityState !== "visible") return;
  for (const el of document.querySelectorAll("time[data-relative]")) {
    el.textContent = relative(new Date(el.dateTime));
  }
}, 60_000);
