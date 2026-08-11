const path = require('path');

module.exports = {
  target: 'node',
  entry: './src/index.ts',
  output: {
    path: path.resolve(__dirname, 'dist'),
    filename: 'index.js',
    libraryTarget: 'umd',
  },
  resolve: {
    extensions: ['.ts', '.js'],
  },
  module: {
    rules: [
      {
        test: /\.ts$/,
        use: 'ts-loader',
        exclude: /node_modules/,
      },
      {
        test: /\.svg$/,
        type: 'asset/source',
      },
    ],
  },
  externals: [
    /^@angular\//,
    /^@ng-bootstrap\//,
    /^@popperjs\//,
    /^rxjs/,
    /^tabby-/,
    'fs',
    'path',
    'os',
  ],
};
