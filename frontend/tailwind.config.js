/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: '#069494',    // 20%: Buttons, Headings, Icons
        active: '#00F0FF',     // 7%: Links, Active States, Progress Indicators
        accent: '#FF69B4',     // 3%: Notifications, Badges, Important CTAs
        canvas: '#FFFFFF',     // 70%: Background
      },
      fontFamily: {
        sans: ['Outfit', 'Inter', 'sans-serif'],
      }
    },
  },
  plugins: [],
}
