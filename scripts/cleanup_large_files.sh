#!/bin/bash
# Cleanup script for large metadata files that are no longer needed
# with the API-first architecture using Semantic Scholar

set -e

echo "🧹 ArXiv Co-Scientist - Large File Cleanup"
echo "=========================================="
echo ""
echo "This script will remove large metadata files that are no longer needed"
echo "with the API-first architecture (Semantic Scholar + Gemini)."
echo ""

# Files to remove
FILES_TO_REMOVE=(
    "data/raw/arxiv.zip"
    "data/raw/arxiv-metadata-oai-snapshot.json"
)

# Check if any files exist
FOUND_FILES=0
for file in "${FILES_TO_REMOVE[@]}"; do
    if [ -f "$file" ]; then
        FOUND_FILES=$((FOUND_FILES + 1))
        SIZE=$(du -h "$file" | cut -f1)
        echo "  ❌ $file ($SIZE)"
    fi
done

if [ $FOUND_FILES -eq 0 ]; then
    echo "✅ No large files found. Already clean!"
    exit 0
fi

echo ""
echo "Total files to remove: $FOUND_FILES"
echo ""

# Calculate total size
TOTAL_SIZE=$(du -ch "${FILES_TO_REMOVE[@]}" 2>/dev/null | tail -1 | cut -f1)
echo "Total space to free: $TOTAL_SIZE"
echo ""

# Confirm deletion
read -p "Do you want to delete these files? (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo "Cancelled. No files deleted."
    exit 0
fi

echo ""
echo "Deleting files..."

for file in "${FILES_TO_REMOVE[@]}"; do
    if [ -f "$file" ]; then
        rm "$file"
        echo "  ✓ Deleted: $file"
    fi
done

echo ""
echo "✅ Cleanup complete!"
echo "Freed $TOTAL_SIZE of storage."
echo ""
echo "The project now uses Semantic Scholar API for metadata."
echo "See README.md for updated usage instructions."
