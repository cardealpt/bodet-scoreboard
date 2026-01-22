#!/usr/bin/env python3
"""
Bodet Scorepad TCP Capture Server
Receives and processes messages from Bodet Scorepad via TCP connection.
"""

import socket
import threading
import queue
import time
from typing import Optional
from configparser import ConfigParser
import logging

from message_parser import MessageParser
from output_handler import OutputHandler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BodetCaptureServer:
    """TCP server that receives messages from Bodet Scorepad."""
    
    def __init__(self, host: str = '0.0.0.0', port: int = 4001):
        """
        Initialize the capture server.
        
        Args:
            host: IP address to bind the server (default: 0.0.0.0)
            port: Port number to listen on (default: 4001)
        """
        self.host = host
        self.port = port
        self.socket: Optional[socket.socket] = None
        self.running = False
        self.message_queue = queue.Queue()
        self.parser = MessageParser()
        self.output_handler = OutputHandler()
        
    def start(self):
        """Start the TCP server and begin listening for connections."""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.bind((self.host, self.port))
            self.socket.listen(1)
            self.running = True
            
            logger.info(f"Bodet Capture Server started on {self.host}:{self.port}")
            logger.info("Waiting for connection from Scorepad...")
            
            # Start message processing thread
            processing_thread = threading.Thread(target=self._process_messages, daemon=True)
            processing_thread.start()
            
            # Main connection loop
            while self.running:
                try:
                    client_socket, client_address = self.socket.accept()
                    logger.info(f"Connected to Scorepad at {client_address}")
                    
                    # Handle client connection in a separate thread
                    client_thread = threading.Thread(
                        target=self._handle_client,
                        args=(client_socket, client_address),
                        daemon=True
                    )
                    client_thread.start()
                    
                except socket.error as e:
                    if self.running:
                        logger.error(f"Socket error: {e}")
                        
        except Exception as e:
            logger.error(f"Failed to start server: {e}")
            raise
            
    def stop(self):
        """Stop the server and close connections."""
        self.running = False
        if self.socket:
            self.socket.close()
        logger.info("Server stopped")
        
    def _handle_client(self, client_socket: socket.socket, client_address):
        """Handle incoming data from a client connection."""
        try:
            buffer = bytearray()
            total_bytes = 0
            
            while self.running:
                try:
                    data = client_socket.recv(4096)
                    if not data:
                        logger.info(f"Connection closed by {client_address} (total bytes received: {total_bytes})")
                        break
                    
                    total_bytes += len(data)
                    logger.info(f"Received {len(data)} bytes from {client_address} (total: {total_bytes})")
                    logger.info(f"Raw data (hex): {data.hex()}")
                    logger.info(f"Raw data (repr): {repr(data)}")
                    
                    buffer.extend(data)
                    
                    # Process complete messages from buffer
                    while len(buffer) > 0:
                        # Look for SOH (0x01) to start a new message
                        soh_index = buffer.find(0x01)
                        if soh_index == -1:
                            # No SOH found, log and clear buffer
                            if len(buffer) > 0:
                                logger.warning(f"No SOH found in buffer ({len(buffer)} bytes): {buffer.hex()}")
                                logger.warning(f"Buffer content (repr): {repr(buffer)}")
                            buffer.clear()
                            break
                            
                        # Remove any data before SOH
                        if soh_index > 0:
                            logger.warning(f"Dropping {soh_index} bytes before SOH: {buffer[:soh_index].hex()}")
                            buffer = buffer[soh_index:]
                            
                        # Look for ETX (0x03) which marks end of message
                        etx_index = buffer.find(0x03, 1)
                        if etx_index == -1:
                            # Incomplete message, wait for more data
                            logger.debug(f"Incomplete message, waiting for ETX. Current buffer ({len(buffer)} bytes): {buffer.hex()}")
                            break
                            
                        # Extract message (SOH to ETX + LRC byte)
                        if len(buffer) > etx_index + 1:
                            message = bytes(buffer[:etx_index + 2])
                            buffer = buffer[etx_index + 2:]
                            
                            logger.info(f"Extracted complete message ({len(message)} bytes): {message.hex()}")
                            
                            # Add to processing queue
                            self.message_queue.put((message, time.time()))
                        else:
                            # Need LRC byte, wait for more data
                            logger.debug(f"Incomplete message, waiting for LRC byte. Buffer: {buffer.hex()}")
                            break
                            
                except socket.timeout:
                    continue
                except socket.error as e:
                    logger.error(f"Socket error from {client_address}: {e}")
                    break
                    
        except Exception as e:
            logger.error(f"Error handling client {client_address}: {e}")
        finally:
            client_socket.close()
            logger.info(f"Connection to {client_address} closed")
            
    def _process_messages(self):
        """Process messages from the queue."""
        while self.running:
            try:
                message, timestamp = self.message_queue.get(timeout=1.0)
                
                # Parse and validate message
                parsed_data = self.parser.parse_message(message)
                
                if parsed_data:
                    # Output to console and JSON
                    self.output_handler.handle_output(parsed_data)
                else:
                    logger.warning(f"Failed to parse message: {message.hex()}")
                    # Still show raw message in console
                    print("\n" + "!"*60)
                    print("RAW MESSAGE (NOT PARSED)")
                    print("!"*60)
                    print(f"Hex: {message.hex()}")
                    print(f"Length: {len(message)} bytes")
                    print(f"Repr: {repr(message)}")
                    print("!"*60 + "\n")
                    
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Error processing message: {e}")


