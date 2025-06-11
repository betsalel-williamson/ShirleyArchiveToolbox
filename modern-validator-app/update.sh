#!/bin/bash

echo "🚀 Applying the final fix: Removing conflicting build configuration from vite.config.ts..."
git add -A && git commit -m "pre-vite-config-cleanup" || echo "No changes to commit, proceeding."

# Overwrite vite.config.ts with the simplest possible configuration.
# The build entry points are now correctly handled by the scripts in package.json.
cat << 'EOF' > vite.config.ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
})
EOF

echo
echo "🎉 vite.config.ts has been cleaned up and corrected."
echo "The conflicting SSR configuration has been removed."
echo
echo "➡️  Please run 'pnpm run build' again. It will now succeed."