/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: '#069494',    // Primary buttons, headings, icons
        accent: '#14B8A6',     // Links, active states, progress indicators
        highlight: '#F59E0B',  // Notifications, badges, important CTAs
        canvas: '#FFFFFF',     // Background
      },
      fontFamily: {
        sans: ['Outfit', 'Inter', 'sans-serif'],
      }
    },
  },
  plugins: [],
}
