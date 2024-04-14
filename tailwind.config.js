/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./dashboard/templates/*.html"],
  theme: {
    fontFamily: {
      sans: ['IBM Plex Mono', 'sans-serif'],
      mono: ['IBM Plex Mono', 'monospace'],
    },
    extend: {
      colors: {
        'eggshell': {
          DEFAULT: '#f4f1de',
        },
        'sienna': {
          DEFAULT: '#e07a5f',
        },
        'blue': {
          DEFAULT: '#7a80ba',
        },
      },
    },
  },
  plugins: [],
}
