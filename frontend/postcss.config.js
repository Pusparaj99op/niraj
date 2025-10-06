export default {
  plugins: {
    '@tailwindcss/postcss': {},
    autoprefixer: {
      overrideBrowserslist: [
        '> 0.5%',
        'last 2 versions',
        'Firefox ESR',
        'not dead',
        'not IE 11',
        'not op_mini all'
      ],
      flexbox: 'no-2009',
      grid: 'autoplace'
    },
  },
}
