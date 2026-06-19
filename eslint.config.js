// ============================================================
// ESLint flat config (ESLint v9+)
// ============================================================
import js from '@eslint/js';
import globals from 'globals';

export default [
  // Recommended baseline
  js.configs.recommended,

  {
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: 'module',
      globals: {
        ...globals.browser,
        ...globals.node,
        // Project-specific globals
        appIcons: 'readonly',
        toast: 'readonly',
        markdown: 'readonly',
        Chart: 'readonly',
      },
    },
    rules: {
      // Project style
      'no-var': 'error',
      'prefer-const': 'warn',
      'prefer-arrow-callback': 'warn',
      'prefer-template': 'warn',
      'object-shorthand': ['warn', 'always'],
      'no-console': ['warn', { allow: ['warn', 'error', 'info'] }],
      'no-debugger': 'error',
      'no-unused-vars': [
        'warn',
        {
          argsIgnorePattern: '^_',
          varsIgnorePattern: '^_',
          caughtErrorsIgnorePattern: '^_',
        },
      ],
      'no-empty': ['error', { allowEmptyCatch: true }],
      'no-eval': 'error',
      'no-implied-eval': 'error',
      eqeqeq: ['error', 'always', { null: 'ignore' }],
      'no-multi-spaces': ['warn', { ignoreEOLComments: true }],
      'no-trailing-spaces': 'warn',
      // comma-dangle disabled — owned by Prettier (prettierrc trailingComma)
      'arrow-body-style': ['warn', 'as-needed'],
      curly: ['error', 'multi-line'],
    },
  },

  // Ignore patterns
  {
    ignores: [
      'node_modules/**',
      'static/**/lib/**',
      'summaries/**',
      'uploads/**',
      'logs/**',
      'venv/**',
      '__pycache__/**',
      '.venv/**',
      'build/**',
      'dist/**',
      'static/css/**/*.css', // CSS linted separately if desired
    ],
  },

  // File-specific overrides
  {
    files: ['static/js/icons.js', 'static/js/toast.js'],
    rules: {
      // IIFE wrappers are intentional for global exports
      'no-implicit-globals': 'off',
    },
  },
];