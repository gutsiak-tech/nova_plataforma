// Tailwind source of truth.
// This CommonJS config is the active config loaded by PostCSS/Vite.
// Keep visual tokens aligned with dashboard/src/index.css and dashboard/src/lib/theme.ts.

/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: [
          "ui-sans-serif",
          "system-ui",
          "Segoe UI",
          "Inter",
          "Roboto",
          "Helvetica Neue",
          "Arial",
          "Noto Sans",
          "Liberation Sans",
          "sans-serif",
        ],
        mono: [
          "ui-monospace",
          "SFMono-Regular",
          "Consolas",
          "Liberation Mono",
          "monospace",
        ],
      },
      boxShadow: {
        soft:
          "0 1px 2px rgba(15, 23, 42, 0.06), 0 8px 24px rgba(15, 23, 42, 0.06)",
        lift:
          "0 2px 4px rgba(15, 23, 42, 0.08), 0 16px 48px rgba(15, 23, 42, 0.12)",
        shell:
          "0 1px 2px rgba(15, 23, 42, 0.06), 0 8px 24px rgba(15, 23, 42, 0.06)",
      },
      colors: {
        orgmigra: {
          blue: {
            50: "#eef3fa",
            100: "#dce7f5",
            200: "#b9cfec",
            300: "#8aafd9",
            400: "#5c8fc7",
            500: "#194E93",
            600: "#194E93",
            700: "#184890",
            800: "#133a72",
            900: "#0f2d56",
          },
          green: {
            50: "#f0f9ec",
            100: "#dff3d6",
            200: "#c2e8b0",
            500: "#65B244",
            600: "#65B244",
            700: "#60B040",
            800: "#4d8c33",
          },
          purple: {
            50: "#f4eef8",
            100: "#e8dcf2",
            200: "#d1b9e4",
            500: "#8C5DAC",
            600: "#8C5DAC",
            700: "#8858A8",
            800: "#6d4586",
          },
          yellow: {
            50: "#fffbeb",
            100: "#fef3c7",
            200: "#fde68a",
            500: "#F9BD2C",
            600: "#F8B828",
            700: "#d4980f",
            800: "#b07d0c",
          },
        },
      },
      borderRadius: {
        xl: "1rem",
        "2xl": "1.35rem",
      },
    },
  },
  plugins: [require("@tailwindcss/forms"), require("@tailwindcss/typography")],
};
