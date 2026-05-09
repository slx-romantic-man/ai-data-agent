module.exports = {
  root: true,
  env: {
    browser: true,
    es2022: true,
  },
  extends: [
    "eslint:recommended",
  ],
  parserOptions: {
    ecmaVersion: "latest",
    sourceType: "module",
  },
  globals: {
    Vue: "readonly",
    axios: "readonly",
    Chart: "readonly",
    marked: "readonly",
    DOMPurify: "readonly",
    morphdom: "readonly",
    tailwindcss: "readonly",
  },
  rules: {
    "no-unused-vars": ["warn", { argsIgnorePattern: "^_" }],
    "no-console": ["warn", { allow: ["warn", "error"] }],
    "eqeqeq": ["error", "always"],
    "curly": ["error", "all"],
  },
};
