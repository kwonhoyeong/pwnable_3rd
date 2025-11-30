/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        sentinel: {
          bg: '#050505',      // Deepest Black
          surface: '#121212', // Off-black for cards
          primary: '#00F0FF', // Neon Cyan
          secondary: '#7000FF', // Electric Purple
          success: '#00FF94', // Neon Green
          warning: '#FFB800', // Neon Orange
          error: '#FF0055',   // Neon Red
          text: {
            main: '#FFFFFF',
            muted: '#94A3B8',
          }
        },
        // Legacy mappings for compatibility
        background: '#050505',
        surface: '#121212',
        primary: '#00F0FF',
        secondary: '#7000FF',
      },
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
        heading: ['Outfit', 'sans-serif'],
      },
      boxShadow: {
        'neon-blue': '0 0 10px rgba(0, 240, 255, 0.5), 0 0 20px rgba(0, 240, 255, 0.3)',
        'neon-purple': '0 0 10px rgba(112, 0, 255, 0.5), 0 0 20px rgba(112, 0, 255, 0.3)',
      },
      dropShadow: {
        'neon': '0 0 10px rgba(0, 240, 255, 0.5)',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        }
      },
      animation: {
        'fade-in': 'fadeIn 0.5s ease-out forwards',
      }
    },
  },
  plugins: [],
}
