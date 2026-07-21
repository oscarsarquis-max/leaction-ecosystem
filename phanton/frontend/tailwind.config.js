/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        display: ['"Sora"', 'system-ui', 'sans-serif'],
        body: ['"IBM Plex Sans"', 'system-ui', 'sans-serif'],
        mono: ['"IBM Plex Mono"', 'ui-monospace', 'monospace'],
      },
      colors: {
        ink: {
          950: '#0b1220',
          900: '#111a2e',
          800: '#1a2740',
          700: '#243352',
          500: '#6b7c99',
          200: '#c5d0e2',
          100: '#e8eef8',
        },
        signal: {
          DEFAULT: '#22c55e',
          glow: '#4ade80',
          soft: '#dcfce7',
        },
        amber: {
          run: '#f59e0b',
        },
      },
      boxShadow: {
        approve: '0 0 0 1px rgba(34,197,94,0.35), 0 0 24px rgba(34,197,94,0.45)',
      },
    },
  },
  plugins: [],
}
