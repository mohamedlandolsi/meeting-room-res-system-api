#!/bin/bash
# Run SonarQube Analysis

set -e  # Exit immediately if a command exits with a non-zero status

# Color setup
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

# Check if running as sudo/root
check_docker_permissions() {
  # Check if user is in docker group
  if ! groups | grep -q docker; then
    echo -e "${YELLOW}You are not in the docker group. Some Docker operations might require sudo.${NC}"
    echo -e "${YELLOW}Attempting to restart SonarQube containers with sudo...${NC}"
    
    # Try to clean up any existing containers with sudo
    sudo docker-compose -f sonarqube/docker-compose.yml down 2>/dev/null || true
    
    # Start containers with sudo
    sudo docker-compose -f sonarqube/docker-compose.yml up -d
    return 0
  fi
  return 1
}

# Check and fix Elasticsearch vm.max_map_count setting
fix_max_map_count() {
  local current_max_map_count=$(cat /proc/sys/vm/max_map_count)
  if [ "$current_max_map_count" -lt 262144 ]; then
    echo -e "${YELLOW}The vm.max_map_count is currently set to $current_max_map_count, which is too low for Elasticsearch.${NC}"
    echo -e "${YELLOW}Attempting to increase vm.max_map_count to 262144...${NC}"
    
    # Try to increase the limit
    if sudo sysctl -w vm.max_map_count=262144; then
      echo -e "${GREEN}Successfully increased vm.max_map_count to 262144.${NC}"
    else
      echo -e "${RED}Failed to increase vm.max_map_count. You may need to run this command manually:${NC}"
      echo -e "${YELLOW}sudo sysctl -w vm.max_map_count=262144${NC}"
      read -p "Do you want to continue anyway? (y/n) " -n 1 -r
      echo
      if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
      fi
    fi
  else
    echo -e "${GREEN}vm.max_map_count is already set to $current_max_map_count, which is adequate.${NC}"
  fi
}

# Function to clean up containers if they're stuck
cleanup_docker_containers() {
  echo -e "${YELLOW}Cleaning up any existing SonarQube containers...${NC}"
  
  # Try normal docker-compose down first
  if docker-compose -f sonarqube/docker-compose.yml down 2>/dev/null; then
    echo -e "${GREEN}Successfully cleaned up containers.${NC}"
  else
    echo -e "${YELLOW}Permission issues detected. Trying with sudo...${NC}"
    
    # Try with sudo
    if sudo docker-compose -f sonarqube/docker-compose.yml down; then
      echo -e "${GREEN}Successfully cleaned up containers with sudo.${NC}"
    else
      echo -e "${RED}Failed to clean up containers. You may need to manually remove them:${NC}"
      echo -e "${YELLOW}sudo docker rm -f sonarqube-sonarqube-1 sonarqube-sonarqube-db-1${NC}"
      
      # Ask if user wants to manually remove containers
      read -p "Do you want to attempt manual container removal? (y/n) " -n 1 -r
      echo
      if [[ $REPLY =~ ^[Yy]$ ]]; then
        sudo docker rm -f sonarqube-sonarqube-1 sonarqube-sonarqube-db-1 || true
      fi
    fi
  fi
}

