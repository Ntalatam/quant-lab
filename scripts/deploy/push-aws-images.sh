#!/usr/bin/env bash

set -euo pipefail

if [[ $# -lt 3 ]]; then
  echo "Usage: $0 <aws-region> <frontend-ecr-url> <backend-ecr-url> [image-tag]"
  echo "Example: $0 us-east-1 123456789012.dkr.ecr.us-east-1.amazonaws.com/quantlab-production/frontend 123456789012.dkr.ecr.us-east-1.amazonaws.com/quantlab-production/backend 2026-04-04"
  exit 1
fi

AWS_REGION="$1"
FRONTEND_REPO="$2"
BACKEND_REPO="$3"
IMAGE_TAG="${4:-$(date +%F)}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

echo "Logging into Amazon ECR in ${AWS_REGION}..."
aws ecr get-login-password --region "${AWS_REGION}" | docker login --username AWS --password-stdin "$(dirname "${FRONTEND_REPO}")"

echo "Building frontend image with NEXT_PUBLIC_API_URL=/api..."
docker build \
  --build-arg NEXT_PUBLIC_API_URL=/api \
  -t "${FRONTEND_REPO}:${IMAGE_TAG}" \
  "${REPO_ROOT}/frontend"

echo "Pushing frontend image ${FRONTEND_REPO}:${IMAGE_TAG}..."
docker push "${FRONTEND_REPO}:${IMAGE_TAG}"

echo "Building backend image..."
docker build \
  -t "${BACKEND_REPO}:${IMAGE_TAG}" \
  "${REPO_ROOT}/backend"

echo "Pushing backend image ${BACKEND_REPO}:${IMAGE_TAG}..."
docker push "${BACKEND_REPO}:${IMAGE_TAG}"

cat <<EOF

Images pushed successfully.
Use these Terraform variables for deployment:
  frontend_image_tag = "${IMAGE_TAG}"
  backend_image_tag  = "${IMAGE_TAG}"
EOF
