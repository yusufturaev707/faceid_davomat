/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  darkMode: "class",
  theme: {
    screens: {
      xs: "420px",
      sm: "640px",
      md: "768px",
      lg: "1024px",
      xl: "1280px",
      "2xl": "1536px",
    },
    extend: {
      colors: {
        primary: {
          50: "rgb(var(--color-primary-50) / <alpha-value>)",
          100: "rgb(var(--color-primary-100) / <alpha-value>)",
          200: "rgb(var(--color-primary-200) / <alpha-value>)",
          300: "rgb(var(--color-primary-300) / <alpha-value>)",
          400: "rgb(var(--color-primary-400) / <alpha-value>)",
          500: "rgb(var(--color-primary-500) / <alpha-value>)",
          600: "rgb(var(--color-primary-600) / <alpha-value>)",
          700: "rgb(var(--color-primary-700) / <alpha-value>)",
          800: "rgb(var(--color-primary-800) / <alpha-value>)",
          900: "rgb(var(--color-primary-900) / <alpha-value>)",
        },
        surface: {
          DEFAULT: "rgb(var(--color-surface) / <alpha-value>)",
          secondary: "rgb(var(--color-surface-secondary) / <alpha-value>)",
        },
      },
      boxShadow: {
        // Legacy
        card: "0 1px 3px 0 rgb(0 0 0 / 0.04), 0 1px 2px -1px rgb(0 0 0 / 0.04)",
        "card-hover":
          "0 4px 6px -1px rgb(0 0 0 / 0.07), 0 2px 4px -2px rgb(0 0 0 / 0.05)",
        elevated:
          "0 10px 15px -3px rgb(0 0 0 / 0.08), 0 4px 6px -4px rgb(0 0 0 / 0.04)",
        // Material Design 3 elevations
        "md-1": "0 1px 2px 0 rgb(0 0 0 / 0.05), 0 1px 3px 1px rgb(0 0 0 / 0.04)",
        "md-2": "0 1px 2px 0 rgb(0 0 0 / 0.06), 0 2px 6px 2px rgb(0 0 0 / 0.06)",
        "md-3": "0 4px 8px 3px rgb(0 0 0 / 0.05), 0 1px 3px 0 rgb(0 0 0 / 0.08)",
        "md-4": "0 6px 10px 4px rgb(0 0 0 / 0.06), 0 2px 3px 0 rgb(0 0 0 / 0.09)",
        "md-5": "0 8px 12px 6px rgb(0 0 0 / 0.08), 0 4px 4px 0 rgb(0 0 0 / 0.10)",
      },
      borderRadius: {
        "4xl": "2rem",
      },
      transitionTimingFunction: {
        "md-standard": "cubic-bezier(0.2, 0, 0, 1)",
        "md-emphasized": "cubic-bezier(0.3, 0, 0, 1)",
      },
      maxWidth: {
        "8xl": "88rem",
      },
    },
  },
  plugins: [],
};
