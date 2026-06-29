/** @type {import('tailwindcss').Config} */

// Build a color from a "R G B" CSS variable so Tailwind can inject opacity.
const v = (name) => `rgb(var(${name}) / <alpha-value>)`;

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        brand: { DEFAULT: v("--c-primary"), 2: v("--c-primary-2"), fg: v("--c-primary-fg") },
        accent: { DEFAULT: v("--c-accent"), strong: v("--c-accent-strong"), fg: v("--c-accent-fg") },
        bg: v("--c-bg"),
        surface: v("--c-surface"),
        "surface-2": v("--c-surface-2"),
        elevated: v("--c-elevated"),
        line: v("--c-border"),
        "line-strong": v("--c-border-strong"),
        ink: v("--c-text"),
        muted: v("--c-text-muted"),
        success: v("--c-success"),
        danger: v("--c-danger"),
        warning: v("--c-warning"),
        info: v("--c-info"),
      },
      fontFamily: {
        sans: ['"Geist Variable"', "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ['"Geist Mono Variable"', "ui-monospace", "SFMono-Regular", "monospace"],
      },
      borderRadius: {
        sm: "8px",
        DEFAULT: "10px",
        lg: "10px",
        xl: "14px",
        "2xl": "18px",
      },
      boxShadow: {
        xs: "0 1px 2px rgb(var(--shadow-color) / 0.06)",
        card: "0 1px 2px rgb(var(--shadow-color) / 0.05), 0 1px 3px rgb(var(--shadow-color) / 0.05)",
        pop: "0 8px 24px -8px rgb(var(--shadow-color) / 0.18), 0 2px 6px rgb(var(--shadow-color) / 0.08)",
      },
      fontSize: {
        "2xs": ["0.6875rem", { lineHeight: "1rem" }],
      },
      keyframes: {
        "fade-in": { from: { opacity: "0", transform: "translateY(4px)" }, to: { opacity: "1", transform: "translateY(0)" } },
        shimmer: { "100%": { transform: "translateX(100%)" } },
      },
      animation: {
        "fade-in": "fade-in 0.2s cubic-bezier(0.16,1,0.3,1)",
      },
    },
  },
  plugins: [],
};