# Function to check SonarQube initial setup status
check_sonarqube_setup() {
  echo -e "${YELLOW}Checking SonarQube setup status...${NC}"
  
  # Try to access the API to check if admin credentials are still default
  local response=$(curl -s -o /dev/null -w "%{http_code}" -u admin:admin http://localhost:9000/api/system/status)
  
  if [ "$response" == "200" ]; then
    echo -e "${YELLOW}SonarQube is using default admin credentials (admin/admin).${NC}"
    echo -e "${YELLOW}Please complete the initial setup before running the scanner:${NC}"
    echo -e "1. Open ${GREEN}http://localhost:9000${NC} in your browser"
    echo -e "2. Log in with username: ${GREEN}admin${NC} and password: ${GREEN}admin${NC}"
    echo -e "3. Update your password when prompted"
    echo -e "4. Go to ${GREEN}Administration > Security > Users${NC}"
    echo -e "5. Click on the ${GREEN}Tokens${NC} action for the admin user"
    echo -e "6. Generate a new token with name 'scanner'"
    echo -e "7. Copy the token and use it with this script:"
    echo -e "   ${GREEN}SONAR_TOKEN=your_token ./run-sonar-scan.sh${NC}"
    
    read -p "Press Enter to open SonarQube in your default browser..."
    xdg-open http://localhost:9000 >/dev/null 2>&1 || open http://localhost:9000 >/dev/null 2>&1 || echo -e "${YELLOW}Could not open browser automatically. Please open http://localhost:9000 manually.${NC}"
    
    # Ask if user wants to provide token now
    read -p "Have you completed the setup and generated a token? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
      read -p "Please enter your SonarQube token: " token
      if [ -n "$token" ]; then
        export SONAR_TOKEN="$token"
        echo -e "${GREEN}Token saved for this session.${NC}"
      else
        echo -e "${RED}No token provided. Exiting.${NC}"
        exit 1
      fi
    else
      echo -e "${YELLOW}Please run the script again after completing the setup.${NC}"
      exit 0
    fi
  elif [ "$response" == "401" ]; then
    echo -e "${GREEN}SonarQube setup has been completed with custom credentials.${NC}"
  else
    echo -e "${RED}Could not determine SonarQube setup status. Got HTTP response code: $response${NC}"
  fi
}

# Check if SonarQube is running
echo -e "${YELLOW}Checking SonarQube server...${NC}"
if ! curl -s -f http://localhost:9000 > /dev/null; then
  echo -e "${RED}SonarQube server is not running.${NC}"
  echo -e "${YELLOW}Checking system requirements for Elasticsearch...${NC}"
  
  # Check and fix vm.max_map_count
  fix_max_map_count
  
  # Clean up any existing containers
  cleanup_docker_containers
  
  echo -e "${YELLOW}Starting SonarQube using Docker Compose...${NC}"
  
  # Check if docker-compose exists in the sonarqube directory
  if [ ! -f "sonarqube/docker-compose.yml" ]; then
    echo -e "${RED}Error: sonarqube/docker-compose.yml not found!${NC}"
    exit 1
  fi
  
  # Try to start SonarQube
  if ! docker-compose -f sonarqube/docker-compose.yml up -d; then
    echo -e "${YELLOW}Failed to start with regular permissions, trying with sudo...${NC}"
    sudo docker-compose -f sonarqube/docker-compose.yml up -d
  fi
  
  # Wait for SonarQube to start
  echo -e "${YELLOW}Waiting for SonarQube to start (this may take up to 5 minutes)...${NC}"
  for i in {1..60}; do
    if curl -s -f http://localhost:9000 > /dev/null; then
      echo -e "\n${GREEN}SonarQube is up and running!${NC}"
      sleep 5  # Give it a few more seconds to fully initialize
      break
    fi
    if [ $i -eq 60 ]; then
      echo -e "\n${RED}SonarQube did not start in the expected time.${NC}"
      echo -e "${YELLOW}Checking container logs for issues...${NC}"
      
      # Try regular docker first, then with sudo if that fails
      if ! docker-compose -f sonarqube/docker-compose.yml logs; then
        sudo docker-compose -f sonarqube/docker-compose.yml logs
      fi
      
      echo -e "\n${YELLOW}Possible solutions:${NC}"
      echo -e "1. Check if any error messages were displayed above"
      echo -e "2. Make sure ports 9000 and 5432 are not in use by other applications"
      echo -e "3. Restart Docker: ${YELLOW}sudo systemctl restart docker${NC}"
      echo -e "4. Force remove containers and try again: ${YELLOW}sudo docker rm -f sonarqube-sonarqube-1 sonarqube-sonarqube-db-1${NC}"
      exit 1
    fi
    echo -n "."
    sleep 5
  done
  echo
  
  # Check if this is the first time SonarQube is starting
  check_sonarqube_setup
else
  # SonarQube is already running, but check if it's using default credentials
  check_sonarqube_setup
fi

# Rest of the script remains unchanged
if [ "$1" == "--with-tests" ]; then
  echo -e "${YELLOW}Running tests with coverage...${NC}"
  
  # Create virtual environment if it doesn't exist
  if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    python3 -m venv venv
  fi
  
  # Activate virtual environment
  source venv/bin/activate
  
  # Install dependencies
  echo -e "${YELLOW}Installing dependencies...${NC}"
  pip install -r user-service/requirements.txt
  pip install -r room-service/requirements.txt
  pip install -r reservation-service/requirements.txt
  pip install pytest pytest-cov coverage

  # Run tests with coverage
  echo -e "${YELLOW}Running user-service tests...${NC}"
  (cd user-service && python -m pytest tests/ -v --cov=. --cov-report=xml:../user-service-coverage.xml)
  
  echo -e "${YELLOW}Running room-service tests...${NC}"
  (cd room-service && python -m pytest tests/ -v --cov=. --cov-report=xml:../room-service-coverage.xml)
  
  echo -e "${YELLOW}Running reservation-service tests...${NC}"
  (cd reservation-service && python -m pytest tests/ -v --cov=. --cov-report=xml:../reservation-service-coverage.xml)
  
  # Merge coverage reports
  echo -e "${YELLOW}Merging coverage reports...${NC}"
  coverage combine user-service-coverage.xml room-service-coverage.xml reservation-service-coverage.xml || true
  coverage xml -o coverage.xml || true
  
  # Deactivate virtual environment
  deactivate
fi

# Run SonarQube scanner
echo -e "${YELLOW}Running SonarQube scanner...${NC}"

# Check if SONAR_TOKEN is set
if [ -z "${SONAR_TOKEN}" ]; then
  echo -e "${RED}Error: SONAR_TOKEN environment variable is not set.${NC}"
  echo -e "${YELLOW}Please run the script with the token:${NC}"
  echo -e "${GREEN}SONAR_TOKEN=your_token ./run-sonar-scan.sh${NC}"
  exit 1
fi

# Add more verbose output to debug authentication issues
echo -e "${YELLOW}Using token starting with: ${SONAR_TOKEN:0:4}...${NC}"

# Create a sonar-scanner.properties file with authentication details
echo -e "${YELLOW}Creating a configuration file with authentication details...${NC}"
mkdir -p .scannerwork
cat > .scannerwork/sonar-scanner.properties << EOF
sonar.host.url=http://localhost:9000
sonar.login=${SONAR_TOKEN}
sonar.projectKey=meeting-room-reservation-system
sonar.projectName=Meeting Room Reservation System
sonar.projectVersion=1.0
sonar.sources=user-service,room-service,reservation-service
sonar.sourceEncoding=UTF-8
sonar.python.coverage.reportPaths=coverage.xml
sonar.exclusions=venv/**,**/__pycache__/**,**/tests/**
EOF

echo -e "${YELLOW}Running scanner with direct properties configuration...${NC}"

# Run scanner using Docker with improved error handling and proper authentication
if ! docker run --rm \
  --network=host \
  -v "$(pwd):/usr/src" \
  -w /usr/src \
  -e SONAR_HOST_URL=http://localhost:9000 \
  -e SONAR_LOGIN="${SONAR_TOKEN}" \
  sonarsource/sonar-scanner-cli:latest \
  -Dsonar.projectKey=meeting-room-reservation-system \
  -Dsonar.projectName="Meeting Room Reservation System" \
  -Dsonar.projectVersion=1.0 \
  -Dsonar.sources=user-service,room-service,reservation-service \
  -Dsonar.sourceEncoding=UTF-8 \
  -Dsonar.python.coverage.reportPaths=coverage.xml \
  -Dsonar.exclusions=venv/**,**/__pycache__/**,**/tests/** \
  -Dsonar.login="${SONAR_TOKEN}" \
  -Dsonar.host.url=http://localhost:9000; then
  
  echo -e "${YELLOW}First attempt failed. Trying alternative approach...${NC}"
  
  docker run --rm \
    --network=host \
    -v "$(pwd):/usr/src" \
    -w /usr/src \
    sonarsource/sonar-scanner-cli:latest \
    -Dproject.settings=.scannerwork/sonar-scanner.properties
    
  # If that fails, try with sudo
  if [ $? -ne 0 ]; then
    echo -e "${RED}Failed to run SonarQube scanner. Trying with sudo...${NC}"
    
    sudo docker run --rm \
      --network=host \
      -v "$(pwd):/usr/src" \
      -w /usr/src \
      -e SONAR_HOST_URL=http://localhost:9000 \
      -e SONAR_LOGIN="${SONAR_TOKEN}" \
      sonarsource/sonar-scanner-cli:latest
  fi
fi

echo -e "${GREEN}SonarQube analysis completed!${NC}"
echo -e "${GREEN}View the results at: http://localhost:9000/dashboard?id=meeting-room-reservation-system${NC}"

