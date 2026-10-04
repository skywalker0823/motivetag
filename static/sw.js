// MotiveTag's service worker (served at /sw.js): shows pushed notifications
// (module/push.py) and opens the right page when one is tapped. It caches nothing,
// so a deploy is never hidden behind an old copy of the site.

self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (event) => event.waitUntil(self.clients.claim()));

self.addEventListener("push", (event) => {
  let data = {};
  try {
    data = event.data?.json() ?? {};
  } catch {
    data = { body: event.data?.text() };
  }
  event.waitUntil(
    self.registration.showNotification(data.title || "MotiveTag", {
      body: data.body || "",
      icon: "/img/icon-192.png",
      badge: "/img/icon-192.png",
      data: { url: data.url || "/" },
      // One notification per conversation or kind; a newer one replaces it.
      tag: data.url || "motivetag",
      renotify: true,
    }),
  );
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const url = new URL(event.notification.data?.url || "/", self.location.origin).href;
  event.waitUntil(
    (async () => {
      const tabs = await self.clients.matchAll({ type: "window", includeUncontrolled: true });
      const open = tabs.find((tab) => new URL(tab.url).origin === self.location.origin);
      if (open) {
        await open.focus();
        return open.navigate(url);
      }
      return self.clients.openWindow(url);
    })(),
  );
});
