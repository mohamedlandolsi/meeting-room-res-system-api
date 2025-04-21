#!/bin/bash
# Database Backup Script for Meeting Room Reservation System
# Backs up PostgreSQL databases and uploads them to AWS S3

# Source configuration file if it exists
CONFIG_FILE="/home/mohamed/meeting-room-res-system-api/config/aws-config.sh"
if [ -f "$CONFIG_FILE" ]; then
    source "$CONFIG_FILE"
fi

# Exit on any error
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

# Log file
LOG_FILE="/home/mohamed/meeting-room-res-system-api/logs/backup_$(date +%Y-%m-%d).log"
BACKUP_DIR="/home/mohamed/meeting-room-res-system-api/backups"

# S3 bucket information - use variables from config file if available
S3_BUCKET="${S3_BUCKET_NAME:-meeting-room-backup-bucket}"
S3_PREFIX="database-backups/$(date +%Y-%m)/$(date +%d)"
# Use date format from config file if available
if [ ! -z "$S3_PREFIX_FORMAT" ]; then
    S3_PREFIX=$(date +"$S3_PREFIX_FORMAT")
fi

# Database configuration
DB_USER="postgres"
DB_PASSWORD="postgres"
DB_HOST="localhost"
DB_PORT="5432"
DATABASES=("user_db" "room_db" "reservation_db")

# Retention policy (in days) - use variables from config file if available
LOCAL_RETENTION_DAYS=${LOCAL_RETENTION_DAYS:-7}
S3_RETENTION_DAYS=${S3_RETENTION_DAYS:-30}

# Create directories if they don't exist
mkdir -p "$BACKUP_DIR"
mkdir -p "$(dirname "$LOG_FILE")"

# Function for logging
log() {
    echo -e "$(date +"%Y-%m-%d %H:%M:%S") - $1" | tee -a "$LOG_FILE"
}

# Function to check required commands
check_dependencies() {
    log "${YELLOW}Checking dependencies...${NC}"
    
    # Check for PostgreSQL client
    if ! command -v pg_dump &> /dev/null; then
        log "${RED}Error: pg_dump is not installed. Please install PostgreSQL client.${NC}"
        exit 1
    fi
    
    # Check for AWS CLI
    if ! command -v aws &> /dev/null; then
        log "${RED}Error: AWS CLI is not installed. Please install AWS CLI.${NC}"
        exit 1
    fi
    
    log "${GREEN}All dependencies are installed.${NC}"
}

# Function to check AWS credentials
check_aws_credentials() {
    log "${YELLOW}Checking AWS credentials...${NC}"
    
    if ! aws sts get-caller-identity &> /dev/null; then
        log "${RED}Error: AWS credentials are not configured correctly.${NC}"
        log "${YELLOW}Please run 'aws configure' to set up your credentials.${NC}"
        log "${YELLOW}Or update credentials in $CONFIG_FILE${NC}"
        exit 1
    fi
    
    # Check if S3 bucket exists
    if ! aws s3 ls "s3://$S3_BUCKET" &> /dev/null; then
        log "${YELLOW}S3 bucket does not exist. Creating bucket $S3_BUCKET...${NC}"
        if aws s3 mb "s3://$S3_BUCKET" --region us-east-1; then
            log "${GREEN}S3 bucket created successfully.${NC}"
            
            # Configure lifecycle policy for S3 bucket
            LIFECYCLE_CONFIG='{
                "Rules": [
                    {
                        "ID": "AutoExpireBackups",
                        "Status": "Enabled",
                        "Prefix": "database-backups/",
                        "Expiration": {
                            "Days": '$S3_RETENTION_DAYS'
                        }
                    }
                ]
            }'
            
            echo "$LIFECYCLE_CONFIG" > /tmp/lifecycle-config.json
            aws s3api put-bucket-lifecycle-configuration --bucket "$S3_BUCKET" --lifecycle-configuration file:///tmp/lifecycle-config.json
            log "${GREEN}S3 bucket lifecycle policy configured (retention: $S3_RETENTION_DAYS days).${NC}"
        else
            log "${RED}Failed to create S3 bucket. Please check your permissions.${NC}"
            exit 1
        fi
    fi
    
    log "${GREEN}AWS credentials verified successfully.${NC}"
}

