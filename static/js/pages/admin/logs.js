// 紀錄 (GET /api/v1/admin/logs): what admins did here, newest first.
import { api } from "../../lib/api.js";
import { h } from "../../lib/dom.js";
import { timeAgo } from "../../lib/time.js";
import { toastError } from "../../lib/toast.js";

const ACTIONS = {
  suspend: "停權",
  lift: "解除停權",
  remove: "刪除被檢舉內容",
  dismiss: "保留被檢舉內容",
  level: "調整等級",
  verify: "設為已驗證",
  notice: "傳通知",
  announce: "發布公告",
};

export async function loadLogs(root) {
  try {
    const { data } = await api("/api/v1/admin/logs");
    root.replaceChildren(
      data.length
        ? h(
            "ol",
            { class: "card log-list" },
            data.map((row) =>
              h(
                "li",
                null,
                h("span", { class: "log-list__when", title: row.at }, timeAgo(row.at)),
                h(
                  "span",
                  null,
                  h("strong", null, row.admin),
                  ` ${ACTIONS[row.action] ?? row.action}`,
                  row.target ? ` ${row.target}` : "",
                  row.detail ? `：${row.detail}` : "",
                ),
              ),
            ),
          )
        : h("p", { class: "card admin-hint" }, "還沒有紀錄"),
    );
  } catch (error) {
    toastError(error, "載入失敗");
  }
}
