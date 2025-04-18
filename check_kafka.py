#!/usr/bin/env python3
"""
Script to check Kafka connectivity status
"""
import sys
import socket
import time

def check_kafka(host="localhost", port=9092, timeout=5):
    """
    Check if Kafka is running by attempting to connect to the broker
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    
    try:
        sock.connect((host, port))
        print(f"✅ Kafka broker is running at {host}:{port}")
        return True
    except socket.error as e:
        print(f"❌ Cannot connect to Kafka broker at {host}:{port}: {e}")
        return False
    finally:
        sock.close()

def main():
    """
    Main function to check Kafka status with optional host and port arguments
    """
    host = "localhost"
    port = 9092
    
    # Parse command line arguments
    if len(sys.argv) > 1:
        host = sys.argv[1]
    if len(sys.argv) > 2:
        try:
            port = int(sys.argv[2])
        except ValueError:
            print(f"Invalid port number: {sys.argv[2]}")
            sys.exit(1)
    
    # Check Kafka status
    if not check_kafka(host, port):
        print("\nKafka may not be running. You can start it using:")
        print("cd ~/meeting-room-res-system-api/kafka")
        print("docker-compose up -d")
    
if __name__ == "__main__":
    main()
