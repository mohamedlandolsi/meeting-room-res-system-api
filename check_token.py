#!/usr/bin/env python3
"""
Script to check JWT token validity
"""
import sys
import jwt
import json
import argparse
from datetime import datetime

def decode_token(token, verify=False):
    """
    Decode a JWT token without verification to inspect its contents
    """
    try:
        # First try to decode without verification
        decoded = jwt.decode(token, options={"verify_signature": False})
        
        # Print token information
        print("✅ JWT Token successfully decoded")
        print("\nToken Header:")
        header = jwt.get_unverified_header(token)
        print(json.dumps(header, indent=2))
        
        print("\nToken Payload:")
        print(json.dumps(decoded, indent=2))
        
        # Check expiration
        if 'exp' in decoded:
            expiry = datetime.fromtimestamp(decoded['exp'])
            now = datetime.now()
            if expiry > now:
                print(f"\n✅ Token is valid until: {expiry}")
            else:
                print(f"\n❌ Token expired at: {expiry}")
        
        # Check identity/subject claim
        if 'sub' in decoded:
            print(f"\n✅ Identity (sub): {decoded['sub']}")
            if not isinstance(decoded['sub'], str):
                print("⚠️  Warning: 'sub' claim should be a string but isn't")
        else:
            print("\n❌ Token missing 'sub' claim (identity)")
            
        return decoded
        
    except Exception as e:
        print(f"❌ Error decoding token: {str(e)}")
        return None

def main():
    """
    Main function to check JWT token
    """
    parser = argparse.ArgumentParser(description='Decode and inspect a JWT token')
    parser.add_argument('token', nargs='?', help='JWT token to decode')
    parser.add_argument('--verify', action='store_true', help='Verify token signature')
    
    args = parser.parse_args()
    
    # Get token from args or prompt
    token = args.token
    if not token:
        token = input("Enter JWT token: ")
    
    token = token.strip()
    if token.startswith('Bearer '):
        token = token[7:]
    
    # Decode the token
    decode_token(token, args.verify)

if __name__ == "__main__":
    main()
