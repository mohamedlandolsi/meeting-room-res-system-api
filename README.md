# Meeting Room Reservation System API

A microservice-based meeting room reservation system for managing meeting spaces, bookings, and user accounts.

## Architecture

This system is composed of three microservices:

- **User Service**: Handles authentication and user management
- **Room Service**: Manages room resources and their attributes
- **Reservation Service**: Handles room booking and availability

### Technology Stack

- **Backend**: Python Flask
- **Database**: PostgreSQL
- **Message Broker**: Apache Kafka
- **Authentication**: OAuth 2.0 with JWT
- **Containerization**: Docker
- **Orchestration**: Kubernetes

## CI/CD Pipeline Automation

This project features a comprehensive CI/CD pipeline using GitHub Actions and Helm for automated testing, building, and deployment to Kubernetes environments.

### GitHub Actions Workflow Overview

Our CI/CD pipeline (implemented in `.github/workflows/cicd.yml`) automates the following stages:

1. **Testing**: Runs automated tests for all microservices
2. **Building**: Builds Docker images for each microservice
3. **Publishing**: Pushes images to Docker Hub with version tags
4. **Deployment**: Deploys the application to Kubernetes using Helm charts

### Workflow Trigger Events

The pipeline is triggered by:
- Push events to the `main` branch
- Pull requests against the `main` branch
- Manual workflow dispatches with environment selection:
  ```yaml
  workflow_dispatch:
    inputs:
      environment:
        description: 'Environment to deploy to'
        required: true
        default: 'development'
        type: choice
        options:
          - development
          - staging
          - production
  ```

### Pipeline Stages in Detail

#### 1. Testing Stage
- Sets up a PostgreSQL service container for test databases
- Configures Python environment with dependencies for each service
- Creates test databases for each service
- Runs test suites for all microservices

```yaml
test:
  services:
    postgres:
      image: postgres:12
      env:
        POSTGRES_PASSWORD: postgres
        POSTGRES_USER: postgres
  steps:
    - name: Set up Python
      uses: actions/setup-python@v4
    - name: Install dependencies and run tests
      run: |
        # Install requirements for all services
        # Create test databases
        # Run tests for each microservice
```

#### 2. Building and Publishing Stage
- Uses Docker Buildx for efficient multi-platform image building
- Logs in to Docker Hub using GitHub repository secrets
- Builds Docker images for each microservice
- Tags images with:
  - Latest tag
  - Date-based tag (YYYYMMDD-HHMM)
  - Git commit SHA tag for traceability
- Pushes images to Docker Hub registry

```yaml
build:
  needs: test
  steps:
    - name: Set up Docker Buildx
      uses: docker/setup-buildx-action@v2
    - name: Login to DockerHub
      uses: docker/login-action@v2
    - name: Build and push microservice images
      uses: docker/build-push-action@v4
```

#### 3. Deployment Stage
- Sets up Helm and kubectl with specified versions
- Configures Kubernetes credentials from GitHub secrets
- Creates or verifies the existence of the designated namespace
- Deploys the application using Helm charts with proper version tagging
- Passes secrets and configuration values securely
- Verifies deployment with rollout status checks for each service

```yaml
deploy:
  needs: build
  steps:
    - name: Set up Helm and kubectl
      # Setup tools
    - name: Configure Kubernetes credentials
      # Configure access to cluster
    - name: Deploy with Helm
      run: |
        helm upgrade --install meeting-room-system ./helm \
          --namespace ${{ env.K8S_NAMESPACE }} \
          --set imageTag=${{ env.SHA_TAG }} \
          # Additional configuration values
```

### Required GitHub Secrets

To enable the CI/CD pipeline, the following secrets must be configured in your GitHub repository:

| Secret Name | Description |
|-------------|-------------|
| `DOCKER_HUB_USERNAME` | Docker Hub username for pushing images |
| `DOCKER_HUB_TOKEN` | Docker Hub access token for authentication |
| `KUBECONFIG` | Base64-encoded Kubernetes configuration file |
| `GOOGLE_CLIENT_ID` | Google OAuth Client ID |
| `GOOGLE_CLIENT_SECRET` | Google OAuth Client Secret |
| `JWT_SECRET_KEY` | Secret key for JWT token generation |

