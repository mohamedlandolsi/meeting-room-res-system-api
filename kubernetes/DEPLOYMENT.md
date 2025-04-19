# Kubernetes Deployment Guide

This guide explains how to deploy the Meeting Room Reservation System to a Kubernetes cluster. The system consists of multiple microservices, PostgreSQL database, Kafka for messaging, and an NGINX load balancer.

## Prerequisites

- A running Kubernetes cluster (minikube, kind, or any cloud provider)
- kubectl installed and configured to connect to your cluster
- Container registry access (Docker Hub or private registry)

## Prepare for Deployment

1. Build and push Docker images:

```bash
# Build images using the script
./build_images.sh yourusername # For Docker Hub
# OR for local registry:
./build_images.sh localhost:5000 # For local registry

# Uncomment the push lines in the script or push manually:
# docker push yourusername/user-service:latest
```

2. Update Kubernetes configurations:

If you're using your own container registry, update the image paths in the Kubernetes YAML files:

```bash
# Using sed to update all YAML files
sed -i 's|image: user-service:latest|image: yourusername/user-service:latest|g' kubernetes/microservices/user-service.yaml
sed -i 's|image: room-service:latest|image: yourusername/room-service:latest|g' kubernetes/microservices/room-service.yaml
sed -i 's|image: reservation-service:latest|image: yourusername/reservation-service:latest|g' kubernetes/microservices/reservation-service.yaml
```

3. Update ConfigMap values in `kubernetes/microservices/config.yaml`:
   - Set a secure JWT secret key
   - Set appropriate DEBUG value for production (False)

## Deployment Steps

1. Create the namespace:

```bash
kubectl apply -f kubernetes/namespace.yaml
```

2. Deploy PostgreSQL database:

```bash
kubectl apply -f kubernetes/database/postgres.yaml
```

3. Deploy Kafka and Zookeeper:

```bash
kubectl apply -f kubernetes/kafka/kafka.yaml
```

4. Deploy the application ConfigMap:

```bash
kubectl apply -f kubernetes/microservices/config.yaml
```

5. Deploy the microservices:

```bash
kubectl apply -f kubernetes/microservices/user-service.yaml
kubectl apply -f kubernetes/microservices/room-service.yaml
kubectl apply -f kubernetes/microservices/reservation-service.yaml
```

6. Deploy NGINX:

```bash
kubectl apply -f kubernetes/nginx/nginx.yaml
```

## Verify Deployment

1. Check if all pods are running:

```bash
kubectl get pods -n meeting-room-system
```

2. Check services:

```bash
kubectl get services -n meeting-room-system
```

3. Get the external IP or port for NGINX:

```bash
kubectl get service nginx -n meeting-room-system
```

For minikube, you may need to run:
```bash
minikube service nginx -n meeting-room-system
```

## Accessing the Application

Once deployed, you can access the API at:

```
http://<EXTERNAL-IP>/auth/google/login
```

Replace `<EXTERNAL-IP>` with the actual external IP of your NGINX service.

## Scaling Services

To scale any microservice, use:

```bash
kubectl scale deployment user-service -n meeting-room-system --replicas=3
```

## Troubleshooting

1. Check pod logs:

```bash
kubectl logs -f pod/pod-name -n meeting-room-system
```

2. Check pod details:

```bash
kubectl describe pod pod-name -n meeting-room-system
```

3. Database initialization issues:
   - Make sure the PostgreSQL pod is running before the microservices
   - Check if databases are created automatically

4. Kafka connection issues:
   - Verify Kafka and Zookeeper pods are running
   - Check Kafka connection logs in the reservation-service

## Cleanup

To remove all resources:

```bash
kubectl delete namespace meeting-room-system
```