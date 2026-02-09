/** @type {import('tailwindcss').Config} */
import colors from 'tailwindcss/colors';

export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // Semantic color aliases using Tailwind built-in colors
        primary: colors.rose,
        neutral: colors.slate,
        secondary: colors.sky,
        accent: colors.violet,
        success: colors.emerald,
      },
      backgroundColor: {
        'dark-primary': '#0f0a0c',    // Deep rose black
        'dark-secondary': '#1a1618',  // Deep gray rose
        'dark-tertiary': '#252022',   // Lighter dark
      },
      fontFamily: {
        sans: ['"Noto Sans SC"', '"Plus Jakarta Sans"', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'monospace'],
      },
      keyframes: {
        // Message entry - refined slide-in effect
        'message-in': {
          '0%': { opacity: '0', transform: 'translateY(8px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        // Fade-in effect
        'fade-in': {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        // Loading pulse - subtle breathing effect
        'pulse-subtle': {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.6' },
        },
        // Recording ripple - clean expansion effect
        'ripple-subtle': {
          '0%': { transform: 'scale(1)', opacity: '0.5' },
          '100%': { transform: 'scale(1.3)', opacity: '0' },
        },
        // Typing indicator - refined bounce
        'typing': {
          '0%, 60%, 100%': { transform: 'translateY(0)' },
          '30%': { transform: 'translateY(-4px)' },
        },
      },
      animation: {
        'message-in': 'message-in 0.25s cubic-bezier(0.16, 1, 0.3, 1)',
        'fade-in': 'fade-in 0.2s ease-out',
        'pulse-subtle': 'pulse-subtle 2s ease-in-out infinite',
        'ripple-subtle': 'ripple-subtle 1.5s ease-out infinite',
        'typing': 'typing 1.2s ease-in-out infinite',
      },
      delay: {
        '75': '75ms',
        '150': '150ms',
        '225': '225ms',
      },
    },
  },
  plugins: [
    function({ addUtilities }) {
      addUtilities({
        '.scrollbar-elegant': {
          'scrollbar-width': 'thin',
          'scrollbar-color': 'rgba(244, 63, 94, 0.3) transparent',
        },
        '.scrollbar-elegant::-webkit-scrollbar': {
          'width': '6px',
        },
        '.scrollbar-elegant::-webkit-scrollbar-track': {
          'background': 'transparent',
        },
        '.scrollbar-elegant::-webkit-scrollbar-thumb': {
          'background-color': 'rgba(244, 63, 94, 0.3)',
          'border-radius': '3px',
        },
        '.scrollbar-elegant::-webkit-scrollbar-thumb:hover': {
          'background-color': 'rgba(244, 63, 94, 0.5)',
        },
      });
    },
  ],
}