class BodetCaptureClient:
    """TCP client that connects to a Scorepad acting as server."""

    def __init__(self, target_host: str, target_port: int = 4001):
        """
        Initialize the capture client.

        Args:
            target_host: IP address of the Scorepad to connect to
            target_port: Port number to connect to (default: 4001)
        """
        self.target_host = target_host
        self.target_port = target_port
        self.socket: Optional[socket.socket] = None
        self.running = False
        self.message_queue = queue.Queue()
        self.parser = MessageParser()
        self.output_handler = OutputHandler()

    def start(self):
        """Start the TCP client and connect to the Scorepad."""
        if not self.target_host:
            raise ValueError("Client mode requires target_host in config.ini")

        self.running = True

        # Start message processing thread
        processing_thread = threading.Thread(target=self._process_messages, daemon=True)
        processing_thread.start()

        logger.info(f"Bodet Capture Client starting. Target: {self.target_host}:{self.target_port}")

        while self.running:
            try:
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.socket.settimeout(10.0)
                logger.info(f"Connecting to Scorepad at {self.target_host}:{self.target_port}...")
                self.socket.connect((self.target_host, self.target_port))
                logger.info("Connected to Scorepad (client mode).")

                self._handle_client(self.socket, (self.target_host, self.target_port))

            except (socket.timeout, ConnectionRefusedError) as e:
                logger.warning(f"Connection failed: {e}. Retrying in 5 seconds...")
                time.sleep(5)
            except Exception as e:
                logger.error(f"Client error: {e}")
                time.sleep(5)
            finally:
                if self.socket:
                    try:
                        self.socket.close()
                    except Exception:
                        pass

    def stop(self):
        """Stop the client and close connections."""
        self.running = False
        if self.socket:
            self.socket.close()
        logger.info("Client stopped")

    def _handle_client(self, client_socket: socket.socket, client_address):
        """Handle incoming data from the connected Scorepad."""
        try:
            buffer = bytearray()
            total_bytes = 0

            while self.running:
                try:
                    data = client_socket.recv(4096)
                    if not data:
                        logger.info(f"Connection closed by {client_address} (total bytes received: {total_bytes})")
                        break

                    total_bytes += len(data)
                    logger.info(f"Received {len(data)} bytes from {client_address} (total: {total_bytes})")
                    logger.info(f"Raw data (hex): {data.hex()}")
                    logger.info(f"Raw data (repr): {repr(data)}")

                    buffer.extend(data)

                    # Process complete messages from buffer
                    while len(buffer) > 0:
                        # Look for SOH (0x01) to start a new message
                        soh_index = buffer.find(0x01)
                        if soh_index == -1:
                            # No SOH found, log and clear buffer
                            if len(buffer) > 0:
                                logger.warning(f"No SOH found in buffer ({len(buffer)} bytes): {buffer.hex()}")
                                logger.warning(f"Buffer content (repr): {repr(buffer)}")
                            buffer.clear()
                            break

                        # Remove any data before SOH
                        if soh_index > 0:
                            logger.warning(f"Dropping {soh_index} bytes before SOH: {buffer[:soh_index].hex()}")
                            buffer = buffer[soh_index:]

                        # Look for ETX (0x03) which marks end of message
                        etx_index = buffer.find(0x03, 1)
                        if etx_index == -1:
                            # Incomplete message, wait for more data
                            logger.debug(f"Incomplete message, waiting for ETX. Current buffer ({len(buffer)} bytes): {buffer.hex()}")
                            break

                        # Extract message (SOH to ETX + LRC byte)
                        if len(buffer) > etx_index + 1:
                            message = bytes(buffer[:etx_index + 2])
                            buffer = buffer[etx_index + 2:]

                            logger.info(f"Extracted complete message ({len(message)} bytes): {message.hex()}")

                            # Add to processing queue
                            self.message_queue.put((message, time.time()))
                        else:
                            # Need LRC byte, wait for more data
                            logger.debug(f"Incomplete message, waiting for LRC byte. Buffer: {buffer.hex()}")
                            break

                except socket.timeout:
                    continue
                except socket.error as e:
                    logger.error(f"Socket error from {client_address}: {e}")
                    break

        except Exception as e:
            logger.error(f"Error handling client {client_address}: {e}")
        finally:
            client_socket.close()
            logger.info(f"Connection to {client_address} closed")

    def _process_messages(self):
        """Process messages from the queue."""
        while self.running:
            try:
                message, timestamp = self.message_queue.get(timeout=1.0)

                # Parse and validate message
                parsed_data = self.parser.parse_message(message)

                if parsed_data:
                    # Output to console and JSON
                    self.output_handler.handle_output(parsed_data)
                else:
                    logger.warning(f"Failed to parse message: {message.hex()}")
                    # Still show raw message in console
                    print("\n" + "!"*60)
                    print("RAW MESSAGE (NOT PARSED)")
                    print("!"*60)
                    print(f"Hex: {message.hex()}")
                    print(f"Length: {len(message)} bytes")
                    print(f"Repr: {repr(message)}")
                    print("!"*60 + "\n")

            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Error processing message: {e}")


def load_config() -> tuple:
    """Load configuration from config.ini file."""
    config = ConfigParser()
    try:
        config.read('config.ini')
        mode = config.get('Server', 'mode', fallback='server').strip().lower()
        host = config.get('Server', 'host', fallback='0.0.0.0')
        port = config.getint('Server', 'port', fallback=4001)
        target_host = config.get('Client', 'target_host', fallback='')
        target_port = config.getint('Client', 'target_port', fallback=4001)
        return mode, host, port, target_host, target_port
    except Exception as e:
        logger.warning(f"Could not load config.ini: {e}. Using defaults.")
        return 'server', '0.0.0.0', 4001, '', 4001


def main():
    """Main entry point."""
    try:
        mode, host, port, target_host, target_port = load_config()

        try:
            if mode == 'client':
                client = BodetCaptureClient(target_host=target_host, target_port=target_port)
                client.start()
            else:
                server = BodetCaptureServer(host=host, port=port)
                server.start()
        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
            if mode == 'client':
                client.stop()
            else:
                server.stop()
            
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        raise


if __name__ == '__main__':
    main()
