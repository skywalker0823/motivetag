// Images go straight from the browser to S3 with a presigned POST, then the server
// records them (see api/blueprints/api_images.py). Photos are shrunk in the browser
// first, so a 4 MB phone picture becomes a few hundred KB before it is sent.
import { api, ApiError, errorMessage } from "./api.js";

const MAX_BYTES = 5 * 1024 * 1024; // what S3 accepts (MAX_IMAGE_BYTES on the server)
const MAX_PICK_BYTES = 25 * 1024 * 1024; // before shrinking
export const IMAGE_TYPES = ["image/png", "image/jpeg", "image/gif", "image/webp"];
// Longest side in pixels: avatars are shown at 96px at most, posts at feed width.
const MAX_SIDE = { avatar: 512, block: 1600, cover: 1200 };
const QUALITY = 0.82;

/** Why `file` cannot be used as an image, or null. */
export function imageError(file) {
  if (!IMAGE_TYPES.includes(file.type)) return errorMessage("file type not allowed");
  // GIFs are sent as they are (shrinking would drop the animation).
  const limit = file.type === "image/gif" ? MAX_BYTES : MAX_PICK_BYTES;
  if (file.size > limit) return `圖片不能超過 ${limit / 1024 / 1024} MB`;
  return null;
}

function encode(canvas, type) {
  return new Promise((resolve) => canvas.toBlob(resolve, type, QUALITY));
}

/**
 * `file` scaled down to `maxSide` and re-encoded as WebP (JPEG where the browser
 * cannot write WebP), or `file` itself when that would not make it smaller.
 */
export async function shrinkImage(file, maxSide) {
  if (file.type === "image/gif") return file;
  let bitmap;
  try {
    bitmap = await createImageBitmap(file); // applies EXIF rotation in current browsers
  } catch {
    return file; // cannot decode here; S3 still gets the original if it is small enough
  }
  const scale = Math.min(1, maxSide / Math.max(bitmap.width, bitmap.height));
  const canvas = document.createElement("canvas");
  canvas.width = Math.round(bitmap.width * scale);
  canvas.height = Math.round(bitmap.height * scale);
  const context = canvas.getContext("2d");
  context.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
  bitmap.close();
  let blob = await encode(canvas, "image/webp");
  if (blob?.type !== "image/webp") {
    // Safari writes PNG when asked for WebP; JPEG has no transparency, so paint it white.
    context.globalCompositeOperation = "destination-over";
    context.fillStyle = "#fff";
    context.fillRect(0, 0, canvas.width, canvas.height);
    blob = await encode(canvas, "image/jpeg");
  }
  if (!blob || (scale === 1 && blob.size >= file.size)) blob = file;
  return blob;
}

/** Checks and shrinks `file` for upload; throws ApiError with a readable message. */
async function prepare(file, maxSide) {
  const error = imageError(file);
  if (error) throw new ApiError(error);
  const image = await shrinkImage(file, maxSide);
  if (image.size > MAX_BYTES) throw new ApiError("圖片不能超過 5 MB");
  return image;
}

/** Sends `image` to S3 with a presigned POST ({url, fields}). */
async function postToS3(signed, image) {
  const form = new FormData();
  for (const [name, value] of Object.entries(signed.fields)) form.append(name, value);
  form.append("file", image); // S3 requires the file to be the last field
  const upload = await fetch(signed.url, { method: "POST", body: form }).catch(() => null);
  if (!upload?.ok) throw new ApiError("圖片上傳失敗，請再試一次");
}

/** Uploads a photo for a chat message to `account`; returns the key to send it with. */
export async function uploadChatPhoto(file, account) {
  const image = await prepare(file, MAX_SIDE.block);
  const { data } = await api(`/api/v1/chats/${encodeURIComponent(account)}/images`, {
    method: "POST",
    body: { content_type: image.type },
  });
  await postToS3(data, image);
  return data.key;
}

/** Uploads `file` as an avatar or a post image; throws ApiError with a readable message. */
export async function uploadImage(file, type, targetId) {
  const image = await prepare(file, MAX_SIDE[type] ?? MAX_SIDE.block);
  const signed = await api("/api/images/upload", {
    method: "POST",
    body: { type, target_id: targetId, content_type: image.type },
  });
  if (!signed.ok) throw new ApiError(errorMessage(signed.error, "圖片上傳失敗"));
  await postToS3(signed, image);
  const done = await api("/api/images", { method: "POST", body: { type, target_id: targetId } });
  if (!done.ok) throw new ApiError(errorMessage(done.error, "圖片上傳失敗"));
}
