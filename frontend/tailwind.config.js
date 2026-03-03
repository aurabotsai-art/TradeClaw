/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'tc-bg': '#1a1a1a',
        'tc-raised': '#222222',
        'tc-overlay': '#2a2a2a',
        'tc-border': '#333333',
        'tc-accent': '#ff6b35',
        'tc-green': '#4ade80',
        'tc-red': '#f87171',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
        display: ['Syne', 'sans-serif'],
      },
    },
  },
  plugins: [],
};