### Helm Chart Architecture

The Helm chart structure (in the `helm/` directory) provides a complete deployment solution:

- `Chart.yaml`: Defines chart metadata, version, and maintainer information
- `values.yaml`: Contains configurable parameters for all components with sensible defaults
- Template files organized by component:
  - Database (PostgreSQL) with persistent storage
  - Messaging (Kafka/Zookeeper) for event handling
  - Microservices with proper environment configuration
  - Reverse proxy (NGINX) for unified API access

#### Key Features of the Helm Chart

- **Environment-aware configuration**: Different settings for development, staging, and production
- **Resource management**: Appropriate CPU and memory limits based on environment
- **Secret handling**: Secure storage of sensitive information
- **Service discovery**: Internal networking for microservice communication
- **Initialization jobs**: Automated database and Kafka topic setup
- **Health checks**: Readiness and liveness probes for all services

#### Helm Chart Structure

```
helm/
├── Chart.yaml             # Chart metadata
├── values.yaml            # Default configuration values
└── templates/             # Kubernetes manifest templates
    ├── namespace.yaml     # Namespace definition
    ├── database/          # Database-related resources
    │   └── postgres.yaml  
    ├── kafka/             # Kafka and Zookeeper resources
    │   └── kafka.yaml     
    ├── microservices/     # Application microservices
    │   ├── google-oauth-secret.yaml
    │   ├── secrets.yaml
    │   ├── user-service.yaml
    │   ├── room-service.yaml
    │   └── reservation-service.yaml
    └── nginx/             # NGINX reverse proxy configuration
        └── nginx.yaml
```

### Setting Up Your Own CI/CD Pipeline

1. **Fork the repository** to your GitHub account
2. **Configure the required secrets** in your repository settings
3. **Update the values.yaml** file with your specific configuration
4. **Push to main branch** or create a pull request to trigger the pipeline
5. **Monitor the workflow** in the GitHub Actions tab

### Monitoring CI/CD Runs

- View pipeline runs in the "Actions" tab of your GitHub repository
- Each run provides detailed logs and status of each stage
- Failed stages will provide error messages to help troubleshooting

## Prerequisites

- Python 3.8+
- PostgreSQL 12+
- Docker and Docker Compose
- Apache Kafka

## Installation and Setup

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/meeting-room-res-system-api.git
cd meeting-room-res-system-api
```

### 2. Set Up Environment Files

Create `.env` files for each service:

```bash
# For user-service
cp user-service/.env.example user-service/.env
# For room-service
cp room-service/.env.example room-service/.env
# For reservation-service
cp reservation-service/.env.example reservation-service/.env
```

Update each `.env` file with your configuration (database credentials, JWT secret, etc.)

### 3. Set Up PostgreSQL Databases

```bash
sudo -u postgres psql

CREATE DATABASE user_db;
CREATE DATABASE room_db;
CREATE DATABASE reservation_db;

# Grant privileges
GRANT ALL PRIVILEGES ON DATABASE user_db TO postgres;
GRANT ALL PRIVILEGES ON DATABASE room_db TO postgres;
GRANT ALL PRIVILEGES ON DATABASE reservation_db TO postgres;

\q
```

### 4. Configure PostgreSQL Authentication

Edit PostgreSQL configuration to use password authentication:

```bash
sudo nano /etc/postgresql/14/main/pg_hba.conf
```

Change local authentication methods from `peer` to `md5` or `scram-sha-256`:

```
local   all             postgres                                md5
local   all             all                                     md5
```

Restart PostgreSQL:

```bash
sudo systemctl restart postgresql
```

### 5. Set Up Kafka with Docker

```bash
# Create kafka directory
mkdir -p kafka
cd kafka

