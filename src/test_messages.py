#!/usr/bin/env python3
"""
Test script to send simulated Bodet Scorepad messages to the capture server.
Useful for testing without a physical Scorepad.
"""

import socket
import time
import sys


def calculate_lrc(data: bytes) -> int:
    """Calculate LRC (XOR of all bytes)."""
    lrc = 0
    for byte in data:
        lrc ^= byte
    return lrc & 0xFF


def create_message(data: bytes) -> bytes:
    """
    Create a valid Bodet protocol message.
    
    Format: SOH (0x01) + Address (0x7F) + STX (0x02) + DATA + ETX (0x03) + LRC
    """
    SOH = 0x01
    ADDRESS = 0x7F
    STX = 0x02
    ETX = 0x03
    
    # Build message: Address + STX + DATA + ETX
    message_part = bytes([ADDRESS, STX]) + data + bytes([ETX])
    
    # Calculate LRC (XOR of Address to ETX)
    lrc = calculate_lrc(message_part)
    
    # Complete message: SOH + message_part + LRC
    full_message = bytes([SOH]) + message_part + bytes([lrc])
    
    return full_message


def send_test_message(host: str = 'localhost', port: int = 4001, data: bytes = None):
    """
    Send a test message to the capture server.
    
    Args:
        host: Server hostname or IP
        port: Server port
        data: Data bytes (if None, uses example data)
    """
    if data is None:
        # Example data - this would be replaced with actual roller hockey message format
        # For now, using a simple test pattern
        data = bytes([0x47, 0x31, 0x31, 0x80, 0x37, 0x20, 0x34, 0x30, 0x37, 0x20, 0x30, 0x31])
    
    message = create_message(data)
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((host, port))
        
        print(f"Sending test message to {host}:{port}")
        print(f"Message (hex): {message.hex()}")
        print(f"Message length: {len(message)} bytes")
        
        sock.sendall(message)
        print("Message sent successfully!")
        
        sock.close()
        
    except ConnectionRefusedError:
        print(f"Error: Could not connect to {host}:{port}")
        print("Make sure the capture server is running!")
        sys.exit(1)
    except Exception as e:
        print(f"Error sending message: {e}")
        sys.exit(1)


def send_multiple_messages(host: str = 'localhost', port: int = 4001, count: int = 5, delay: float = 1.0):
    """
    Send multiple test messages with delay between them.
    
    Args:
        host: Server hostname or IP
        port: Server port
        count: Number of messages to send
        delay: Delay between messages in seconds
    """
    print(f"Sending {count} test messages to {host}:{port}...")
    
    for i in range(count):
        print(f"\n--- Message {i+1}/{count} ---")
        send_test_message(host, port)
        
        if i < count - 1:
            time.sleep(delay)


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Send test messages to Bodet capture server')
    parser.add_argument('--host', default='localhost', help='Server hostname (default: localhost)')
    parser.add_argument('--port', type=int, default=4001, help='Server port (default: 4001)')
    parser.add_argument('--count', type=int, default=1, help='Number of messages to send (default: 1)')
    parser.add_argument('--delay', type=float, default=1.0, help='Delay between messages in seconds (default: 1.0)')
    parser.add_argument('--data', help='Hex string of data bytes (e.g., "4731318037")')
    
    args = parser.parse_args()
    
    # Parse hex data if provided
    data = None
    if args.data:
        try:
            data = bytes.fromhex(args.data.replace(' ', ''))
        except ValueError as e:
            print(f"Error parsing hex data: {e}")
            sys.exit(1)
    
    if args.count > 1:
        send_multiple_messages(args.host, args.port, args.count, args.delay)
    else:
        send_test_message(args.host, args.port, data)


if __name__ == '__main__':
    main()
