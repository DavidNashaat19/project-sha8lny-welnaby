/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: '#050810',
        surface: '#0a0f1e',
        card: '#0d1428',
        border: '#1a2340',
        primary: '#00D4FF',
        secondary: '#7B61FF',
        highlight: '#FFD166',
        textPrimary: '#F0F4FF',
        textMuted: '#5A6490',
      },
      fontFamily: {
        sans: ['DM Sans', 'Sora', 'sans-serif'],
        display: ['Clash Display', 'Cabinet Grotesk', 'sans-serif'],
        arabic: ['Cairo', 'Tajawal', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
    },
  },
  plugins: [],
}
