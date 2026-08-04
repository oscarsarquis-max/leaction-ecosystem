/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        ink: '#1a2332',
        muted: '#5a6778',
        school: {
          50: '#eef8f5',
          100: '#d5efe8',
          500: '#0f6b5c',
          600: '#0c574b',
          700: '#0a453c',
          900: '#062e28',
        },
        panel: '#f3f5f7',
      },
      fontFamily: {
        sans: ['"IBM Plex Sans"', 'system-ui', 'sans-serif'],
      },
      boxShadow: {
        panel: '0 1px 2px rgba(26, 35, 50, 0.06), 0 8px 24px rgba(26, 35, 50, 0.04)',
      },
    },
  },
  plugins: [],
}
