module.exports = {
  "presets": [
    ["@babel/preset-env", { "targets": { "node": "current" } }],
    ["@babel/preset-react"],
    ["@babel/preset-typescript"]
  ],
  "plugins": [
    ["@babel/plugin-transform-runtime", { "regenerator": true }],
    ["@babel/plugin-proposal-class-properties"],
    ["module-resolver", {
      "root": ["./src"],
      "alias": {
        "@/components": "./src/client/components",
        "@/views": "./src/client/views",
        "@/utils": "./src/utils",
        "@/api": "./src/api",
        "@/db": "./src/db",
        "@/data": "./src/data"
      }
    }]
  ]
};
