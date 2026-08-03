/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: {
          50: "#f4f7f6",
          100: "#e3ebe8",
          700: "#1f3d36",
          900: "#10241f",
        },
        accent: {
          500: "#0f766e",
          600: "#0d9488",
        },
      },
      fontFamily: {
        sans: ["\"Source Sans 3\"", "Segoe UI", "sans-serif"],
        display: ["\"Fraunces\"", "Georgia", "serif"],
      },
    },
  },
  plugins: [require("@tailwindcss/forms")],
};
