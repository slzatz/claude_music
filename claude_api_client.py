"""
Direct Claude API client for reliable music request processing.

This module provides direct access to Claude's API for music parsing and selection,
eliminating the mock response issues that occur with Claude Code's Task function.
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

try:
    import anthropic
    from anthropic import APIError, APITimeoutError, RateLimitError
except ImportError:
    raise ImportError("anthropic package not found. Install with: uv pip install anthropic")

try:
    from dotenv import load_dotenv
    load_dotenv()  # Load environment variables from .env file
except ImportError:
    pass  # dotenv is optional

# Import existing prompt templates
try:
    from music_parsing_prompts import STANDARD_MUSIC_PARSING_PROMPT, format_result_selection_prompt
except ImportError:
    # Fallback prompt if module not available
    STANDARD_MUSIC_PARSING_PROMPT = """
Parse the following natural language music request into structured components:

"{request}"

Return ONLY a valid JSON object with exactly these keys: title, artist, preferences
- title: The song title (clean, lowercase, no annotations)
- artist: The artist name (clean, no possessives, or null if not specified)  
- preferences: Dictionary with boolean flags for user preferences

Examples:
- "Neil Young's Harvest" → {{"title": "harvest", "artist": "neil young", "preferences": {{}}}}
- "play a live version of harvest" → {{"title": "harvest", "artist": null, "preferences": {{"prefer_live": true}}}}

Do not include any explanatory text. Return only the raw JSON.
"""


def log_progress(message: str):
    """Log progress to file for monitoring."""
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    log_message = f"[{timestamp}] 🎵 API {message}"
    
    try:
        log_file = os.path.expanduser(".claude_music_progress.log")
        with open(log_file, "a") as f:
            f.write(log_message + "\n")
            f.flush()
    except:
        pass  # Don't fail if we can't write to file


class ClaudeAPIClient:
    """
    Direct Claude API client for music request processing.
    
    This client provides reliable LLM capabilities without the unpredictable 
    behavior of Claude Code's Task function.
    """
    
    def __init__(self, api_key: Optional[str] = None, model: str = "claude-3-5-sonnet-20241022"):
        """
        Initialize the Claude API client.
        
        Args:
            api_key: Anthropic API key (if None, will look for ANTHROPIC_API_KEY env var)
            model: Claude model to use for requests
        """
        self.api_key = api_key or os.getenv('ANTHROPIC_API_KEY')
        self.model = model
        
        if not self.api_key:
            raise ValueError(
                "No API key provided. Either pass api_key parameter or set ANTHROPIC_API_KEY environment variable. "
                "Get your key from: https://console.anthropic.com/account/keys"
            )
        
        self.client = anthropic.Anthropic(api_key=self.api_key)
        log_progress("🔌 API client initialized successfully")
    
    
    def parse_music_request(self, request: str) -> Dict[str, Any]:
        """
        Parse a natural language music request using Claude API.
        
        Args:
            request: Natural language music request
            
        Returns:
            Dict with parsed components: {'title': str, 'artist': str|None, 'preferences': dict}
        """
        try:
            log_progress(f"🎯 Parsing request: '{request[:50]}...'")
            
            # Format the prompt with the actual request
            prompt = STANDARD_MUSIC_PARSING_PROMPT.format(request=request)
            
            # Add extra instructions to ensure JSON-only response
            full_prompt = f"""IMPORTANT: Return ONLY valid JSON, no explanatory text.

{prompt}

