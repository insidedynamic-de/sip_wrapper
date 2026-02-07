#!/bin/bash
#
# Build Docker image with version info
#
# Usage:
#   ./build-docker.sh                    # Build with auto-detected version
#   ./build-docker.sh 1.2.3              # Build with specific version
#   ./build-docker.sh 1.2.3 my-registry  # Build and tag for registry
#

set -e

# Get version from argument or VERSION file
VERSION="${1:-$(cat VERSION 2>/dev/null || echo 'dev')}"
REGISTRY="${2:-}"
GIT_COMMIT=$(git rev-parse --short HEAD 2>/dev/null || echo 'unknown')
BUILD_DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

IMAGE_NAME="insidedynamic-wrapper"

echo "Building Docker image..."
echo "  Version:    ${VERSION}"
echo "  Git Commit: ${GIT_COMMIT}"
echo "  Build Date: ${BUILD_DATE}"
echo ""

# Build with version args
docker build \
  --build-arg VERSION="${VERSION}" \
  --build-arg GIT_COMMIT="${GIT_COMMIT}" \
  --build-arg BUILD_DATE="${BUILD_DATE}" \
  -t "${IMAGE_NAME}:${VERSION}" \
  -t "${IMAGE_NAME}:latest" \
  -f Dockerfile.coolify \
  .

echo ""
echo "Built: ${IMAGE_NAME}:${VERSION}"
echo "Built: ${IMAGE_NAME}:latest"

# Tag for registry if specified
if [ -n "$REGISTRY" ]; then
  docker tag "${IMAGE_NAME}:${VERSION}" "${REGISTRY}/${IMAGE_NAME}:${VERSION}"
  docker tag "${IMAGE_NAME}:latest" "${REGISTRY}/${IMAGE_NAME}:latest"
  echo "Tagged: ${REGISTRY}/${IMAGE_NAME}:${VERSION}"
  echo "Tagged: ${REGISTRY}/${IMAGE_NAME}:latest"
fi
