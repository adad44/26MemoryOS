/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
      },
      colors: {
        ink: '#202124',
        line: '#d7dce2',
        panel: '#f7f8fa',
        moss: '#2f6f5e',
        rust: '#b5532a',
        signal: '#246b8f',
      },
    },
  },
  plugins: [],
};
