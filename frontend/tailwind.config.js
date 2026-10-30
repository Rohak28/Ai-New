/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
          sans: ['Inter', 'sans-serif'],
          heading: ['Outfit', 'sans-serif'],
          mono: ['JetBrains Mono', 'monospace'],
      },
      colors: {
          brand: {
              accent: '#2563eb',
              pass: '#059669',
              fail: '#dc2626',
              warn: '#d97706'
          }
      },
      animation: {
          'fade-in': 'fadeIn 0.4s ease-out',
          'slide-up': 'slideUp 0.5s ease-out',
          'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      },
      keyframes: {
          fadeIn: {
              '0%': { opacity: '0' },
              '100%': { opacity: '1' },
          },
          slideUp: {
              '0%': { opacity: '0', transform: 'translateY(20px)' },
              '100%': { opacity: '1', transform: 'translateY(0)' },
          }
      }
    },
  },
  plugins: [],
}
