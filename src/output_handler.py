"""
Output Handler for Bodet Scorepad Data
Handles console output and JSON file writing for OBS/vMix integration.
"""

import json
import logging
from typing import Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class OutputHandler:
    """Handles output of parsed match data to console and JSON file."""
    
    def __init__(self, json_file: str = 'matchfacts.json'):
        """
        Initialize the output handler.
        
        Args:
            json_file: Path to JSON output file for OBS/vMix
        """
        self.json_file = Path(json_file)
        self.match_data = {
            'score': {
                'home': 0,
                'guest': 0
            },
            'MatchClock': {
                'time': '00:00',
                'period': 1
            },
            'Penalties': {
                'HomeTeam': {
                    'Player1': {
                        'HPP1-active': 0,
                        'HPP1-Time': '00:00'
                    },
                    'Player2': {
                        'HPP2-active': 0,
                        'HPP2-Time': '00:00'
                    }
                },
                'GuestTeam': {
                    'Player1': {
                        'GPP1-active': 0,
                        'GPP1-Time': '00:00'
                    },
                    'Player2': {
                        'GPP2-active': 0,
                        'GPP2-Time': '00:00'
                    }
                }
            }
        }
        
    def handle_output(self, parsed_data: Dict[str, Any]):
        """
        Handle output of parsed data.
        
        Args:
            parsed_data: Dictionary with parsed message data
        """
        # Console output
        self._output_console(parsed_data)
        
        # Update match data structure (will be refined as parser improves)
        self._update_match_data(parsed_data)
        
        # Write JSON file
        self._write_json()
        
    def _output_console(self, parsed_data: Dict[str, Any]):
        """Output parsed data to console."""
        print("\n" + "="*70)
        print(">>> BODET SCOREPAD MESSAGE RECEIVED <<<")
        print("="*70)
        
        # Print timestamp
        import datetime
        print(f"Timestamp: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")
        
        # Print raw data info
        if 'raw_data' in parsed_data:
            print(f"\nRaw Data (hex): {parsed_data['raw_data']}")
            print(f"Data Length: {parsed_data['data_length']} bytes")
            
        # Print individual bytes if available
        if 'byte1' in parsed_data or 'byte2' in parsed_data:
            print("\n--- Message Header ---")
            for i in range(1, 5):
                key = f'byte{i}'
                if key in parsed_data:
                    print(f"  {key.upper()}: {parsed_data[key]}")
                
        # Print message type
        msg_type = parsed_data.get('message_type', 'unknown')
        print(f"\nMessage Type: {msg_type.upper()}")
        
        # Print match data if available
        has_match_data = False
        if 'score' in parsed_data:
            score = parsed_data['score']
            if 'home' in score or 'guest' in score:
                if not has_match_data:
                    print("\n--- Match Data ---")
                    has_match_data = True
                print(f"  Score - Home: {score.get('home', 0)}, Guest: {score.get('guest', 0)}")
                
        if 'time' in parsed_data:
            if not has_match_data:
                print("\n--- Match Data ---")
                has_match_data = True
            print(f"  Time: {parsed_data['time']}")
            
        if 'period' in parsed_data:
            if not has_match_data:
                print("\n--- Match Data ---")
                has_match_data = True
            print(f"  Period: {parsed_data['period']}")
        
        # Print byte analysis if available (for debugging)
        if 'byte_analysis' in parsed_data:
            print("\n--- Byte Analysis ---")
            for byte_info in parsed_data['byte_analysis'][:10]:  # Limit to first 10
                print(f"  {byte_info}")
            if len(parsed_data['byte_analysis']) > 10:
                print(f"  ... ({len(parsed_data['byte_analysis']) - 10} more bytes)")
                
        print("="*70 + "\n")
        
    def _update_match_data(self, parsed_data: Dict[str, Any]):
        """
        Update internal match data structure.
        
        This will be expanded as we understand the roller hockey message format better.
        
        Args:
            parsed_data: Parsed message data
        """
        # For now, just store the raw parsed data
        # This will be refined once we understand the message format
        if 'score' in parsed_data:
            self.match_data['score'] = parsed_data['score']
        if 'time' in parsed_data:
            self.match_data['MatchClock']['time'] = parsed_data['time']
        if 'period' in parsed_data:
            self.match_data['MatchClock']['period'] = parsed_data['period']
            
    def _write_json(self):
        """Write match data to JSON file for OBS/vMix."""
        try:
            with open(self.json_file, 'w', encoding='utf-8') as f:
                json.dump(self.match_data, f, indent=4, ensure_ascii=False)
            logger.debug(f"Updated {self.json_file}")
        except Exception as e:
            logger.error(f"Failed to write JSON file: {e}")
