// This file is now very simple. It just registers babel to transpile the rest of the server code.
require('@babel/register')({
    presets: ['@babel/preset-env', '@babel/preset-react', '@babel/preset-typescript'],
    extensions: ['.js', '.jsx', '.ts', '.tsx'],
});
require('ignore-styles'); // Ignore CSS/SCSS imports on the server

module.exports = require('./app.ts');
