/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // Science-focused palette for node categorization
        physics: '#3B82F6',     // Blue-500
        math: '#EF4444',        // Red-500
        cs: '#10B981',          // Emerald-500
        biology: '#8B5CF6',     // Violet-500
        chemistry: '#F59E0B',   // Amber-500
        
        // UI Layers for Glass Interface
        glass: {
          light: 'rgba(255, 255, 255, 0.85)',
          dark: 'rgba(15, 23, 42, 0.85)',
        },
      },
      backdropBlur: {
        xs: '2px',
      },
      animation: {
        'slide-in-right': 'slideInRight 0.3s ease-out',
        'slide-out-right': 'slideOutRight 0.3s ease-out',
        'fade-in': 'fadeIn 0.2s ease-out',
      },
      keyframes: {
        slideInRight: {
          '0%': { transform: 'translateX(100%)' },
          '100%': { transform: 'translateX(0)' },
        },
        slideOutRight: {
          '0%': { transform: 'translateX(0)' },
          '100%': { transform: 'translateX(100%)' },
        },
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
      },
    },
  },
  plugins: [],
}