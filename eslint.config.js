// Minimal ESLint v9 flat-config for browser JS under static/js
// Docs: https://eslint.org/docs/latest/use/configure/configuration-files-new

import js from "@eslint/js";

export default [
  js.configs.recommended,
  {
    files: ["static/js/**/*.js"],
    languageOptions: {
      ecmaVersion: 2021,
      sourceType: "module",
      globals: {
        window: "readonly",
        document: "readonly",
        console: "readonly",
        // Browser built-ins used in app.js
        fetch: "readonly",
        setTimeout: "readonly",
        clearTimeout: "readonly",
        localStorage: "readonly",
        FormData: "readonly",
        confirm: "readonly",
        // External globals from scripts
        Chart: "readonly",
        bootstrap: "readonly",
      },
    },
    rules: {
      "no-var": "error",
      "prefer-const": "warn",
    },
  },
];


