#!/bin/bash
# Script to set up automated database backups using cron

# Define colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Setting up automated database backups...${NC}"

# Get the absolute path of the backup script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_SCRIPT="${SCRIPT_DIR}/backup.sh"

# Check if the backup script exists
if [ ! -f "$BACKUP_SCRIPT" ]; then
    echo -e "${RED}Backup script not found at $BACKUP_SCRIPT${NC}"
    exit 1
fi

# Ensure the script is executable
chmod +x "$BACKUP_SCRIPT"

# Display current crontab
echo -e "${YELLOW}Current crontab entries:${NC}"
crontab -l 2>/dev/null || echo "No crontab entries found"

# Ask for backup frequency
echo -e "\n${YELLOW}Select backup frequency:${NC}"
echo "1) Hourly"
echo "2) Daily (recommended)"
echo "3) Weekly"
echo "4) Custom"
read -p "Enter choice [2]: " FREQUENCY
FREQUENCY=${FREQUENCY:-2}

# Default to 2 AM for daily backups
BACKUP_HOUR=2
BACKUP_MINUTE=0

case $FREQUENCY in
    1)
        # Hourly backup - run at 30 minutes past each hour
        CRON_SCHEDULE="30 * * * *"
        SCHEDULE_DESC="hourly at 30 minutes past the hour"
        ;;
    2)
        # Daily backup - ask for preferred time
        read -p "Enter hour for daily backup (0-23) [2]: " BACKUP_HOUR
        BACKUP_HOUR=${BACKUP_HOUR:-2}
        read -p "Enter minute for daily backup (0-59) [0]: " BACKUP_MINUTE
        BACKUP_MINUTE=${BACKUP_MINUTE:-0}
        CRON_SCHEDULE="$BACKUP_MINUTE $BACKUP_HOUR * * *"
        SCHEDULE_DESC="daily at $BACKUP_HOUR:$(printf "%02d" $BACKUP_MINUTE)"
        ;;
    3)
        # Weekly backup - ask for preferred day and time
        read -p "Enter day of week for backup (0-6, where 0 is Sunday) [0]: " BACKUP_DAY
        BACKUP_DAY=${BACKUP_DAY:-0}
        read -p "Enter hour for backup (0-23) [2]: " BACKUP_HOUR
        BACKUP_HOUR=${BACKUP_HOUR:-2}
        read -p "Enter minute for backup (0-59) [0]: " BACKUP_MINUTE
        BACKUP_MINUTE=${BACKUP_MINUTE:-0}
        CRON_SCHEDULE="$BACKUP_MINUTE $BACKUP_HOUR * * $BACKUP_DAY"
        
        # Convert day number to name for display
        DAY_NAMES=("Sunday" "Monday" "Tuesday" "Wednesday" "Thursday" "Friday" "Saturday")
        SCHEDULE_DESC="weekly on ${DAY_NAMES[$BACKUP_DAY]} at $BACKUP_HOUR:$(printf "%02d" $BACKUP_MINUTE)"
        ;;
    4)
        # Custom cron schedule
        echo -e "${YELLOW}Enter custom cron schedule (minute hour day month weekday):${NC}"
        echo "Examples:"
        echo "  30 2 * * *      # Daily at 2:30 AM"
        echo "  0 */4 * * *     # Every 4 hours"
        echo "  0 0 * * 0       # Weekly on Sunday at midnight"
        echo "  0 0 1 * *       # Monthly on the 1st at midnight"
        read -p "Custom schedule: " CRON_SCHEDULE
        SCHEDULE_DESC="custom schedule: $CRON_SCHEDULE"
        ;;
    *)
        echo -e "${RED}Invalid choice. Using daily backup at 2:00 AM.${NC}"
        CRON_SCHEDULE="0 2 * * *"
        SCHEDULE_DESC="daily at 2:00 AM"
        ;;
esac

# Create cron job entry
CRON_ENTRY="$CRON_SCHEDULE $BACKUP_SCRIPT >> /home/mohamed/meeting-room-res-system-api/logs/cron_backup.log 2>&1"

# Check if entry already exists
EXISTING_CRONTAB=$(crontab -l 2>/dev/null || echo "")
if echo "$EXISTING_CRONTAB" | grep -q "$BACKUP_SCRIPT"; then
    echo -e "${YELLOW}Backup job already exists in crontab. Updating...${NC}"
    # Remove old entry and add new one
    NEW_CRONTAB=$(echo "$EXISTING_CRONTAB" | grep -v "$BACKUP_SCRIPT")
    echo -e "$NEW_CRONTAB\n$CRON_ENTRY" | crontab -
else
    # Add to existing crontab
    echo -e "$EXISTING_CRONTAB\n$CRON_ENTRY" | crontab -
fi

# Verify cron job was added
if crontab -l 2>/dev/null | grep -q "$BACKUP_SCRIPT"; then
    echo -e "${GREEN}Successfully scheduled database backups $SCHEDULE_DESC${NC}"
    echo -e "${GREEN}Backup logs will be written to: /home/mohamed/meeting-room-res-system-api/logs/cron_backup.log${NC}"
else
    echo -e "${RED}Failed to schedule backup job. Please try again or add manually to crontab.${NC}"
    exit 1
fi

# Create logs directory if it doesn't exist
mkdir -p /home/mohamed/meeting-room-res-system-api/logs

# Test AWS configuration
echo -e "${YELLOW}Testing AWS configuration...${NC}"
if "$BACKUP_SCRIPT" --test-aws 2>&1 | grep -q "AWS credentials verified successfully"; then
    echo -e "${GREEN}AWS configuration test passed!${NC}"
else
    echo -e "${RED}AWS configuration test failed.${NC}"
    echo -e "${YELLOW}Please update your AWS credentials in /home/mohamed/meeting-room-res-system-api/config/aws-config.sh${NC}"
    echo -e "${YELLOW}Make sure to install AWS CLI if not already installed: sudo apt install awscli${NC}"
fi

echo -e "\n${GREEN}Setup completed!${NC}"
echo -e "${YELLOW}To manually run a backup, execute:${NC}"
echo -e "  $BACKUP_SCRIPT"
echo -e "\n${YELLOW}To modify the schedule later, run:${NC}"
echo -e "  crontab -e"