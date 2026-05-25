import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  build: {
    chunkSizeWarningLimit: 1024,
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (!id.includes("node_modules")) return undefined;
          if (
            id.includes("/react/") ||
            id.includes("/react-dom/") ||
            id.includes("/react-router-dom/")
          ) {
            return "react-vendor";
          }
          if (
            id.includes("/antd/") ||
            id.includes("/@ant-design/icons/") ||
            id.includes("/@ant-design/")
          ) {
            return "antd-vendor";
          }
          if (id.includes("/axios/") || id.includes("/dayjs/")) {
            return "utils-vendor";
          }
          return undefined;
        }
      }
    }
  },
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true
      },
      "/health": {
        target: "http://localhost:8000",
        changeOrigin: true
      }
    }
  }
});
