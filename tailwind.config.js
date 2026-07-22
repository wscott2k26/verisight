/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        base: '#05070F',
        card: '#0C1020',
        border: '#1E293B',
        cyan: {
          neon: '#00F0FF',
        },
        magenta: {
          neon: '#FF007A',
        },
        green: {
          neon: '#39FF14',
        },
      },
      keyframes: {
        scanline: {
          '0%, 100%': { transform: 'translateY(0%)' },
          '50%': { transform: 'translateY(calc(260px - 100%))' },
        },
      },
      animation: {
        scanline: 'scanline 2.4s ease-in-out infinite',
      },
    },
  },
  plugins: [],
}
