import { Config } from 'tailwindcss';
import forms from '@tailwindcss/forms';

const config: Config = {
  mode: "jit",
  content: ["./src/**/**/*.{js,ts,jsx,tsx,html,mdx}", "./src/**/*.{js,ts,jsx,tsx,html,mdx}"],
  darkMode: "class",
  theme: {
    screens: { md: { max: "1050px" }, sm: { max: "550px" } },
    extend: {
      colors: {
        black: { 900: "#090c13", "900_01": "#090c12", "900_07": "#0a0d1407" },
        blue_gray: {
          300: "#99a0ad",
          700: "#525866",
          900: "#202738",
          "900_01": "#282f3f",
          "900_02": "#202632",
          "900_03": "#2c3341",
        },
        gray: {
          500: "#909399",
          600: "#717784",
          800: "#47494e",
          900: "#0e121b",
          "900_01": "#131825",
          "900_02": "#1f2430",
          "900_03": "#1d2330",
          "900_04": "#0c1018",
          "900_05": "#0d111b",
        },
        indigo: { 700: "#253fa7", 900: "#0b1c5d", a200: "#5678ff", a200_01: "#5f7cf2", a400: "#335cff" },
        white: {
          a700: "#fdfdfd",
          a700_01: "#ffffff",
          a700_3f: "#ffffff3f",
          a700_7f: "#fdfdfd7f",
          a700_7f_01: "#ffffff7f",
        },
      },
      boxShadow: { xs: "0 1px 2px 0 #0a0d1407" },
      fontFamily: {
        sans: [
          '-apple-system',
          'BlinkMacSystemFont',
          '"Segoe UI"',
          'Roboto',
          '"Helvetica Neue"',
          'Arial',
          'sans-serif',
        ],
      },
      backgroundImage: { gradient: "radial-gradient(90deg, #5678ff,#253fa7)" },
    },
  },
  plugins: [forms()],
};

export default config;
