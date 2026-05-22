#!/bin/bash
set -euo pipefail

IMAGE="undermix/spotify_sync"
TAG="${1:-latest}"

echo "🔨 Building frontend..."
cd frontend
yarn install --frozen-lockfile
yarn build
cd ..

echo "🐳 Building Docker image: ${IMAGE}:${TAG}"
docker build \
  --build-arg BUILD_DATE="$(date -u +'%Y-%m-%dT%H:%M:%SZ')" \
  --build-arg VCS_REF="$(git rev-parse --short HEAD 2>/dev/null || echo 'dev')" \
  -t "${IMAGE}:${TAG}" \
  .

echo "📤 Pushing to Docker Hub..."
docker push "${IMAGE}:${TAG}"

echo "✅ Done: ${IMAGE}:${TAG}"