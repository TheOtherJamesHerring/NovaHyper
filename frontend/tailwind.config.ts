import type { Config } from 'tailwindcss'

export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      fontFamily: {
        sans:    ['Inter', 'system-ui', 'sans-serif'],
        mono:    ['"IBM Plex Mono"', 'ui-monospace', 'monospace'],
        display: ['Syne', 'sans-serif'],
      },
      colors: {
        /* Dark-theme surfaces */
        dark: {
          bg:      '#0b0d12',
          bg2:     '#12151d',
          bg3:     '#1a1e28',
          surface: '#1f2433',
          border:  'rgba(255,255,255,0.07)',
        },
        accent:  '#4f8ef7',
        success: '#38d9a9',
        nova: {
          warn:   '#f59e0b',
          danger: '#ef4444',
          purple: '#a78bfa',
          blue:   '#4f8ef7',
          green:  '#38d9a9',
        },
      },
      borderColor: {
        dark: 'rgba(255,255,255,0.07)',
      },
    },
  },
  plugins: [],
} satisfies Config
