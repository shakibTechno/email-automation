module.exports = {
  root: true,
  env: { browser: true, es2020: true },
  extends: [
    'eslint:recommended',
    'plugin:@typescript-eslint/recommended',
    'plugin:react-hooks/recommended',
  ],
  ignorePatterns: ['dist', '.eslintrc.cjs'],
  parser: '@typescript-eslint/parser',
  plugins: ['react-refresh'],
  rules: {
    'react-refresh/only-export-components': [
      'warn',
      { allowConstantExport: true },
    ],
    '@typescript-eslint/no-explicit-any': 'off',

    // Radix's Select reserves the empty string for a cleared value and throws
    // "A <Select.Item /> must have a value prop that is not an empty string"
    // when an item uses it. That is a render-time crash, not a warning, so the
    // whole dialog containing it dies — which is how "add a sequence step" came
    // to do nothing at all, silently, in four separate files. Use a sentinel
    // such as '__none' and map it back when reading the value.
    'no-restricted-syntax': [
      'error',
      {
        selector:
          'JSXElement[openingElement.name.name="SelectItem"] > JSXOpeningElement > JSXAttribute[name.name="value"][value.value=""]',
        message:
          'SelectItem cannot have value="" — Radix throws and the dialog crashes. Use a sentinel like \'__none\' and map it back in onValueChange.',
      },
    ],
  },
}
