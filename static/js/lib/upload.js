// Images go straight from the browser to S3 with a presigned POST, then the server
// records them (see api/blueprints/api_images.py).
import { api, ApiError, errorMessage } from "./api.js";

const MAX_BYTES = 5 * 1024 * 1024;
export const IMAGE_TYPES = ["image/png", "image/jpeg", "image/gif"];

/** Uploads `file` as an avatar or a post image; throws ApiError with a readable message. */
export async function uploadImage(file, type, targetId) {
  if (!IMAGE_TYPES.includes(file.type)) throw new ApiError(errorMessage("file type not allowed"));
  if (file.size > MAX_BYTES) throw new ApiError("圖片不能超過 5 MB");
  const signed = await api("/api/images/upload", {
    method: "POST",
    body: { type, target_id: targetId, content_type: file.type },
  });
  if (!signed.ok) throw new ApiError(errorMessage(signed.error, "圖片上傳失敗"));
  const form = new FormData();
  for (const [name, value] of Object.entries(signed.fields)) form.append(name, value);
  form.append("file", file); // S3 requires the file to be the last field
  const upload = await fetch(signed.url, { method: "POST", body: form }).catch(() => null);
  if (!upload?.ok) throw new ApiError("圖片上傳失敗，請再試一次");
  const done = await api("/api/images", { method: "POST", body: { type, target_id: targetId } });
  if (!done.ok) throw new ApiError(errorMessage(done.error, "圖片上傳失敗"));
}
