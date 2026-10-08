import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}"
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: "#0f4c5c",
          foreground: "#ffffff"
        },
        secondary: {
          DEFAULT: "#1f6f7d",
          foreground: "#ffffff"
        },
        accent: {
          DEFAULT: "#dcefee",
          foreground: "#12343d"
        },
        muted: {
          DEFAULT: "#edf4f6",
          foreground: "#324750"
        }
      }
    }
  },
  plugins: []
};

export default config;
