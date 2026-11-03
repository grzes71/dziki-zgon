/** @type {import('tailwindcss').Config} */
export default {
  content: ['./src/**/*.{astro,html,js,jsx,md,mdx,svelte,ts,tsx,vue}'],
  theme: {
    extend: {
      colors: {
        atari: {
          darkest: '#080a08',
          dark: '#0e120f',
          surface: '#151b16',
          panel: '#1b231c',
          border: '#2e3d30',
          borderLight: '#475d4a',
          gold: '#d89b34',
          goldBright: '#f7b946',
          goldMuted: '#946f25',
          green: '#4ea059',
          greenBright: '#6cd37a',
          greenSwamp: '#2c4b31',
          crimson: '#a33333',
          crimsonBright: '#df4848',
          blueCyan: '#3a7d99',
          parchment: '#ded8c5',
          parchmentMuted: '#9e9987',
        }
      },
      fontFamily: {
        mono: ['"Courier New"', 'Courier', 'Consolas', 'monospace'],
        pixel: ['"Courier New"', 'Consolas', 'monospace']
      },
      boxShadow: {
        'pixel': '2px 2px 0px 0px rgba(0, 0, 0, 0.8)',
        'pixel-gold': '2px 2px 0px 0px #946f25',
        'pixel-border': 'inset -2px -2px 0px 0px #151b16, inset 2px 2px 0px 0px #475d4a',
        'crt-glow': '0 0 15px rgba(108, 211, 122, 0.15)',
      }
    },
  },
  plugins: [],
};

