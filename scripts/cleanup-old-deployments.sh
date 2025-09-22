#!/bin/bash

# Senior MHealth - Clean up old deployment artifacts
# Keeps only the latest versions to save storage and costs

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}🧹 Starting cleanup of old deployment artifacts${NC}"

# Configuration
PROJECT_ID="senior-mhealth-472007"
REGION="asia-northeast3"
KEEP_REVISIONS=3  # Number of revisions to keep for each service

# Function to clean old container images
cleanup_gcr_images() {
    local repository=$1
    local keep_count=$2

    echo -e "${YELLOW}Cleaning ${repository}...${NC}"

    # Get all image digests sorted by timestamp (oldest first)
    digests=$(gcloud container images list-tags ${repository} \
        --limit=999 \
        --sort-by=~timestamp \
        --format="get(digest)" | tail -n +$((keep_count + 1)))

    if [ -z "$digests" ]; then
        echo "No old images to delete in ${repository}"
        return
    fi

    # Delete old images
    for digest in $digests; do
        echo "Deleting ${repository}@${digest}"
        gcloud container images delete "${repository}@${digest}" --quiet --force-delete-tags || true
    done
}

# Function to clean old Cloud Run revisions
cleanup_cloud_run_revisions() {
    local service=$1
    local keep_count=$2

    echo -e "${YELLOW}Cleaning revisions for ${service}...${NC}"

    # Get all revisions except the latest ones
    revisions=$(gcloud run revisions list \
        --service=${service} \
        --region=${REGION} \
        --format="value(name)" \
        --sort-by=~creationTimestamp | tail -n +$((keep_count + 1)))

    if [ -z "$revisions" ]; then
        echo "No old revisions to delete for ${service}"
        return
    fi

    # Delete old revisions
    for revision in $revisions; do
        echo "Deleting revision ${revision}"
        gcloud run revisions delete ${revision} --region=${REGION} --quiet || true
    done
}

# Function to clean Artifact Registry images
cleanup_artifact_registry() {
    local repository=$1
    local location=$2

    echo -e "${YELLOW}Cleaning Artifact Registry ${repository}...${NC}"

    # List all images and keep only the latest version of each
    images=$(gcloud artifacts docker images list \
        ${location}-docker.pkg.dev/${PROJECT_ID}/${repository} \
        --include-tags \
        --format="value(IMAGE)" | sort -u)

    for image in $images; do
        # Get all versions except the latest
        versions=$(gcloud artifacts docker images list \
            ${image} \
            --include-tags \
            --sort-by=~createTime \
            --format="value(VERSION)" | tail -n +2)

        for version in $versions; do
            if [ ! -z "$version" ]; then
                echo "Deleting ${image}:${version}"
                gcloud artifacts docker images delete \
                    "${image}:${version}" \
                    --delete-tags \
                    --quiet || true
            fi
        done
    done
}

# 1. Clean GCR Images
echo -e "${GREEN}📦 Cleaning Container Registry images...${NC}"
cleanup_gcr_images "gcr.io/${PROJECT_ID}/ai-service" 2
cleanup_gcr_images "gcr.io/${PROJECT_ID}/senior-mhealth-api" 3

# 2. Clean Cloud Run Revisions
echo -e "${GREEN}☁️ Cleaning Cloud Run revisions...${NC}"
cleanup_cloud_run_revisions "senior-mhealth-ai" ${KEEP_REVISIONS}
cleanup_cloud_run_revisions "senior-mhealth-api" ${KEEP_REVISIONS}

# Also clean Firebase Functions Cloud Run services
for func in analyzehealthdata cleanuptestfcmtokens cleanusertesttokens generatemonthlyreports monitorcallstatus oncallrecordinguploaded processvoiceupload registerfcmtoken sendfcmonanalysiscomplete; do
    cleanup_cloud_run_revisions ${func} 2
done

# 3. Clean Artifact Registry
echo -e "${GREEN}🗄️ Cleaning Artifact Registry...${NC}"
cleanup_artifact_registry "ai-service" "asia-northeast3"
cleanup_artifact_registry "cloud-run-source-deploy" "asia-northeast3"

# 4. Clean unused Cloud Storage buckets
echo -e "${GREEN}🪣 Checking Cloud Storage buckets...${NC}"
# List all buckets and their sizes
gsutil du -sh gs://${PROJECT_ID}* 2>/dev/null || true

# 5. Summary
echo -e "${GREEN}✅ Cleanup completed!${NC}"
echo -e "${YELLOW}📊 Current resource usage:${NC}"

# Show remaining images
echo -e "\n${YELLOW}Container Registry:${NC}"
gcloud container images list --repository=gcr.io/${PROJECT_ID} --format="table(name)"

# Show remaining revisions
echo -e "\n${YELLOW}Cloud Run services:${NC}"
gcloud run services list --region=${REGION} --format="table(SERVICE:label=SERVICE,LAST_DEPLOYED:label=DEPLOYED)"

echo -e "\n${GREEN}💡 Tip: Run this script monthly to keep costs down${NC}"