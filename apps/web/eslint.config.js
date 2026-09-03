import js from "@eslint/js";
import reactHooks from "eslint-plugin-react-hooks";
import tseslint from "typescript-eslint";

export default tseslint.config(
  { ignores: ["dist/**"] },
  js.configs.recommended,
  tseslint.configs.recommended,
  reactHooks.configs.flat["recommended-latest"],
  {
    files: ["**/*.{ts,tsx}"],
    languageOptions: {
      parserOptions: { ecmaFeatures: { jsx: true } },
    },
  },
);
