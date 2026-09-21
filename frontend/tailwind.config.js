/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Core dark surfaces
        navy: {
          950: '#060A14',
          900: '#0B1120',
          800: '#111827',
          700: '#1A2332',
          600: '#243044',
        },
        // Primary accent — teal/cyan family
        primary: '#0D9488',
        accent: '#14B8A6',
        'accent-light': '#5EEAD4',
        'accent-muted': '#0F766E',
        // Supporting — indigo
        indigo: {
          DEFAULT: '#6366F1',
          muted: '#4338CA',
          light: '#818CF8',
        },
        // Semantic tokens
        surface: {
          DEFAULT: '#111827',
          raised: '#1A2332',
          overlay: '#243044',
        },
        // Highlight / warning
        highlight: '#F59E0B',
        'highlight-dark': '#D97706',
      },
      fontFamily: {
        sans: ['Inter', 'Outfit', 'system-ui', 'sans-serif'],
        display: ['Outfit', 'Inter', 'sans-serif'],
      },
      boxShadow: {
        'card': '0 1px 3px rgba(0,0,0,0.3), 0 1px 2px rgba(0,0,0,0.2)',
        'card-hover': '0 4px 12px rgba(0,0,0,0.4), 0 2px 4px rgba(0,0,0,0.3)',
        'glow-teal': '0 0 20px rgba(20,184,166,0.15)',
        'glow-teal-sm': '0 0 10px rgba(20,184,166,0.1)',
        'inner-glow': 'inset 0 1px 0 rgba(255,255,255,0.05)',
      },
      borderColor: {
        'subtle': 'rgba(255,255,255,0.08)',
        'subtle-light': 'rgba(255,255,255,0.12)',
      },
      keyframes: {
        'fade-in': {
          '0%': { opacity: '0', transform: 'translateY(8px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        'gauge-fill': {
          '0%': { strokeDashoffset: '282.74' },
        },
        'pulse-soft': {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.6' },
        },
        'typing-dot': {
          '0%, 60%, 100%': { opacity: '0.3', transform: 'translateY(0)' },
          '30%': { opacity: '1', transform: 'translateY(-4px)' },
        },
      },
      animation: {
        'fade-in': 'fade-in 0.4s ease-out forwards',
        'fade-in-delay': 'fade-in 0.4s ease-out 0.1s forwards',
        'gauge-fill': 'gauge-fill 1s ease-out forwards',
        'pulse-soft': 'pulse-soft 2s ease-in-out infinite',
        'typing-dot-1': 'typing-dot 1.4s ease-in-out infinite',
        'typing-dot-2': 'typing-dot 1.4s ease-in-out 0.2s infinite',
        'typing-dot-3': 'typing-dot 1.4s ease-in-out 0.4s infinite',
      },
    },
  },
  plugins: [],
}