Remember: Return ONLY the JSON object, nothing else."""
            
            # Call Claude API directly
            response = self.client.messages.create(
                model=self.model,
                max_tokens=200,
                temperature=0.0,  # Deterministic parsing
                messages=[{"role": "user", "content": full_prompt}]
            )
            
            response_text = response.content[0].text.strip()
            log_progress(f"📝 API response: '{response_text[:100]}...'")
            
            # Parse the JSON response
            try:
                parsed_result = json.loads(response_text)
                log_progress("✅ Successfully parsed JSON response")
                
                # Validate the response structure
                if not isinstance(parsed_result, dict):
                    raise ValueError("Response is not a JSON object")
                
                # Ensure required keys exist
                if 'title' not in parsed_result:
                    raise ValueError("Missing 'title' in response")

                other_keys = ['artist', 'preferences']
                for key in other_keys:
                    if key not in parsed_result:
                        parsed_result[key] = None if key == 'artist' else {}
                
                return parsed_result
                
            except json.JSONDecodeError as e:
                log_progress(f"❌ JSON parsing failed: {str(e)}")
                log_progress(f"Raw response: '{response_text}'")
                
                # Try to extract information using regex as fallback
                return self._fallback_parse(request, response_text)
                
        except APIError as e:
            log_progress(f"❌ API error: {str(e)}")
            return {
                'error': f'API error: {str(e)}',
                'original_request': request
            }
        except Exception as e:
            log_progress(f"❌ Unexpected error: {str(e)}")
            return {
                'error': f'Parsing failed: {str(e)}',
                'original_request': request
            }
    
    def select_best_track(self, results: List[Dict], target_title: str, 
                         target_artist: str = None, preferences: Dict = None) -> Optional[int]:
        """
        Use Claude API to select the best track from search results.
        
        This replaces the unreliable Task function calls for result selection.
        
        Args:
            results: List of search results with position, title, artist, album
            target_title: Target song title
            target_artist: Target artist name (optional)
            preferences: User preferences dict (optional)
            
        Returns:
            Position number of best match, or None if no good match
        """
        if not results:
            return None
            
        try:
            log_progress(f"🎯 Selecting best track from {len(results)} results")
            
            # Use existing prompt template if available
            try:
                prompt = format_result_selection_prompt(
                    title=target_title,
                    artist=target_artist,
                    preferences=preferences or {},
                    results=results
                )
            except (NameError, ImportError):
                # Fallback prompt if template not available
                prompt = self.create_selection_prompt(results, target_title, target_artist, preferences)
            
            if not prompt:
                log_progress("❌ Could not create selection prompt")
                return None
            
            # Add instructions for numeric response
            full_prompt = f"""{prompt}

