/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./index-v2.html'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        primary: '#4da6ff',
        'background-dark': '#0a0e1a',
        'neon-blue': '#4da6ff',
      },
      fontFamily: {
        display: ['Inter', 'sans-serif'],
        body: ['Inter', 'sans-serif'],
        heading: ['"DM Serif Display"', 'serif'],
      },
      borderRadius: { DEFAULT: '8px' },
    },
  },
  plugins: [],
};
