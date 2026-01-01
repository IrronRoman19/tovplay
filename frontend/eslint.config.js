// eslint.config.js

import js from "@eslint/js";
import stylistic from "@stylistic/eslint-plugin";
import pluginImport from "eslint-plugin-import";
import pluginReact from "eslint-plugin-react";
import pluginReactRefresh from "eslint-plugin-react-refresh";
import pluginUnusedImports from "eslint-plugin-unused-imports";
import globals from "globals";

export default [
  // Global ignores
  {
    ignores: ["dist", "node_modules", "cypress/**/*"]
  },

  // Base ESLint recommended config
  js.configs.recommended,

  // Main configuration for your React source code
  {
    files: ["src/**/*.{js,jsx}", "src/**/*.test.{js,jsx}", "*.config.js"],
    plugins: {
      react: pluginReact,
      "react-refresh": pluginReactRefresh,
      "unused-imports": pluginUnusedImports,
      "@stylistic": stylistic,
      import: pluginImport
    },
    languageOptions: {
      ecmaVersion: "latest",
      sourceType: "module",
      globals: {
        ...globals.browser,
        ...globals.node
      },
      parserOptions: {
        ecmaFeatures: { jsx: true }
      }
    },
    // Add this settings block
    settings: {
      react: {
        version: "detect" // Automatically detects the React version
      }
    },
    rules: {
      // Spread rules from React's recommended configs
      ...pluginReact.configs.recommended.rules,
      ...pluginReact.configs["jsx-runtime"].rules,

      // Your custom rules and overrides go here
      "react-refresh/only-export-components": [
        "error",
        { allowConstantExport: true }
      ],
      "react/prop-types": "error", // Good practice to turn off if using TypeScript/not using prop-types
      "@stylistic/object-curly-newline": [
        "error",
        {
          ImportDeclaration: { multiline: true }
        }
      ],
      "no-unused-vars": ["error", { argsIgnorePattern: "^_" }],
      "@stylistic/padding-line-between-statements": [
        "error",
        { blankLine: "always", prev: "if", next: "if" }
      ],
      "react/jsx-uses-vars": "error",
      "react/no-unescaped-entities": "off",
      "@stylistic/indent": [
        "error",
        2,
        {
          SwitchCase: 1
        }
      ],
      curly: ["error", "all"],
      "prefer-const": "error",
      "@stylistic/arrow-parens": ["error", "as-needed"],
      "@stylistic/array-element-newline": ["error", "consistent"],
      "import/order": [
        "error",
        { groups: ["external", "internal"], alphabetize: { order: "asc" } }
      ],
      "@stylistic/brace-style": "error",
      "@stylistic/object-curly-spacing": ["error", "always"],
      "@stylistic/semi": "error",
      "@stylistic/comma-dangle": ["error", "never"],
      "@stylistic/quotes": [
        "error",
        "double",
        {
          allowTemplateLiterals: "always",
          avoidEscape: true
        }
      ],

      // Let the plugin handle unused imports and variables
      "unused-imports/no-unused-imports": "error",
      "unused-imports/no-unused-vars": [
        "error",
        {
          vars: "all",
          varsIgnorePattern: "^_",
          args: "after-used",
          argsIgnorePattern: "^_"
        }
      ]
    }
  }
];
