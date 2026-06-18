/* global workbox */

importScripts("https://storage.googleapis.com/workbox-cdn/releases/6.5.4/workbox-sw.js");

if (workbox) {
  workbox.core.skipWaiting();
  workbox.core.clientsClaim();

  const { registerRoute } = workbox.routing;
  const { NetworkFirst, StaleWhileRevalidate } = workbox.strategies;

  registerRoute(
    ({ request }) =>
      request.destination === "style" ||
      request.destination === "script" ||
      request.destination === "image",
    new StaleWhileRevalidate({ cacheName: "assets" })
  );

  registerRoute(
    ({ url }) =>
      url.pathname.startsWith("/accounts") ||
      url.pathname.startsWith("/turns") ||
      url.pathname.startsWith("/movements") ||
      url.pathname.startsWith("/sync"),
    new NetworkFirst({ cacheName: "api" })
  );
}
