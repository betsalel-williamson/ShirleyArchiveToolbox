#!/bin/bash

echo "🚀 Resolving deprecated subdependency warnings..."
git add -A && git commit -m "pre-dependency-update" || echo "No changes to commit, proceeding."

echo
echo "--> Updating all dependencies to their latest versions..."
# The '-L' or '--latest' flag tells pnpm to ignore the ranges in package.json
# and install the latest available version.
pnpm up --latest

echo
echo "✅ package.json has been updated."
echo "Running 'pnpm install' to apply changes and update the lockfile..."
pnpm install

echo
echo "🎉 Dependencies updated successfully!"
echo "The deprecated warnings should now be resolved."
echo "➡️  You can now run 'pnpm run dev' or 'pnpm run build' again."