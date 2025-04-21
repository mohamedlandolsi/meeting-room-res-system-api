#!/bin/bash
# AWS S3 Configuration File for Backup Script

# AWS Credentials
# Replace these with your actual AWS credentials
export AWS_ACCESS_KEY_ID="YOUR_AWS_ACCESS_KEY"
export AWS_SECRET_ACCESS_KEY="YOUR_AWS_SECRET_KEY"
export AWS_DEFAULT_REGION="us-east-1"

# S3 Bucket Configuration
export S3_BUCKET_NAME="meeting-room-backup-bucket"
# You can customize the prefix if needed
export S3_PREFIX_FORMAT="database-backups/%Y-%m/%d"

# Retention Configuration
export LOCAL_RETENTION_DAYS=7
export S3_RETENTION_DAYS=30