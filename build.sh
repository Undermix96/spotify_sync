#!/bin/bash
set -euo pipefail

IMAGE="undermix/spotify_sync"
TAGS=("$@")

# Default to "latest" if no tag provided
if [ ${#TAGS[@]} -eq 0 ]; then
    TAGS=("latest")
fi

echo "🐳 Building Docker image with tags: ${TAGS[*]}"

# Build once with all tags (Docker supports multiple -t flags)
BUILD_TAGS=()
for TAG in "${TAGS[@]}"; do
    BUILD_TAGS+=(-t "${IMAGE}:${TAG}")
done

docker build \
  --build-arg BUILD_DATE="$(date -u +'%Y-%m-%dT%H:%M:%SZ')" \
  --build-arg VCS_REF="$(git rev-parse --short HEAD 2>/dev/null || echo 'dev')" \
  "${BUILD_TAGS[@]}" \
  .

echo "📤 Pushing all tags to Docker Hub..."
for TAG in "${TAGS[@]}"; do
    echo "  → Pushing ${IMAGE}:${TAG}"
    docker push "${IMAGE}:${TAG}"
done

echo "✅ Done: ${TAGS[*]}"
