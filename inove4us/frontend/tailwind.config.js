/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx,ts,tsx}'],
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#f1edff',
          100: '#e4dbff',
          200: '#c9b8ff',
          300: '#a98fff',
          400: '#8a64f5',
          500: '#6d3fe6',
          600: '#5a27cf',
          700: '#3f17a8',
          800: '#3a1490',
          900: '#2c0d72',
        },
        accent: {
          50: '#fdeaf4',
          100: '#fbd0e6',
          200: '#f8a3cd',
          300: '#f56fb0',
          400: '#ef3d93',
          500: '#e6007e',
          600: '#c4006b',
          700: '#9c0055',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
