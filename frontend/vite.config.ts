import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { VitePWA } from "vite-plugin-pwa";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// Inside Docker Compose the backend is reachable at http://backend:8000.
// Locally (npm run dev) it defaults to http://localhost:8000.
const proxyTarget = process.env.VITE_PROXY_TARGET || "http://localhost:8000";

export default defineConfig({
  // The "@/..." alias must be declared here for Vite's bundler — tsconfig
  // "paths" only affects TypeScript's type-checker, not module resolution.
  resolve: {
    alias: { "@": path.resolve(__dirname, "src") },
  },
  plugins: [
    react(),
    VitePWA({
      registerType: "autoUpdate",
      includeAssets: ["favicon.svg", "apple-touch-icon.png"],
      // serve manifest + service worker in `vite dev` too, so the app is
      // installable during local/Docker development (not just production builds)
      devOptions: { enabled: true, type: "module", navigateFallback: "index.html" },
      manifest: {
        name: "Sainext — Inventory OS",
        short_name: "Sainext",
        description: "Stock check, material blocking, orders, dispatch and dealer management.",
        theme_color: "#121824",
        background_color: "#121824",
        display: "standalone",
        orientation: "portrait",
        start_url: "/",
        scope: "/",
        lang: "en",
        categories: ["business", "productivity"],
        icons: [
          { src: "icon-192.png", sizes: "192x192", type: "image/png", purpose: "any" },
          { src: "icon-512.png", sizes: "512x512", type: "image/png", purpose: "any" },
          { src: "icon-maskable-512.png", sizes: "512x512", type: "image/png", purpose: "maskable" }
        ],
        shortcuts: [
          { name: "Stock Check", short_name: "Stock", url: "/stock-check", icons: [{ src: "icon-192.png", sizes: "192x192" }] },
          { name: "Orders", short_name: "Orders", url: "/orders", icons: [{ src: "icon-192.png", sizes: "192x192" }] },
          { name: "Material Blocking", short_name: "Blocks", url: "/blocks", icons: [{ src: "icon-192.png", sizes: "192x192" }] }
        ]
      },
      workbox: {
        navigateFallback: "/index.html",
        runtimeCaching: [
          {
            // app data: fresh-first, fall back to last-known cache when offline
            urlPattern: ({ url }) => url.pathname.startsWith("/api/"),
            handler: "NetworkFirst",
            options: {
              cacheName: "sainext-api",
              networkTimeoutSeconds: 5,
              expiration: { maxEntries: 200, maxAgeSeconds: 60 * 60 * 24 },
              cacheableResponse: { statuses: [0, 200] },
            },
          },
          {
            urlPattern: ({ request }) => request.destination === "font",
            handler: "CacheFirst",
            options: {
              cacheName: "sainext-fonts",
              expiration: { maxEntries: 30, maxAgeSeconds: 60 * 60 * 24 * 365 },
            },
          },
        ],
      },
    })
  ],
  server: {
    host: true,
    port: 5173,
    proxy: {
      "/api": { target: proxyTarget, changeOrigin: true }
    }
  }
});
