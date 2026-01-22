"""
Message Parser for Bodet Scorepad Protocol
Handles parsing and validation of messages from the Scorepad.
"""

import logging
import time
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class MessageParser:
    """Parses messages from Bodet Scorepad according to the protocol specification."""
    
    # Protocol constants
    SOH = 0x01  # Start of Heading
    STX = 0x02  # Start of Text
    ETX = 0x03  # End of Text
    ADDRESS = 0x7F  # Default address byte
    
    def __init__(self):
        """Initialize the message parser."""
        self.last_match_data = {}
        
    def parse_message(self, raw_message: bytes) -> Optional[Dict[str, Any]]:
        """
        Parse a raw message from the Scorepad.
        
        Message format: SOH (0x01) + Address (0x7F) + STX (0x02) + DATA + ETX (0x03) + LRC
        
        Args:
            raw_message: Raw bytes received from Scorepad
            
        Returns:
            Parsed data dictionary or None if parsing fails
        """
        if not raw_message or len(raw_message) < 5:
            logger.warning(f"Message too short: {len(raw_message)} bytes")
            return None
            
        # Validate message structure
        if raw_message[0] != self.SOH:
            logger.warning(f"Invalid SOH: expected 0x{self.SOH:02X}, got 0x{raw_message[0]:02X}")
            return None
            
        if raw_message[1] != self.ADDRESS:
            logger.debug(f"Address byte: 0x{raw_message[1]:02X} (expected 0x{self.ADDRESS:02X})")
            
        if raw_message[2] != self.STX:
            logger.warning(f"Invalid STX: expected 0x{self.STX:02X}, got 0x{raw_message[2]:02X}")
            return None
            
        # Find ETX
        etx_index = None
        for i in range(3, len(raw_message)):
            if raw_message[i] == self.ETX:
                etx_index = i
                break
                
        if etx_index is None:
            logger.warning("ETX not found in message")
            return None
            
        # Extract data portion (between STX and ETX)
        data = raw_message[3:etx_index]
        
        # Extract LRC (byte after ETX)
        if len(raw_message) <= etx_index + 1:
            logger.warning("LRC byte missing")
            return None
            
        received_lrc = raw_message[etx_index + 1]
        
        # Validate LRC
        calculated_lrc = self._calculate_lrc(raw_message[1:etx_index + 1])  # Address to ETX
        if received_lrc != calculated_lrc:
            logger.warning(
                f"LRC mismatch: received 0x{received_lrc:02X}, "
                f"calculated 0x{calculated_lrc:02X}"
            )
            # Continue anyway for debugging purposes
            
        # Parse the data portion
        return self._parse_data(data)
        
    def _calculate_lrc(self, data: bytes) -> int:
        """
        Calculate Longitudinal Redundancy Check (LRC).
        
        LRC is calculated as XOR of all bytes from Address to ETX.
        
        Args:
            data: Bytes from Address (0x7F) to ETX (0x03) inclusive
            
        Returns:
            LRC byte value
        """
        lrc = 0
        for byte in data:
            lrc ^= byte
        return lrc & 0xFF
        
    def _parse_data(self, data: bytes) -> Optional[Dict[str, Any]]:
        """
        Parse the data portion of the message.
        
        The format varies by sport. For roller hockey (rink hockey), we need to
        identify the message type and parse accordingly.
        
        Args:
            data: Data bytes between STX and ETX
            
        Returns:
            Dictionary with parsed match data
        """
        if len(data) < 2:
            logger.warning(f"Data too short: {len(data)} bytes")
            return None
            
        # First two bytes typically indicate message type
        # Format varies by sport - we'll start with a generic parser
        # and refine based on actual messages received
        
        message_type = None
        if len(data) >= 2:
            # Try to identify message type
            # Common patterns: first byte might be sport ID, second byte message type
            byte1 = data[0]
            byte2 = data[1] if len(data) > 1 else 0
            
            # For now, log raw data and try basic parsing
            logger.info(f"Received message - Length: {len(data)}, First bytes: {data[:min(10, len(data))].hex()}")
            
            # Try to parse as ASCII where possible
            try:
                ascii_data = data.decode('ascii', errors='ignore')
                logger.info(f"ASCII representation: {repr(ascii_data)}")
            except:
                pass
                
        # Try to identify sport and message type
        # Based on Bodet protocol, first bytes typically indicate:
        # Byte 1: Sport ID or message type indicator
        # Byte 2: Message type (e.g., 0x06 = score, 0x07 = clock, etc.)
        
        parsed = {
            'raw_data': data.hex(),
            'data_length': len(data),
            'message_type': 'unknown',
            'timestamp': time.time()
        }
        
        # Extract individual bytes for analysis
        if len(data) >= 2:
            byte1 = data[0]
            byte2 = data[1]
            
            parsed['byte1'] = f"0x{byte1:02X}"
            parsed['byte2'] = f"0x{byte2:02X}"
            
            # Try to identify message type based on common patterns
            # Roller hockey messages may follow similar patterns to ice hockey or floorball
            # Message types typically: 0x06 (score), 0x07 (clock), 0x08 (penalties), etc.
            
            if byte2 == 0x36:  # '6' in ASCII - often score message
                parsed['message_type'] = 'score'
                parsed.update(self._parse_score_message(data))
            elif byte2 == 0x37:  # '7' in ASCII - often clock message
                parsed['message_type'] = 'clock'
                parsed.update(self._parse_clock_message(data))
            elif byte2 == 0x38:  # '8' in ASCII - often penalties message
                parsed['message_type'] = 'penalties'
                parsed.update(self._parse_penalties_message(data))
            else:
                # Try to parse as generic roller hockey message
                parsed.update(self._parse_roller_hockey_generic(data))
                
        return parsed
        
    def _parse_score_message(self, data: bytes) -> Dict[str, Any]:
        """Parse a score message (type 06)."""
        result = {}
        
        if len(data) >= 10:
            # Typical score message format (varies by sport):
            # Byte 3: Status word
            # Byte 4: Sport ID
            # Byte 5-6: Home score (tens and ones)
            # Byte 7-8: Guest score (tens and ones)
            # Additional bytes may contain period, timeouts, etc.
            
            try:
                # Try to extract scores (may be ASCII digits or binary)
                if len(data) >= 9:
                    # Common pattern: scores as ASCII digits
                    home_tens = data[5] if data[5] >= 0x30 and data[5] <= 0x39 else 0
                    home_ones = data[6] if data[6] >= 0x30 and data[6] <= 0x39 else 0
                    guest_tens = data[7] if data[7] >= 0x30 and data[7] <= 0x39 else 0
                    guest_ones = data[8] if data[8] >= 0x30 and data[8] <= 0x39 else 0
                    
                    home_score = (home_tens - 0x30) * 10 + (home_ones - 0x30) if home_tens >= 0x30 else 0
                    guest_score = (guest_tens - 0x30) * 10 + (guest_ones - 0x30) if guest_tens >= 0x30 else 0
                    
                    result['score'] = {
                        'home': home_score,
                        'guest': guest_score
                    }
            except Exception as e:
                logger.debug(f"Error parsing score: {e}")
                
        return result
        
    def _parse_clock_message(self, data: bytes) -> Dict[str, Any]:
        """Parse a clock/time message (type 07)."""
        result = {}
        
        if len(data) >= 8:
            # Typical clock message format:
            # Byte 3: Status word
            # Byte 4: Sport ID
            # Byte 5-6: Minutes (tens and ones)
            # Byte 7-8: Seconds (tens and ones)
            
            try:
                if len(data) >= 8:
                    # Try ASCII parsing
                    min_tens = data[5] if data[5] >= 0x30 and data[5] <= 0x39 else 0
                    min_ones = data[6] if data[6] >= 0x30 and data[6] <= 0x39 else 0
                    sec_tens = data[7] if data[7] >= 0x30 and data[7] <= 0x39 else 0
                    sec_ones = data[8] if len(data) > 8 and data[8] >= 0x30 and data[8] <= 0x39 else 0
                    
                    if min_tens >= 0x30:
                        minutes = (min_tens - 0x30) * 10 + (min_ones - 0x30) if min_ones >= 0x30 else (min_tens - 0x30)
                        seconds = (sec_tens - 0x30) * 10 + (sec_ones - 0x30) if sec_ones >= 0x30 else (sec_tens - 0x30) if sec_tens >= 0x30 else 0
                        
                        result['time'] = f"{minutes:02d}:{seconds:02d}"
            except Exception as e:
                logger.debug(f"Error parsing clock: {e}")
                
        return result
        
    def _parse_penalties_message(self, data: bytes) -> Dict[str, Any]:
        """Parse a penalties message (type 08)."""
        result = {}
        # Penalties parsing will be implemented based on actual message format
        # For now, return empty structure
        return result
        
    def _parse_roller_hockey_generic(self, data: bytes) -> Dict[str, Any]:
        """Parse generic roller hockey message - attempts basic extraction."""
        result = {}
        
        # Log all bytes for analysis
        byte_info = []
        for i, byte_val in enumerate(data[:min(20, len(data))]):
            byte_info.append(f"Byte[{i}]: 0x{byte_val:02X} ({byte_val})")
            
        result['byte_analysis'] = byte_info
        
        # Try to find ASCII-readable portions
        ascii_parts = []
        for i in range(len(data)):
            if 0x20 <= data[i] <= 0x7E:  # Printable ASCII
                ascii_parts.append(chr(data[i]))
            else:
                if ascii_parts:
                    result['ascii_segments'] = result.get('ascii_segments', [])
                    result['ascii_segments'].append(''.join(ascii_parts))
                    ascii_parts = []
                    
        if ascii_parts:
            result['ascii_segments'] = result.get('ascii_segments', [])
            result['ascii_segments'].append(''.join(ascii_parts))
            
        return result
