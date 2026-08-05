/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        qmind: {
          app: "var(--qmind-bg-app)",
          surface: "var(--qmind-bg-surface)",
          main: "var(--qmind-text-main)",
          muted: "var(--qmind-text-muted)",
          "text-main": "var(--qmind-text-main)",
          "text-muted": "var(--qmind-text-muted)",
          success: "var(--qmind-semantic-success)",
          warning: "var(--qmind-semantic-warning)",
          danger: "var(--qmind-semantic-danger)",
          info: "var(--qmind-semantic-info)",
          future: "var(--qmind-semantic-future)",
          current: "var(--qmind-semantic-current)",
          disabled: "var(--qmind-semantic-disabled)",
          semantic: {
            success: "var(--qmind-semantic-success)",
            warning: "var(--qmind-semantic-warning)",
            danger: "var(--qmind-semantic-danger)",
            info: "var(--qmind-semantic-info)",
            future: "var(--qmind-semantic-future)",
            current: "var(--qmind-semantic-current)",
            disabled: "var(--qmind-semantic-disabled)",
          },
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        display: ["Inter", "system-ui", "sans-serif"],
      },
      borderRadius: {
        qmind: "var(--qmind-radius-md)",
        "qmind-sm": "var(--qmind-radius-sm)",
        "qmind-md": "var(--qmind-radius-md)",
      },
      boxShadow: {
        qmind: "var(--qmind-shadow-card)",
        "qmind-card": "var(--qmind-shadow-card)",
      },
    },
  },
  plugins: [require("@tailwindcss/forms")],
};
