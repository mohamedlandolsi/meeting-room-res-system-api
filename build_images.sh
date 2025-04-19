#!/bin/bash
# Script to build Docker images for Kubernetes deployment

set -e  # Exit on any error

# Set the registry - use localhost:5000 for local testing or your Docker Hub username
REGISTRY=${1:-localhost:5000}

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

# Uncomment to push images to registry
# echo "Pushing images to registry..."
# for SERVICE in "${SERVICES[@]}"; do
#   echo "Pushing $SERVICE..."
#   docker push $REGISTRY/$SERVICE:latest
#   docker push $REGISTRY/$SERVICE:$(date +%Y%m%d-%H%M)
# done
# echo "All images pushed to registry!"

echo "To push these images to your registry, uncomment the push commands in this script"
echo "or run: docker push [image_name]"