# Create docker-compose.yml
cat > docker-compose.yml << 'EOF'
version: '3'
services:
  zookeeper:
    image: wurstmeister/zookeeper
    ports:
      - "2181:2181"
  kafka:
    image: wurstmeister/kafka
    ports:
      - "9092:9092"
    environment:
      KAFKA_ADVERTISED_LISTENERS: INSIDE://kafka:9093,OUTSIDE://localhost:9092
      KAFKA_LISTENER_SECURITY_PROTOCOL_MAP: INSIDE:PLAINTEXT,OUTSIDE:PLAINTEXT
      KAFKA_LISTENERS: INSIDE://0.0.0.0:9093,OUTSIDE://0.0.0.0:9092
      KAFKA_INTER_BROKER_LISTENER_NAME: INSIDE
      KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
EOF

# Start Kafka and Zookeeper
docker-compose up -d

# Create required topics
docker-compose exec kafka kafka-topics.sh --create --topic room_events --bootstrap-server kafka:9093 --partitions 1 --replication-factor 1
```

### 6. Install Python Dependencies

```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies for each service
pip install -r user-service/requirements.txt
pip install -r room-service/requirements.txt
pip install -r reservation-service/requirements.txt
```

### 7. Configure Google OAuth

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Navigate to "APIs & Services" > "Credentials"
3. Create an OAuth 2.0 Client ID
4. Add `http://localhost:5000/auth/google/callback` to Authorized Redirect URIs
5. Add your client ID and secret to `user-service/.env`

### 8. Start the Services

Start each service in a separate terminal:

```bash
# Terminal 1: User Service
cd user-service
source ../venv/bin/activate
python app.py

# Terminal 2: Room Service
cd room-service
source ../venv/bin/activate
python app.py

# Terminal 3: Reservation Service
cd reservation-service
source ../venv/bin/activate
python app.py
```

## API Documentation

### User Service (Port 5000)

#### Authentication
- `GET /auth/google/login` - Initiate Google OAuth login
- `GET /auth/google/callback` - OAuth callback endpoint

#### User Management
- `GET /users/profile` - Get current user profile
- `PUT /users/profile` - Update user profile

#### Admin User Management
- `GET /admin/users` - List all users (admin only)
- `PUT /admin/users/{id}` - Update user details (admin only)
- `DELETE /admin/users/{id}` - Delete a user (admin only)

### Room Service (Port 5001)

#### Room Management
- `GET /rooms` - List all rooms
- `GET /rooms/{id}` - Get room details
- `POST /rooms` - Create a new room (admin only)
- `PUT /rooms/{id}` - Update room details (admin only)
- `DELETE /rooms/{id}` - Delete a room (admin only)

### Reservation Service (Port 5002)

#### Reservation Management
- `GET /reservations` - List all user reservations
- `GET /reservations/{id}` - Get reservation details
- `POST /reservations` - Create a new reservation
- `PUT /reservations/{id}` - Update a reservation
- `DELETE /reservations/{id}` - Cancel a reservation

#### Availability
- `GET /availability` - Check room availability
  - Query parameters: `room_id`, `date`

## Testing

### Testing with cURL

```bash
# Authenticate (this will redirect to browser)
curl http://localhost:5000/auth/google/login

# After authentication, save the JWT token and use for other requests

# Create a room (admin only)
curl -X POST http://localhost:5001/rooms \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{"name": "Conference Room A", "capacity": 10, "equipment": "Projector, Whiteboard"}'

# Create a reservation
curl -X POST http://localhost:5002/reservations \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{"room_id": 1, "start_time": "2025-04-16T10:00:00", "end_time": "2025-04-16T11:00:00", "purpose": "Team Meeting"}'
```

## Troubleshooting

### Database Connection Issues
- Ensure PostgreSQL is running: `sudo systemctl status postgresql`
- Verify database credentials in `.env` files
- Check PostgreSQL authentication configuration in `pg_hba.conf`

### Kafka Issues
- Verify Kafka is running: `docker ps`
- Check Kafka logs: `docker-compose logs kafka`

### OAuth Authentication Issues
- Verify redirect URIs match between Google Cloud Console and application
- Ensure correct client ID and secret in `.env` file

## License

[MIT License](LICENSE)
