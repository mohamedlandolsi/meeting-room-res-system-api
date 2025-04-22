#!/bin/bash
# Script to build Docker images for Kubernetes deployment

set -e  # Exit on any error

# Set the registry - use gcr.io/PROJECT_ID format for Google Container Registry
# Default to mohamedlandolsi if no project ID is provided
PROJECT_ID=${1:-mohamedlandolsi}
REGISTRY="gcr.io/${PROJECT_ID}"

# Service names and their respective directories
SERVICES=("user-service" "room-service" "reservation-service")

echo "Building images with registry prefix: $REGISTRY"

# Build and tag each service
for SERVICE in "${SERVICES[@]}"; do
  echo "Building $SERVICE..."
  
  # Build the image
  docker build -t $REGISTRY/$SERVICE:latest $SERVICE
  
  # Tag with date for versioning
  DATE_TAG=$(date +%Y%m%d-%H%M)
  docker tag $REGISTRY/$SERVICE:latest $REGISTRY/$SERVICE:$DATE_TAG
  
  echo "Successfully built $SERVICE - Tagged as $REGISTRY/$SERVICE:latest and $REGISTRY/$SERVICE:$DATE_TAG"
done

echo "All images built successfully!"

echo "To push these images to Google Container Registry, run:"
echo "gcloud auth configure-docker"
echo "docker push [image_name]"