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
        background: '#111315', // Deep Charcoal
        surface: '#1A1D1F',    // Soft Black
        primary: '#6C5DD3',    // Royal Purple
        secondary: '#6F767E',  // Slate Grey
        accent: {
          blue: '#3F8CFF',
          orange: '#FF754C',
          yellow: '#FFCE73',
          green: '#7FBA7A',
        },
        text: {
          main: '#FFFFFF',
          muted: '#6F767E',
        },
        // Semantic mappings for compatibility
        critical: '#FF754C',
        high: '#FFCE73',
        medium: '#3F8CFF',
        low: '#7FBA7A',
      },
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