# Function to backup databases
backup_databases() {
    log "${YELLOW}Starting database backups...${NC}"
    
    # Generate timestamp for backup filenames
    TIMESTAMP=$(date +"%Y%m%d-%H%M%S")
    
    # Loop through each database and create backup
    for DB_NAME in "${DATABASES[@]}"; do
        BACKUP_FILENAME="${DB_NAME}_${TIMESTAMP}.sql.gz"
        BACKUP_PATH="${BACKUP_DIR}/${BACKUP_FILENAME}"
        
        log "${YELLOW}Backing up database: ${DB_NAME}${NC}"
        
        if PGPASSWORD="$DB_PASSWORD" pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -F c | gzip > "$BACKUP_PATH"; then
            log "${GREEN}Successfully backed up database: ${DB_NAME}${NC}"
            # Get size of backup file
            BACKUP_SIZE=$(du -h "$BACKUP_PATH" | cut -f1)
            log "${GREEN}Backup size: ${BACKUP_SIZE}${NC}"
        else
            log "${RED}Failed to backup database: ${DB_NAME}${NC}"
            continue
        fi
        
        # Upload to S3
        log "${YELLOW}Uploading ${DB_NAME} backup to S3...${NC}"
        if aws s3 cp "$BACKUP_PATH" "s3://${S3_BUCKET}/${S3_PREFIX}/${BACKUP_FILENAME}"; then
            log "${GREEN}Successfully uploaded ${DB_NAME} backup to S3.${NC}"
        else
            log "${RED}Failed to upload ${DB_NAME} backup to S3.${NC}"
        fi
    done
    
    log "${GREEN}Database backup completed.${NC}"
}

# Function to backup Kafka configuration
backup_kafka_config() {
    log "${YELLOW}Backing up Kafka configuration...${NC}"
    
    TIMESTAMP=$(date +"%Y%m%d-%H%M%S")
    KAFKA_BACKUP_DIR="${BACKUP_DIR}/kafka"
    mkdir -p "$KAFKA_BACKUP_DIR"
    
    # Backup Kafka topics list and configuration
    if [ -f "./kafka/docker-compose.yml" ]; then
        TOPICS_BACKUP_FILE="${KAFKA_BACKUP_DIR}/kafka-topics-${TIMESTAMP}.json"
        
        # Start Kafka container if it's not running
        if ! docker-compose -f ./kafka/docker-compose.yml ps | grep -q "Up" | grep -q "kafka"; then
            log "${YELLOW}Kafka is not running. Skipping Kafka configuration backup.${NC}"
        else
            log "${YELLOW}Getting Kafka topics...${NC}"
            # Use the Kafka container to list topics
            if docker-compose -f ./kafka/docker-compose.yml exec -T kafka kafka-topics.sh --list --bootstrap-server kafka:9093 > "${TOPICS_BACKUP_FILE}.tmp"; then
                # For each topic, get configuration
                while read -r TOPIC; do
                    if [ ! -z "$TOPIC" ]; then
                        log "${YELLOW}Getting configuration for topic: ${TOPIC}${NC}"
                        docker-compose -f ./kafka/docker-compose.yml exec -T kafka kafka-topics.sh --describe --topic "$TOPIC" --bootstrap-server kafka:9093 >> "${TOPICS_BACKUP_FILE}.tmp"
                        echo "" >> "${TOPICS_BACKUP_FILE}.tmp"
                    fi
                done < "${TOPICS_BACKUP_FILE}.tmp"
                
                # Format nicely and compress
                cat "${TOPICS_BACKUP_FILE}.tmp" | gzip > "$TOPICS_BACKUP_FILE.gz"
                rm "${TOPICS_BACKUP_FILE}.tmp"
                
                # Upload to S3
                log "${YELLOW}Uploading Kafka configuration to S3...${NC}"
                if aws s3 cp "${TOPICS_BACKUP_FILE}.gz" "s3://${S3_BUCKET}/${S3_PREFIX}/kafka-topics-${TIMESTAMP}.json.gz"; then
                    log "${GREEN}Successfully uploaded Kafka configuration to S3.${NC}"
                else
                    log "${RED}Failed to upload Kafka configuration to S3.${NC}"
                fi
            else
                log "${RED}Failed to backup Kafka topics.${NC}"
            fi
        fi
    else
        log "${YELLOW}Kafka docker-compose.yml not found. Skipping Kafka configuration backup.${NC}"
    fi
}

# Function to cleanup old backups
cleanup_old_backups() {
    log "${YELLOW}Cleaning up old local backups (older than ${LOCAL_RETENTION_DAYS} days)...${NC}"
    
    # Find and delete old backup files
    find "$BACKUP_DIR" -type f -name "*.sql.gz" -mtime +${LOCAL_RETENTION_DAYS} -delete
    find "$BACKUP_DIR" -type f -name "*.json.gz" -mtime +${LOCAL_RETENTION_DAYS} -delete
    
    log "${GREEN}Local backup cleanup completed.${NC}"
}

# Process command-line arguments
if [ "$1" = "--test-aws" ]; then
    log "${YELLOW}Testing AWS configuration...${NC}"
    check_dependencies
    check_aws_credentials
    exit 0
fi

# Main execution
log "${GREEN}=== Starting backup process ===${NC}"

# Check dependencies
check_dependencies

# Check AWS credentials
check_aws_credentials

# Backup databases
backup_databases

# Backup Kafka configuration
backup_kafka_config

# Cleanup old backups
cleanup_old_backups

log "${GREEN}=== Backup process completed successfully ===${NC}"

exit 0