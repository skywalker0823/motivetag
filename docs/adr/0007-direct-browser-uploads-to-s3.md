# 0007. Browsers upload images straight to S3 with presigned POSTs

- Status: Accepted
- Date: 2026-09-26

## Context

Avatars and post images were uploaded to Flask, which streamed them to S3. Every
upload held a request in the app's only gevent worker
([0008](0008-single-gunicorn-worker.md)) for as long as the user's upload took,
went through nginx's body limit, and used the server's bandwidth twice. The bucket
is private; images are served by redirecting to short-lived presigned GET URLs.

## Decision

Uploads take three steps (`api/blueprints/api_images.py`, `static/js/member.js`):

1. `POST /api/images/upload` — the app checks the session, the image type
   (PNG/JPEG/GIF/WebP) and, for a post image, that the member owns the post. It returns
   a **presigned POST** for exactly one key (`avatar_<member>` or `block_<post>`),
   valid for 5 minutes, whose policy pins the `Content-Type` and limits the size to
   **1 B – 5 MB**.
2. The browser POSTs the file **directly to S3** (the bucket's CORS rule allows
   POST from `https://motivetag.com` only).
3. `POST /api/images` — the app checks the object exists with an allowed type
   (`HeadObject`) and records it on the member or post.

The S3 client uses the regional endpoint: the global one does not serve buckets in
opt-in regions like `ap-east-2`, and a browser will not follow its redirect for a
cross-origin POST.

## Consequences

- Image bytes never touch nginx or gunicorn, so a slow upload cannot stall chat.
- S3 enforces the size and type limits, not our code; the app cannot inspect the
  pixels. The browser shrinks photos before uploading instead
  (`static/js/lib/upload.js`: longest side 1600 px for posts, 512 px for avatars,
  re-encoded as WebP, or JPEG where the browser cannot write WebP; GIFs are sent as
  they are). Re-encoding through a canvas also drops EXIF data such as GPS
  coordinates, but only for clients that use our page.
- `/images/<key>` hands out the same presigned GET for half an hour (in memory,
  ADR 0008), so browsers can cache the image by URL; a new upload to that key
  forgets it. Other members may see an old avatar for up to the redirect's
  10-minute cache.
- A client could upload a non-image with an image `Content-Type`; it is only ever
  served from the S3 domain with that type, never from our origin, so it cannot
  run script on `motivetag.com`.
- Keys are fixed per member/post, so a new upload replaces the old image.

## Alternatives considered

- **Presigned PUT** — simpler, but cannot enforce a size range.
- **Keep proxying through Flask** — the problem above.
- **CloudFront with signed URLs / OAC** — caching and a nicer domain, at the cost
  of another distribution and key pair; worth it if image traffic grows.

## Revisit when

We want thumbnails or EXIF stripping (an S3-triggered Lambda), or image traffic
justifies a CDN.
