'use strict';
const path = require('path');
const TerserPlugin = require("terser-webpack-plugin");
const MiniCssExtractPlugin = require('mini-css-extract-plugin');
const CssMinimizerPlugin = require("css-minimizer-webpack-plugin");
const { CleanWebpackPlugin } = require('clean-webpack-plugin');

const devMode = process.env.NODE_ENV !== 'production';

module.exports = {
  devtool: devMode ? 'source-map' : false,
  mode: devMode ? 'development' : 'production',
  entry: {
    'app': './src/client/client.tsx',
    'app.min': './src/client/client.tsx'
  },
  output: {
    path: path.resolve(__dirname, './dist/js'),
    filename: '[name].js'
  },
  resolve: {
    // THIS IS THE FIX: Tell Webpack to try these extensions when resolving modules
    extensions: ['.ts', '.tsx', '.js', '.jsx', '.scss'],
    alias: {
      '@/components': path.resolve(__dirname, './src/client/components'),
      '@/views': path.resolve(__dirname, './src/client/views'),
      '@/utils': path.resolve(__dirname, './src/utils'),
    }
  },
  optimization: {
    minimize: true,
    minimizer: [
      new TerserPlugin({ test: /\.min\.js$/i }),
      new MiniCssExtractPlugin({ filename: '../css/[name].css' }),
      new CssMinimizerPlugin({ test: /\.min\.css$/i }),
    ],
  },
  module: {
    rules: [
      {
        test: /\.(js|jsx|ts|tsx)$/,
        loader: 'babel-loader',
        exclude: /node_modules/,
      },
      {
        test: /\.(sa|sc|c)ss$/,
        use: [
          MiniCssExtractPlugin.loader,
          { loader: "css-loader", options: { sourceMap: true } },
          { loader: 'sass-loader', options: { sourceMap: true } },
        ]
      },
      {
        test: /\.(png|jpe?g|gif|ttf|eot|svg|woff(2)?)(\?[a-z0-9=&.]+)?$/,
        loader: 'file-loader',
        options: {
          outputPath: '../images/',
          name: '[name].[ext]'
        }
      }
    ],
  },
  plugins: [
    new CleanWebpackPlugin({
      cleanOnceBeforeBuildPatterns: [
          path.join(__dirname, 'dist/js/*'),
          path.join(__dirname, 'dist/css/*')
      ],
    }),
  ]
};