IMPORTANT: Return ONLY the position number (integer), no explanation or other text."""
            
            # Call Claude API
            response = self.client.messages.create(
                model=self.model,
                max_tokens=10,
                temperature=0.0,  # Deterministic selection
                messages=[{"role": "user", "content": full_prompt}]
            )
            
            response_text = response.content[0].text.strip()
            log_progress(f"📝 Selection response: '{response_text}'")
            
            # Parse the position number
            try:
                position = int(response_text.split()[0])  # Get first number
                
                # Validate position is in results
                valid_positions = [r.get('position') for r in results if 'position' in r]
                if position in valid_positions:
                    log_progress(f"✅ Selected position: {position}")
                    return position
                else:
                    log_progress(f"❌ Invalid position {position}, valid positions: {valid_positions[:5]}")
                    return None
                    
            except (ValueError, IndexError) as e:
                log_progress(f"❌ Could not parse position from: '{response_text}' - {str(e)}")
                return None
                
        except APIError as e:
            log_progress(f"❌ API error in selection: {str(e)}")
            return None
        except Exception as e:
            log_progress(f"❌ Unexpected error in selection: {str(e)}")
            return None
    
    def _fallback_parse(self, request: str, api_response: str) -> Dict[str, Any]:
        """
        Fallback parsing when API returns non-JSON response.
        
        Attempts to extract useful information from the API response,
        then falls back to simple regex parsing.
        """
        log_progress("🔄 Attempting fallback parsing...")
        
        # Try to extract JSON from the API response text
        import re
        
        # Look for JSON-like structures in the response
        json_match = re.search(r'\{[^}]*"title"[^}]*\}', api_response)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
        
        # Regex fallback if API response is unusable
        request_lower = request.lower().strip()
        
        # Remove common prefixes
        request_lower = re.sub(r'^(play\s+|i\s+want\s+to\s+hear\s+|put\s+on\s+)', '', request_lower)
        request_lower = re.sub(r'\s+', ' ', request_lower).strip()
        
        # Simple preferences detection
        preferences = {}
        if re.search(r'\blive\s+(version|recording)', request_lower):
            preferences['prefer_live'] = True
        elif re.search(r'\bacoustic\s+version', request_lower):
            preferences['prefer_acoustic'] = True
        
        # Simple "by" pattern
        by_match = re.search(r'^(.+?)\s+by\s+(.+)$', request_lower)
        if by_match:
            return {
                'title': by_match.group(1).strip(),
                'artist': by_match.group(2).strip(),
                'preferences': preferences
            }
        
        # Simple possessive pattern
        poss_match = re.search(r"^(.+?)'s\s+(.+)$", request_lower)
        if poss_match:
            return {
                'title': poss_match.group(2).strip(),
                'artist': poss_match.group(1).strip(),
                'preferences': preferences
            }
        
        # Fallback: treat as title only
        return {
            'title': request_lower,
            'artist': None,
            'preferences': preferences
        }
    
    def create_selection_prompt(self, results: List[Dict], title: str, 
                               artist: str = None, preferences: Dict = None) -> str:
        """
        Create a fallback selection prompt if the template is not available.
        """
        if not results:
            return ""
        
        artist_text = artist if artist else "unknown artist"
        preferences_text = "no specific preferences"
        
        if preferences:
            prefs = []
            if preferences.get('prefer_live'):
                prefs.append('live version')
            if preferences.get('prefer_acoustic'):
                prefs.append('acoustic version')
            if preferences.get('prefer_studio'):
                prefs.append('studio version')
            if prefs:
                preferences_text = ", ".join(prefs)
        
        # Format results list
        results_lines = []
        for result in results:
            pos = result.get('position', '?')
            title_text = result.get('title', 'Unknown')
            artist_text_result = result.get('artist', 'Unknown')
            album = result.get('album', 'Unknown')
            results_lines.append(f"{pos}. {title_text} - {artist_text_result} - {album}")
        
        results_list = "\n".join(results_lines)
        
        return f"""You are a music expert selecting the best track from search results.

TARGET: "{title}" by {artist_text}
PREFERENCES: {preferences_text}

SEARCH RESULTS:
{results_list}

Select the position number (1-{len(results)}) that best matches the request.
Prefer: exact title matches, correct artist, original albums over compilations.

Return only the position number."""

    def test_connection(self) -> Dict[str, Any]:
        """
        Test the API connection with a simple request.
        
        Returns:
            Dict with success status and details
        """
        try:
            log_progress("🧪 Testing API connection...")
            response = self.client.messages.create(
                model=self.model,
                max_tokens=10,
                messages=[{"role": "user", "content": "Hello"}]
            )
            log_progress("✅ API connection test successful")
            return {
                'success': True,
                'message': 'API connection successful',
                'model': self.model,
                'response_length': len(response.content[0].text)
            }
        except Exception as e:
            log_progress(f"❌ API connection test failed: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'message': 'API connection failed'
            }

# Convenience function to get an api client - not currently in use
def get_api_client() -> ClaudeAPIClient:
    """
    Get a configured Claude API client.
    
    Checks for API key in environment variables and creates client.
    
    Returns:
        ClaudeAPIClient instance
        
    Raises:
        ValueError: If no API key is found
    """
    return ClaudeAPIClient()

# Convenience functions that match the existing interface
if __name__ == "__main__":
    # Test the API client
    try:
        client = get_api_client()
        
        # Test connection
        connection_test = client.test_connection()
        print("Connection test:", connection_test)
        
        if connection_test['success']:
            # Test parsing
            test_requests = [
                "ani difranco's fixing her hair",
                "play harvest by neil young",
                "I'd like to hear a live version of comfortably numb"
            ]
            
            for request in test_requests:
                print(f"\nTesting: '{request}'")
                result = client.parse_music_request(request)
                print(f"Result: {result}")
                
    except Exception as e:
        print(f"Error: {e}")
        print("Make sure to set your ANTHROPIC_API_KEY environment variable")
