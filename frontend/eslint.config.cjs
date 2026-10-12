const { createRequire } = require("node:module");
const { existsSync } = require("node:fs");
const { delimiter, join, resolve } = require("node:path");

const eslintExecutable = process.platform === "win32" ? "eslint.cmd" : "eslint";
const eslintBinDirectory = process.env.PATH.split(delimiter).find((entry) =>
  existsSync(join(entry, eslintExecutable)),
);

if (!eslintBinDirectory) {
  throw new Error("ESLint's package directory could not be located.");
}

// npm exec installs the pinned lint packages into a temporary node_modules tree.
const requireLintPackage = createRequire(resolve(eslintBinDirectory, "eslint.config.cjs"));
const typescriptEslint = requireLintPackage("typescript-eslint");

module.exports = [
  { ignores: ["dist/**", "node_modules/**"] },
  {
    files: ["src/**/*.{ts,tsx}"],
    languageOptions: {
      parser: typescriptEslint.parser,
      parserOptions: {
        ecmaFeatures: { jsx: true },
        sourceType: "module",
      },
    },
    plugins: { "@typescript-eslint": typescriptEslint.plugin },
    rules: {
      "no-debugger": "error",
      "no-unreachable": "error",
      "@typescript-eslint/no-unused-vars": ["warn", {
        argsIgnorePattern: "^_",
        varsIgnorePattern: "^_",
      }],
    },
  },
];
