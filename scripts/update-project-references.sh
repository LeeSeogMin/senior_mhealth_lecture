#!/bin/bash

# =============================================================================
# Project Reference Update Script
# Updates all references from old project ID to new one
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

echo ""
echo "============================================="
echo "   Project Reference Update Script"
echo "============================================="
echo ""

# Load .env file
if [ -f ".env" ]; then
    source .env
else
    log_error ".env file not found!"
    exit 1
fi

OLD_PROJECT_ID="senior-mhealth-472007"
NEW_PROJECT_ID="${GCP_PROJECT_ID}"

if [ -z "$NEW_PROJECT_ID" ]; then
    log_error "GCP_PROJECT_ID not set in .env file"
    exit 1
fi

log_info "Updating references from $OLD_PROJECT_ID to $NEW_PROJECT_ID"

# =============================================================================
# 1. Update deployment scripts
# =============================================================================
log_step "Updating deployment scripts..."

find . -name "*.sh" -type f -exec grep -l "$OLD_PROJECT_ID" {} \; | while read file; do
    log_info "Updating $file"
    sed -i.bak "s/$OLD_PROJECT_ID/$NEW_PROJECT_ID/g" "$file"
    rm -f "$file.bak"
done

# =============================================================================
# 2. Update configuration files
# =============================================================================
log_step "Updating configuration files..."

# Python files
find . -name "*.py" -type f -exec grep -l "$OLD_PROJECT_ID" {} \; | while read file; do
    log_info "Updating $file"
    sed -i.bak "s/$OLD_PROJECT_ID/$NEW_PROJECT_ID/g" "$file"
    rm -f "$file.bak"
done

# JavaScript/TypeScript files
find . -name "*.js" -name "*.ts" -type f -exec grep -l "$OLD_PROJECT_ID" {} \; | while read file; do
    log_info "Updating $file"
    sed -i.bak "s/$OLD_PROJECT_ID/$NEW_PROJECT_ID/g" "$file"
    rm -f "$file.bak"
done

# YAML files
find . -name "*.yml" -name "*.yaml" -type f -exec grep -l "$OLD_PROJECT_ID" {} \; | while read file; do
    log_info "Updating $file"
    sed -i.bak "s/$OLD_PROJECT_ID/$NEW_PROJECT_ID/g" "$file"
    rm -f "$file.bak"
done

# Markdown files
find . -name "*.md" -type f -exec grep -l "$OLD_PROJECT_ID" {} \; | while read file; do
    log_info "Updating $file"
    sed -i.bak "s/$OLD_PROJECT_ID/$NEW_PROJECT_ID/g" "$file"
    rm -f "$file.bak"
done

# =============================================================================
# 3. Update service account references
# =============================================================================
log_step "Updating service account references..."

# Update email references
OLD_SA_EMAIL="@${OLD_PROJECT_ID}.iam.gserviceaccount.com"
NEW_SA_EMAIL="@${NEW_PROJECT_ID}.iam.gserviceaccount.com"

find . -type f \( -name "*.js" -o -name "*.ts" -o -name "*.py" -o -name "*.sh" \) -exec grep -l "$OLD_SA_EMAIL" {} \; | while read file; do
    log_info "Updating service account emails in $file"
    sed -i.bak "s/$OLD_SA_EMAIL/$NEW_SA_EMAIL/g" "$file"
    rm -f "$file.bak"
done

# =============================================================================
# 4. Update storage bucket references
# =============================================================================
log_step "Updating storage bucket references..."

OLD_BUCKET="${OLD_PROJECT_ID}.firebasestorage.app"
NEW_BUCKET="${NEW_PROJECT_ID}.firebasestorage.app"

find . -type f \( -name "*.js" -o -name "*.ts" -o -name "*.py" \) -exec grep -l "$OLD_BUCKET" {} \; | while read file; do
    log_info "Updating storage bucket in $file"
    sed -i.bak "s/$OLD_BUCKET/$NEW_BUCKET/g" "$file"
    rm -f "$file.bak"
done

OLD_APPSPOT="${OLD_PROJECT_ID}.appspot.com"
NEW_APPSPOT="${NEW_PROJECT_ID}.appspot.com"

find . -type f \( -name "*.js" -o -name "*.ts" -o -name "*.py" \) -exec grep -l "$OLD_APPSPOT" {} \; | while read file; do
    log_info "Updating appspot bucket in $file"
    sed -i.bak "s/$OLD_APPSPOT/$NEW_APPSPOT/g" "$file"
    rm -f "$file.bak"
done

# =============================================================================
# 5. Update web app URLs
# =============================================================================
log_step "Updating web app URLs..."

OLD_WEB_URL="${OLD_PROJECT_ID}.web.app"
NEW_WEB_URL="${NEW_PROJECT_ID}.web.app"

find . -type f \( -name "*.js" -o -name "*.ts" \) -exec grep -l "$OLD_WEB_URL" {} \; | while read file; do
    log_info "Updating web app URL in $file"
    sed -i.bak "s/$OLD_WEB_URL/$NEW_WEB_URL/g" "$file"
    rm -f "$file.bak"
done

OLD_FIREBASE_URL="${OLD_PROJECT_ID}.firebaseapp.com"
NEW_FIREBASE_URL="${NEW_PROJECT_ID}.firebaseapp.com"

find . -type f \( -name "*.js" -o -name "*.ts" \) -exec grep -l "$OLD_FIREBASE_URL" {} \; | while read file; do
    log_info "Updating Firebase app URL in $file"
    sed -i.bak "s/$OLD_FIREBASE_URL/$NEW_FIREBASE_URL/g" "$file"
    rm -f "$file.bak"
done

# =============================================================================
# 6. Update GCR image references
# =============================================================================
log_step "Updating GCR image references..."

OLD_GCR="gcr.io/${OLD_PROJECT_ID}"
NEW_GCR="gcr.io/${NEW_PROJECT_ID}"

find . -type f \( -name "*.sh" -o -name "*.md" -o -name "*.yml" -o -name "*.yaml" \) -exec grep -l "$OLD_GCR" {} \; | while read file; do
    log_info "Updating GCR reference in $file"
    sed -i.bak "s|$OLD_GCR|$NEW_GCR|g" "$file"
    rm -f "$file.bak"
done

# =============================================================================
# 7. Update Cloud SQL references
# =============================================================================
log_step "Updating Cloud SQL references..."

OLD_CLOUD_SQL="${OLD_PROJECT_ID}:asia-northeast3:${OLD_PROJECT_ID}-db"
NEW_CLOUD_SQL="${NEW_PROJECT_ID}:asia-northeast3:${NEW_PROJECT_ID}-db"

find . -type f \( -name "*.js" -o -name "*.ts" \) -exec grep -l "$OLD_CLOUD_SQL" {} \; | while read file; do
    log_info "Updating Cloud SQL reference in $file"
    sed -i.bak "s/$OLD_CLOUD_SQL/$NEW_CLOUD_SQL/g" "$file"
    rm -f "$file.bak"
done

echo ""
echo "============================================="
echo "   Update Complete!"
echo "============================================="
echo ""
log_info "All references updated from $OLD_PROJECT_ID to $NEW_PROJECT_ID"
log_warn "Please review the changes and test the application"
echo ""