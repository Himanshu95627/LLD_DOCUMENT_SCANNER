import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The backend (app/main.py) only allows CORS from http://localhost:3000,
// so we pin the dev server to that port. strictPort fails loudly instead
// of silently moving to 3001 (which the backend would then reject).
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    strictPort: true,
  },
});
