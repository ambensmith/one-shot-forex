/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        canvas: '#FAFAF9',
        surface: '#FFFFFF',
        primary: '#1C1917',
        secondary: '#57534E',
        tertiary: '#A8A29E',
        inverse: '#FAFAF9',
        brand: {
          DEFAULT: '#4F46E5',
          light: '#EEF2FF',
          hover: '#4338CA',
        },
        border: {
          DEFAULT: '#E7E5E4',
          subtle: '#F5F5F4',
          strong: '#D6D3D1',
        },
        hover: '#F5F5F4',
        active: '#EEEEEC',
        profitable: {
          text: '#15803D',
          accent: '#22C55E',
        },
        loss: {
          text: '#DC2626',
          accent: '#EF4444',
        },
        pending: {
          text: '#B45309',
          accent: '#F59E0B',
        },
        info: {
          text: '#4F46E5',
          accent: '#6366F1',
        },
        cooldown: {
          text: '#64748B',
          accent: '#94A3B8',
        },
      },
      fontFamily: {
        display: ['Fraunces', 'Georgia', 'Times New Roman', 'serif'],
        sans: ['Outfit', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'sans-serif'],
        mono: ['JetBrains Mono', 'SF Mono', 'Fira Code', 'monospace'],
      },
      boxShadow: {
        whisper: '0 1px 3px rgba(0,0,0,0.04), 0 1px 2px rgba(0,0,0,0.02)',
        lifted: '0 4px 16px rgba(0,0,0,0.06), 0 1px 3px rgba(0,0,0,0.04)',
        floating: '0 8px 32px rgba(0,0,0,0.08), 0 2px 8px rgba(0,0,0,0.04)',
        modal: '0 16px 48px rgba(0,0,0,0.12), 0 4px 16px rgba(0,0,0,0.06)',
      },
      maxWidth: {
        content: '1200px',
        narrative: '720px',
      },
      borderRadius: {
        card: '10px',
        pill: '16px',
        button: '8px',
      },
    },
  },
  plugins: [],
}
