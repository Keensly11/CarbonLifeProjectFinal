const { getDefaultConfig } = require('@expo/metro-config');

const config = getDefaultConfig(__dirname);

// Completely disable problematic features
config.transformer = {
  ...config.transformer,
  unstable_allowRequireContext: true,
};

config.resolver.unstable_enablePackageExports = false;
config.resolver.unstable_conditionsByPlatform = {
  ...config.resolver.unstable_conditionsByPlatform,
  ios: ['react-native'],
  android: ['react-native'],
};

module.exports = config;
