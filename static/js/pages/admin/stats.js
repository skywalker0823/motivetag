// 總覽 (GET /api/v1/admin/stats): number tiles, sign-ups and posts per day, and who
// posts and levels the most. One series per chart, so no legend; each bar has a
// tooltip, and a table carries the same numbers for screen readers.
import { api } from "../../lib/api.js";
import { h } from "../../lib/dom.js";
import { toastError } from "../../lib/toast.js";

function tile(label, value, note) {
  return h(
    "div",
    { class: "stat-tile" },
    h("p", { class: "stat-tile__label" }, label),
    h("p", { class: "stat-tile__value" }, String(value)),
    note && h("p", { class: "stat-tile__note" }, note),
  );
}

function dayLabel(iso) {
  return `${Number(iso.slice(5, 7))}/${Number(iso.slice(8, 10))}`;
}

/** A small bar chart of one count per day, with a hover/focus tooltip per bar. */
function dailyChart(title, daily, key) {
  const max = Math.max(1, ...daily.map((d) => d[key]));
  const total = daily.reduce((sum, d) => sum + d[key], 0);
  const tip = h("div", { class: "day-chart__tip", hidden: true });
  const show = (bar, d) => {
    tip.textContent = `${dayLabel(d.day)}：${d[key]}`;
    tip.hidden = false;
    tip.style.left = `${bar.offsetLeft + bar.offsetWidth / 2}px`;
  };
  const bars = daily.map((d) => {
    const bar = h(
      "div",
      { class: "day-chart__slot", tabindex: "0", "aria-label": `${dayLabel(d.day)}：${d[key]}` },
      h("div", { class: "day-chart__bar", style: { height: `${(d[key] / max) * 100}%` } }),
    );
    bar.addEventListener("pointerenter", () => show(bar, d));
    bar.addEventListener("focus", () => show(bar, d));
    bar.addEventListener("pointerleave", () => (tip.hidden = true));
    bar.addEventListener("blur", () => (tip.hidden = true));
    return bar;
  });
  return h(
    "figure",
    { class: "card day-chart" },
    h("figcaption", { class: "day-chart__title" }, title, h("span", { class: "day-chart__total" }, `14 天共 ${total}，最多 ${max}`)),
    h("div", { class: "day-chart__plot", "aria-hidden": "true" }, bars, tip),
    h(
      "div",
      { class: "day-chart__axis", "aria-hidden": "true" },
      h("span", null, dayLabel(daily[0].day)),
      h("span", null, "今天"),
    ),
    h(
      "table",
      { class: "visually-hidden" },
      h("caption", null, title),
      h("tr", null, h("th", null, "日期"), h("th", null, "數量")),
      daily.map((d) => h("tr", null, h("td", null, dayLabel(d.day)), h("td", null, String(d[key])))),
    ),
  );
}

function ranking(title, rows, text) {
  return h(
    "div",
    { class: "card ranking" },
    h("h2", { class: "ranking__title" }, title),
    rows.length
      ? h(
          "ol",
          { class: "ranking__list" },
          rows.map((row) => h("li", null, h("span", null, row.account), h("span", { class: "ranking__value" }, text(row)))),
        )
      : h("p", { class: "admin-hint" }, "還沒有資料"),
  );
}

export async function loadStats(root) {
  try {
    const { data } = await api("/api/v1/admin/stats");
    const m = data.members;
    root.replaceChildren(
      h(
        "div",
        { class: "stat-grid" },
        tile("會員", m.members - m.demo, `另有示範帳號 ${m.demo}`),
        tile("現在在線", data.online),
        tile("今日活躍", m.active_today, `7 天內 ${m.active_week}`),
        tile("今日新註冊", m.new_today, `7 天內 ${m.new_week}`),
        tile("今日貼文", data.posts.today, `7 天內 ${data.posts.week}・總共 ${data.posts.total}`),
        tile("今日留言", data.comments.today, `7 天內 ${data.comments.week}`),
        tile("今日私訊", data.messages.today, `7 天內 ${data.messages.week}`),
        tile("待處理檢舉", data.open_reports, `停權中 ${m.suspended}`),
      ),
      h(
        "div",
        { class: "chart-grid" },
        dailyChart("每日新註冊（不含示範帳號）", data.daily, "signups"),
        dailyChart("每日貼文", data.daily, "posts"),
      ),
      h(
        "div",
        { class: "chart-grid" },
        ranking("7 天內發文最多", data.top_posters, (row) => `${row.n} 篇`),
        ranking("等級最高", data.top_levels, (row) => `Lv ${row.level}・${row.exp} exp`),
      ),
      h("p", { class: "admin-hint" }, `已驗證 Email 的會員 ${m.verified} 人。「活躍」是當天打開過網站的人。`),
    );
  } catch (error) {
    toastError(error, "載入失敗");
  }
}
