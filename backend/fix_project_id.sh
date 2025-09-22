#!/bin/bash

# Fix Project ID Script - Update all hardcoded project IDs to actual value

OLD_PROJECT_ID="thematic-center-463215-m2"
NEW_PROJECT_ID="senior-mhealth-472007"

echo "Updating project ID from ${OLD_PROJECT_ID} to ${NEW_PROJECT_ID}"

# Python files
find . -type f -name "*.py" -exec sed -i "s/${OLD_PROJECT_ID}/${NEW_PROJECT_ID}/g" {} \;

# TypeScript files
find . -type f -name "*.ts" -exec sed -i "s/${OLD_PROJECT_ID}/${NEW_PROJECT_ID}/g" {} \;

# JavaScript files
find . -type f -name "*.js" -exec sed -i "s/${OLD_PROJECT_ID}/${NEW_PROJECT_ID}/g" {} \;

# Shell scripts
find . -type f -name "*.sh" -exec sed -i "s/${OLD_PROJECT_ID}/${NEW_PROJECT_ID}/g" {} \;

# JSON files
find . -type f -name "*.json" -exec sed -i "s/${OLD_PROJECT_ID}/${NEW_PROJECT_ID}/g" {} \;

# YAML files
find . -type f -name "*.yaml" -exec sed -i "s/${OLD_PROJECT_ID}/${NEW_PROJECT_ID}/g" {} \;
find . -type f -name "*.yml" -exec sed -i "s/${OLD_PROJECT_ID}/${NEW_PROJECT_ID}/g" {} \;

echo "Project ID update completed!"
echo "Please verify the changes and update any service account emails if needed."