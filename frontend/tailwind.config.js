/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        surface: "#fcfcfc",
        card: "#ffffff",
        subtle: "#f4f4f5",
        border: "#e4e4e7",
        charcoal: {
          900: "#09090b",
          800: "#18181b",
          700: "#27272a",
          500: "#71717a",
          400: "#a1a1aa",
          300: "#d4d4d8",
          100: "#f4f4f5",
        },
        brand: {
          DEFAULT: "#09090b",
          blue: "#2563eb",
          emerald: "#059669",
          amber: "#d97706",
        }
      },
      fontFamily: {
        sans: ['-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
        mono: ['ui-monospace', 'SFMono-Regular', 'Menlo', 'Monaco', 'Consolas', 'monospace'],
      }
    },
  },
  plugins: [],
}
