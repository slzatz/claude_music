"""
Simple interface for Claude Code to handle music requests using the intelligent agent.

This module provides a clean, easy-to-use interface that Claude Code can invoke
to handle natural language music requests without needing to understand the
internal workings of the agent.
"""

# Unified MusicAgent class - contains all functionality previously split between base and derived classes
from typing import Optional, Dict, Any, List, Tuple
import json
import sys
import os
import re
import traceback
import subprocess
from datetime import datetime


def log_progress(message: str):
    """Log progress to file for headless mode monitoring."""
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]  # HH:MM:SS.mmm format
    log_message = f"[{timestamp}] 🎵 {message}"
    
    # Write to log file for headless mode monitoring
    try:
        log_file = os.path.expanduser(".claude_music_progress.log")
        with open(log_file, "a") as f:
            f.write(log_message + "\n")
            f.flush()
    except:
        pass  # Don't fail if we can't write to file

def handle_music_request(user_request: str, api_client=None, verbose: bool = False) -> str:
    """
    Complete end-to-end music request handler using Claude API.
    
    This is the main entry point that provides reliable LLM-powered music processing
    without the mock response issues of the Task function approach.
    
    Args:
        user_request: Natural language music request (e.g., "play Bruce Springsteen's Thunder Road")
        api_client: Optional Claude API client (will create one if not provided)
        verbose: Whether to return detailed information about the process
        
    Returns:
        Human-readable message about the result
        
    Example:
        result = handle_music_request("play Bruce Springsteen's Thunder Road")
    """
    try:
        start_time = datetime.now()
        
        # Show process info for debugging
        import os
        pid = os.getpid()
        log_progress(f"🎯 [API] Processing music request: '{user_request}' (PID: {pid})")
        
        # Step 1: Create agent with API client
        log_progress("Step 1: Create agent with API client")
        agent = MusicAgent(api_client=api_client)
        
        # Step 2: Parse the natural language request using API
        log_progress("Step 2: Parse the natural language request using API")
        parsed = agent.parse_music_request(user_request)
        
        # Handle parsing errors
        if 'error' in parsed:
            log_progress(f"Parsing failed: {parsed['error']}")
            return f"❌ Could not understand request: {parsed['error']}"
        
        log_progress(f"Parsed: title='{parsed['title']}', artist='{parsed.get('artist', 'none')}'")
        
        # Step 3: Generate queries, search, match and play 
        log_progress("Step 3: Generate queries, search, match and play")
        result = agent.search_match_play(
            parsed['title'], 
            parsed['artist'], 
            parsed['preferences']
        )
        
        # Calculate total time
        elapsed = (datetime.now() - start_time).total_seconds()
        log_progress(f"Completed in {elapsed:.2f} seconds")
        
        # Convert agent result to user-friendly message
        if result['success']:
            if verbose:
                details = result.get('details', {})
                message = result['message']
                if 'search_query_used' in details:
                    message += f"\n(Used search query: '{details['search_query_used']}')"
                if 'total_results' in details:
                    message += f"\n(Found {details['total_results']} total results)"
                return message
            else:
                return result['message']
        else:
            if verbose:
                error_details = result.get('details', {})
                message = result['message']
                if 'queries_tried' in error_details:
                    message += f"\n(Tried {len(error_details['queries_tried'])} different search queries)"
                return f"❌ {message}"
            else:
                return f"❌ {result['message']}"
        
    except Exception as e:
        elapsed = (datetime.now() - start_time).total_seconds() if 'start_time' in locals() else 0
        log_progress(f"Failed after {elapsed:.2f} seconds: {str(e)}")
        return f"❌ Unexpected error processing music request: {str(e)}"


def _fallback_simple_parse(user_request: str) -> Dict[str, Any]:
    """
    Simple fallback parsing when LLM parsing fails.
    
    This handles basic patterns like "song by artist" and "artist's song".
    """
    request_lower = user_request.lower().strip()
    
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


class MusicAgent:
    """
    Unified intelligent agent for natural language music requests.
    
    This agent integrates both programmatic and LLM-powered capabilities:
    - Uses Claude API for parsing and intelligent selection when available
    - Falls back to algorithmic methods when API client is unavailable
    - Handles Sonos CLI integration for music playback
    """
    
    def __init__(self, api_client=None):
        """
        Initialize the music agent.
        
        Args:
            api_client: Optional Claude API client for LLM capabilities.
                       If None, will attempt to create one, falling back to programmatic-only mode.
        """
        # Initialize core state
        self.last_search_results = []
        
        # Initialize API client for LLM capabilities
        if api_client is None:
            try:
                from claude_api_client import get_api_client
                api_client = get_api_client()
            except Exception as e:
                log_progress(f"❌ Could not initialize API client: {e}")
                api_client = None
        self.api_client = api_client
    
    # ============================================================================
    # Core Infrastructure Methods (Sonos CLI Integration)
    # ============================================================================
    
    def execute_sonos_command(self, command: List[str]) -> Dict[str, Any]:
        """
        Execute a sonos CLI command and return the result.
        
        Args:
            command: List of command parts (e.g., ['sonos', 'searchtrack', 'harvest', 'neil', 'young'])
            
        Returns:
            Dict containing 'success', 'output', and 'error' keys
        """
        start_time = datetime.now()
        command_str = ' '.join(command)
        log_progress(f"Executing: {command_str}")
        
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            elapsed = (datetime.now() - start_time).total_seconds()
            if result.returncode == 0:
                log_progress(f"Command completed ({elapsed:.2f}s)")
            else:
                log_progress(f"Command failed ({elapsed:.2f}s): {result.stderr.strip() if result.stderr else 'Unknown error'}")
            
            return {
                'success': result.returncode == 0,
                'output': result.stdout.strip(),
                'error': result.stderr.strip() if result.stderr else None
            }
            
        except subprocess.TimeoutExpired:
            elapsed = (datetime.now() - start_time).total_seconds()
            log_progress(f"Command timed out ({elapsed:.2f}s)")
            return {
                'success': False,
                'output': '',
                'error': 'Command timed out after 30 seconds'
            }
        except Exception as e:
            elapsed = (datetime.now() - start_time).total_seconds()
            log_progress(f"Command error ({elapsed:.2f}s): {str(e)}")
            return {
                'success': False,
                'output': '',
                'error': str(e)
            }
    
    def parse_search_results(self, search_output: str) -> List[Dict[str, Any]]:
        """
        Parse sonos searchtrack output into structured data.
        
        Args:
            search_output: Raw output from sonos searchtrack command
            
        Returns:
            List of track dictionaries with position, title, artist, album
        """
        log_progress("Parse_search_results")
        results = []
        lines = search_output.strip().split('\n')
        
        for line in lines:
            # Match pattern: "number. Title-Artist-Album"
            # Note that LLM could probably just use raw_line but algorithmic
            # matching requires structured fields.
            match = re.match(r'^(\d+)\.\s+(.+?)-(.+?)-(.+)$', line.strip())
            if match:
                results.append({
                    'position': int(match.group(1)),
                    'title': match.group(2).strip(),
                    'artist': match.group(3).strip(),
                    'album': match.group(4).strip(),
                    'raw_line': line.strip()
                })
            else:
                # Fallback for old format without album
                old_match = re.match(r'^(\d+)\.\s+(.+?)-(.+)$', line.strip())
                if old_match:
                    results.append({
                        'position': int(old_match.group(1)),
                        'title': old_match.group(2).strip(),
                        'artist': old_match.group(3).strip(),
                        'album': 'Unknown Album',
                        'raw_line': line.strip()
                    })
        
        return results
        
    def get_current_track_info(self) -> Dict[str, Any]:
        """Get information about currently playing track."""
        result = self.execute_sonos_command(['sonos', 'what'])
        return result
    
    def play_track_by_position(self, position: int) -> Dict[str, Any]:
        """Play a track by its position from the last search results."""
        result = self.execute_sonos_command(['sonos', 'playtrackfromlist', str(position)])
        return result

    # ============================================================================
    # Parsing Methods (API-powered with fallback)
    # ============================================================================
    
    def parse_music_request(self, request: str) -> Dict[str, Any]:
        """
        Parse a natural language music request using Claude API.
        
        This method uses direct API calls for reliable, consistent parsing
        when API client is available, otherwise falls back to simple regex parsing.
        
        Args:
            request: Natural language music request (e.g., "play Bruce Springsteen's Thunder Road")
            
        Returns:
            Dict with parsed components: {'title': str, 'artist': str|None, 'preferences': dict}
        """
        if not self.api_client:
            log_progress("❌ No API client available - falling back to simple parsing")
            return _fallback_simple_parse(request)
        
        log_progress(f"🎯 Parsing with API: '{request[:50]}...'")
        
        try:
            # Use the API client for reliable parsing
            result = self.api_client.parse_music_request(request)
            
            # Check for API errors
            if 'error' in result:
                log_progress(f"❌ API parsing error: {result['error']}")
                log_progress("🔄 Falling back to simple regex parsing")
                return _fallback_simple_parse(request)
            
            log_progress("✅ API parsing completed successfully")
            return result
            
        except Exception as e:
            log_progress(f"❌ Unexpected error in API parsing: {str(e)}")
            log_progress("🔄 Falling back to simple regex parsing")
            return _fallback_simple_parse(request)

    # ============================================================================
    # LLM-Powered Selection Method (when API available)
    # ============================================================================
    
    def llm_select_best_match(self, results, target_title: str, 
                              target_artist: str = None, preferences = None):
        """
        Use Claude API for reliable LLM-powered result selection.
        
        This method now uses direct API calls for consistent selection behavior
        without the mock response issues of the Task function approach.
        """
        if not self.api_client:
            log_progress("❌ No API client available for LLM selection")
            return None
            
        log_progress(f"🎯 Using API for track selection from {len(results)} results")
        
        try:
            # Use the API client for reliable selection
            position = self.api_client.select_best_track(
                results=results,
                target_title=target_title, 
                target_artist=target_artist,
                preferences=preferences or {}
            )
            
            if position:
                log_progress(f"✅ API selected position: {position}")
                return position
            else:
                log_progress("❌ API selection returned no result")
                return None
                
        except Exception as e:
            log_progress(f"❌ API selection error: {str(e)}")
            return None

    # ============================================================================
    # Programmatic Matching Methods (algorithmic fallback)
    # ============================================================================
    
    def _calculate_similarity(self, str1: str, str2: str) -> float:
        """Calculate simple similarity between two strings."""
        from difflib import SequenceMatcher
        return SequenceMatcher(None, str1, str2).ratio()
        
    def _clean_for_matching(self, text: str) -> str:
        """Clean text for better matching by removing noise and normalizing."""
        if not text:
            return ""
            
        # Remove common annotations
        text = re.sub(r'\s*\(\d{4}\s*remaster(ed)?\)', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\s*\(live.*?\)', '', text, flags=re.IGNORECASE) 
        text = re.sub(r'\s*\[explicit\]', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\s*-\s*live\s*$', '', text, flags=re.IGNORECASE)
        
        # Normalize whitespace and case
        text = re.sub(r'\s+', ' ', text.lower().strip())
        return text
        
    def _normalize_for_exact_match(self, text: str) -> str:
        """Normalize text for exact matching by removing all punctuation and extra spaces."""
        if not text:
            return ""
        
        # Remove all punctuation and normalize spacing
        normalized = re.sub(r'[^\w\s]', '', text.lower())
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        return normalized

    def _detect_live_version(self, title: str, album: str) -> bool:
        """Detect if a track is a live version based on title and album context."""
        live_patterns = [
            r'\blive\b', r'\bconcert\b', r'live\s+from', r'live\s+at', r'artists\s+den',
            r'live\s+recording', r'concert\s+version'
        ]
        
        text_to_check = f"{title} {album}".lower()
        return any(re.search(pattern, text_to_check) for pattern in live_patterns)
    
    def _detect_acoustic_version(self, title: str, album: str) -> bool:
        """Detect if a track is an acoustic version based on title and album context."""
        acoustic_patterns = [
            r'\bacoustic\b', r'\bunplugged\b', r'acoustic\s+version',
            r'stripped', r'solo\s+acoustic'
        ]
        
        text_to_check = f"{title} {album}".lower()
        return any(re.search(pattern, text_to_check) for pattern in acoustic_patterns)

    def _calculate_match_score(self, result: Dict[str, Any], target_title: str, 
                             target_artist: str, prefer_live: bool, prefer_acoustic: bool, prefer_studio: bool) -> float:
        """
        Calculate a comprehensive match score for a search result.
        
        Considers multiple factors:
        - Title similarity (exact vs fuzzy matching)
        - Artist similarity (if provided)  
        - Live/acoustic/studio preference matching
        - Album context for version detection
        - Quality indicators (explicit, remaster, etc.)
        """
        title_clean = self._clean_for_matching(result['title'])
        artist_clean = self._clean_for_matching(result['artist'])
        album_clean = self._clean_for_matching(result['album'])
        
        # Base title similarity score
        if title_clean == target_title:
            title_score = 1.0  # Exact match
        else:
            title_score = self._calculate_similarity(title_clean, target_title)
            
            # Special handling for exact matches with different spacing/punctuation
            if self._normalize_for_exact_match(title_clean) == self._normalize_for_exact_match(target_title):
                title_score = 1.0
        
        # Artist matching score
        artist_score = 0.0
        if target_artist:
            if artist_clean == target_artist:
                artist_score = 1.0
            else:
                artist_score = self._calculate_similarity(artist_clean, target_artist)
                # Bonus for partial name matches
                if target_artist in artist_clean or artist_clean in target_artist:
                    artist_score = max(artist_score, 0.8)
        
        # Version type detection and scoring
        is_live_track = self._detect_live_version(result['title'], result['album'])
        is_acoustic_track = self._detect_acoustic_version(result['title'], result['album'])
        is_studio_track = not is_live_track and not is_acoustic_track  # Studio is default
        
        version_score = 0.0
        
        if prefer_live:
            if is_live_track:
                version_score = 0.3  # Significant bonus for live versions when requested
            else:
                version_score = -0.1  # Small penalty when live requested but not found
        elif prefer_acoustic:
            if is_acoustic_track:
                version_score = 0.3  # Significant bonus for acoustic versions when requested
            else:
                version_score = -0.1  # Small penalty when acoustic requested but not found
        elif prefer_studio:
            if is_studio_track:
                version_score = 0.2  # Bonus for studio when specifically requested
            else:
                version_score = -0.1  # Penalty when studio requested but not found
        else:
            # Default preference: slightly prefer studio versions
            if is_studio_track:
                version_score = 0.1  # Small bonus for studio
            elif is_live_track:
                version_score = -0.05  # Very small penalty for live when not requested
            else:  # acoustic
                version_score = 0.05  # Neutral for acoustic
        
        # Combine scores
        if target_artist:
            combined_score = (title_score * 0.6) + (artist_score * 0.3) + version_score + 0.1
        else:
            combined_score = (title_score * 0.8) + version_score + 0.2
        
        return max(0.0, min(1.0, combined_score))

    def _get_programmatic_scores(self, results: List[Dict[str, Any]], target_title: str, 
                               target_artist: str, preferences: Dict[str, Any]) -> List[Tuple[int, float, Dict]]:
        """Get programmatic scores for all results."""
        prefer_live = preferences.get('prefer_live', False)
        prefer_acoustic = preferences.get('prefer_acoustic', False)
        prefer_studio = preferences.get('prefer_studio', False)
        
        scored_matches = []
        target_title_clean = self._clean_for_matching(target_title)
        target_artist_clean = self._clean_for_matching(target_artist) if target_artist else None
        
        for result in results:
            score = self._calculate_match_score(
                result, target_title_clean, target_artist_clean, prefer_live, prefer_acoustic, prefer_studio
            )
            
            if score > 0.3:  # Minimum viable match threshold
                scored_matches.append((result['position'], score, result))
        
        return scored_matches
    
    def select_best_match(self, results, target_title: str, target_artist: str = None, preferences = None):
        """
        Hybrid intelligent selection using both LLM and programmatic approaches.
        
        Uses LLM selection when available and complexity indicators suggest benefit,
        falls back to programmatic selection otherwise.
        """
        log_progress("select_best_match")
        log_progress("Search Results:")
        log_progress('\n                  '.join([f"{r['position']}: {r['title']}, {r['artist']}, {r['album']}" for r in results]))
        if not results:
            return None
            
        preferences = preferences or {}
        
        # First, get programmatic scores for all results
        programmatic_matches = self._get_programmatic_scores(results, target_title, target_artist, preferences)
        
        if not programmatic_matches:
            return None
        
        # Determine if we should use LLM selection
        if self.api_client: #and self._should_use_llm_selection(programmatic_matches, preferences):
            try:
                log_progress("Using LLM to select best match...")
                llm_selection = self.llm_select_best_match(results, target_title, target_artist, preferences)
                if llm_selection:
                    log_progress("LLM selection completed")
                    return llm_selection
                else:
                    log_progress("LLM selection returned no result, using programmatic fallback")
            except Exception as e:
                # Fallback to programmatic if LLM fails
                log_progress(f"LLM selection failed ({e}), falling back to programmatic selection")

        # Use programmatic selection
        log_progress("Using programmatic selection")
        best_match = max(programmatic_matches, key=lambda x: x[1])
        return best_match[0]  # Return position


    def _should_use_llm_selection(self, programmatic_matches, preferences):
        """
        Determine if we should use LLM selection based on complexity indicators.
        
        Use LLM when:
        - Multiple good matches (ambiguous choice)
        - No clear programmatic winner
        - Complex preferences that might need contextual understanding
        """
        if not programmatic_matches:
            return False
        
        # Sort by score
        programmatic_matches_sorted = sorted(programmatic_matches, key=lambda x: x[1], reverse=True)
        top_score = programmatic_matches_sorted[0][1]
        
        # Count strong matches (score > 0.7)
        strong_matches = [m for m in programmatic_matches if m[1] > 0.7]
        
        # Use LLM if:
        use_llm = (
            len(strong_matches) >= 3 or  # Multiple good matches
            top_score < 0.8 or  # No clear winner
            self._has_complex_preferences(preferences) or  # Complex requirements
            self._has_ambiguous_albums(programmatic_matches)  # Album names need interpretation
        )
        
        return use_llm
    
    def _has_complex_preferences(self, preferences):
        """Check if preferences require contextual understanding."""
        # Multiple preferences (e.g., acoustic AND live)
        active_prefs = sum(1 for v in preferences.values() if v)
        return active_prefs >= 2
    
    def _has_ambiguous_albums(self, matches):
        """Check if album names might need LLM interpretation."""
        ambiguous_patterns = [
            'greatest hits', 'best of', 'collection', 'anthology',
            'deluxe', 'remaster', 'anniversary', 'special edition'
        ]
        
        for _, _, result in matches:
            album_lower = result['album'].lower()
            if any(pattern in album_lower for pattern in ambiguous_patterns):
                return True
        return False

    # ============================================================================
    # Search Query Generation Methods
    # ============================================================================
    
    def generate_search_queries(self, title: str, artist: str = None, preferences: Dict[str, Any] = None) -> List[str]:
        """
        Generate intelligent search queries with fallback strategies for API issues.
        
        Specifically handles the "fixing her hair" API parsing issue by using
        alternative query formats that avoid the problematic pattern.
        
        Args:
            title: Song title
            artist: Artist name (optional)
            preferences: Search preferences
            
        Returns:
            Ordered list of search query strings to try
        """
        log_progress("generate_search_queries")
        preferences = preferences or {}
        queries = []
        
        # Strategy for handling known API issues
        # "fixing her hair" fails, but "fixing hair" works
        title_variants = [title]
        
        # Create abbreviated versions that might avoid API issues
        if len(title.split()) > 2:
            # Try removing small words that might cause parsing issues
            title_no_articles = re.sub(r'\b(the|a|an|her|his|my|your|our|their)\b', '', title, flags=re.IGNORECASE)
            title_no_articles = re.sub(r'\s+', ' ', title_no_articles).strip()
            if title_no_articles and title_no_articles != title:
                title_variants.append(title_no_articles)
        
        # Generate queries for each title variant
        for title_var in title_variants:
            if artist:
                # Primary search strategies
                queries.extend([
                    f"{title_var} by {artist}",
                    f"{title_var} {artist}",
                    f"{artist} {title_var}"
                ])
                
                # Handle version preferences
                if preferences.get('prefer_live'):
                    queries.insert(0, f"live {title_var} {artist}")
                    queries.insert(1, f"{title_var} live {artist}")
                    queries.insert(2, f"{artist} {title_var} live")
                elif preferences.get('prefer_acoustic'):
                    queries.insert(0, f"acoustic {title_var} {artist}")
                    queries.insert(1, f"{title_var} acoustic {artist}")
                    queries.insert(2, f"{artist} {title_var} acoustic")
                elif preferences.get('prefer_studio'):
                    queries.insert(0, f"studio {title_var} {artist}")
                    queries.insert(1, f"{title_var} studio {artist}")
                
                # Fallback: just artist name (to find any songs by them)
                queries.append(artist)
                
            else:
                # No artist specified
                queries.append(title_var)
                
                if preferences.get('prefer_live'):
                    queries.insert(0, f"live {title_var}")
                    queries.insert(1, f"{title_var} live")
                elif preferences.get('prefer_acoustic'):
                    queries.insert(0, f"acoustic {title_var}")
                    queries.insert(1, f"{title_var} acoustic")
                elif preferences.get('prefer_studio'):
                    queries.insert(0, f"studio {title_var}")
        
        return queries

    def get_album_for_song(self, title: str, artist: str = None) -> str:
        """
        Use Claude API to identify the primary album that contains a specific song.
        
        This method is called when API parsing fails, allowing us to search by album
        instead of song title, which often avoids parsing issues.
        
        Args:
            title: Song title
            artist: Artist name (optional but recommended)
            
        Returns:
            Album name string, or empty string if lookup fails
        """
        if not self.api_client:
            log_progress("❌ No API client available for album lookup")
            return ""
        
        try:
            artist_part = f" by {artist}" if artist else ""
            log_progress(f"🔍 Looking up album for '{title}'{artist_part}...")
            
            # Create a focused prompt for album identification
            prompt = f"""Identify the primary album that contains the song "{title}"{artist_part}.

Return ONLY the album name, nothing else. If the song appears on multiple albums, return the original studio album (not compilations, greatest hits, or live albums unless that's the only version).

Examples:
- "Harvest" by Neil Young → Harvest
- "Comfortably Numb" by Pink Floyd → The Wall
- "Fixing Her Hair" by Ani DiFranco → Imperfectly

Song: "{title}"{artist_part}
Album:"""
            
            # Use API client for album lookup
            response = self.api_client.client.messages.create(
                model=self.api_client.model,
                max_tokens=50,
                temperature=0.0,  # Deterministic responses
                messages=[{"role": "user", "content": prompt}]
            )
            
            result = response.content[0].text.strip()
            
            if result:
                log_progress(f"✅ Album lookup successful: '{result}'")
                return result
            else:
                log_progress("❌ Album lookup returned empty result")
                return ""
                
        except Exception as e:
            log_progress(f"❌ Album lookup failed with exception: {type(e).__name__}: {e}")
            return ""

    # ============================================================================
    # Main Workflow Method
    # ============================================================================
    
    def search_match_play(self, title: str, artist: str = None, preferences: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Process a music request with pre-parsed components.
        
        This method includes enhanced album lookup fallback when API parsing fails,
        combining the best of both the base and enhanced implementations.
        
        Args:
            title: Song title (required)
            artist: Artist name (optional)
            preferences: Playback preferences (optional)
            
        Returns:
            Dict with success status, message, and details about the track played
        """
        log_progress("search_match_play")
        try:
            preferences = preferences or {}
            
            # Step 1: Generate intelligent search queries with fallback strategies
            log_progress("Generating search queries...")
            search_queries = self.generate_search_queries(title, artist, preferences)
            
            # Step 2: Execute searches with enhanced error handling
            best_match = None
            search_results = None
            successful_query = None
            api_parsing_failed = False
            
            for query in search_queries:
                log_progress(f"Trying search: '{query}'")
                try:
                    search_result = self.execute_sonos_command(['sonos', 'searchtrack'] + query.split())
                    if search_result['success']:
                        log_progress(f"sonos searchtrack command was successful")
                    else:   
                        log_progress(f"sonos searchtrack command failed: {search_result.get('error', 'Unknown error')}")
                    
                    # Check for API parsing failure in error message (since exceptions are caught by execute_sonos_command)
                    if not search_result['success'] and search_result.get('error') and "string indices must be integers" in search_result['error']:
                        log_progress(f"🚫 API parsing failed for query '{query}': {search_result['error']}")
                        api_parsing_failed = True
                        
                        # Immediately try album lookup instead of continuing with broad searches
                        if self.api_client:
                            log_progress("🔍 API parsing failed, immediately trying LLM album lookup...")
                            album_name = self.get_album_for_song(title, artist)
                            
                            if album_name:
                                # Include artist in album search for better precision
                                if artist:
                                    album_search_query = f"{artist} {album_name}"
                                    log_progress(f"🎵 Trying artist+album search: '{album_search_query}'")
                                    album_search_result = self.execute_sonos_command(['sonos', 'searchtrack', artist, album_name])
                                else:
                                    log_progress(f"🎵 Trying album-only search: '{album_name}'")
                                    album_search_result = self.execute_sonos_command(['sonos', 'searchtrack', album_name])
                                
                                if album_search_result['success'] and album_search_result['output'].strip():
                                    results = self.parse_search_results(album_search_result['output'])
                                    
                                    if results:
                                        log_progress(f"Found {len(results)} results from album search")
                                        # For album search results, use programmatic matching for focused results
                                        match_position = self.select_best_match(
                                            results, title, artist, preferences
                                        )
                                        
                                        if match_position:
                                            log_progress(f"✅ Album-based search successful! Selected position {match_position}")
                                            best_match = match_position
                                            search_results = results
                                            # Update successful query to show it used artist+album
                                            if artist:
                                                successful_query = f"album:{artist} {album_name}"
                                            else:
                                                successful_query = f"album:{album_name}"
                                            break  # Exit the search loop - we found our match
                                        else:
                                            log_progress("No good match found in album search results")
                                    else:
                                        log_progress("Album search returned no valid results")
                                else:
                                    log_progress("Album search command failed")
                            else:
                                log_progress("❌ Could not determine album for immediate lookup")
                        
                        # Only continue with remaining queries if album lookup failed
                        continue
                    
                    if search_result['success'] and search_result['output'].strip():
                        results = self.parse_search_results(search_result['output'])
                        
                        if results:
                            log_progress(f"Found {len(results)} results")
                            # Step 3: Analyze results and find best match
                            match_position = self.select_best_match(
                                results, title, artist, preferences
                            )
                            
                            if match_position:
                                log_progress(f"Selected position {match_position}")
                                best_match = match_position
                                search_results = results
                                successful_query = query
                                break
                        else:
                            log_progress("No valid results found")
                    else:
                        log_progress("Search command failed or returned no results")
                
                except Exception as e:
                    # Log unexpected errors but continue trying
                    log_progress(f"⚠️ Unexpected error for query '{query}': {str(e)}")
                    continue
            
            if not best_match:
                return {
                    'success': False,
                    'message': f'Could not find a good match for "{title}" by {artist or "unknown artist"}. Try being more specific or using different search terms.',
                    'details': {
                        'parsed_title': title,
                        'parsed_artist': artist,
                        'queries_tried': search_queries,
                        'api_parsing_failed': api_parsing_failed
                    }
                }
            
            # Step 4: Play the selected track
            selected_track = next(
                (r for r in search_results if r['position'] == best_match), 
                None
            )
            
            log_progress(f"Playing track: {selected_track['title']} by {selected_track['artist']}")
            play_result = self.play_track_by_position(best_match)
            
            if play_result['success']:
                return {
                    'success': True,
                    'message': f'Now playing: {selected_track["title"]} by {selected_track["artist"]}',
                    'details': {
                        'track': selected_track,
                        'search_query_used': successful_query,
                        'position_played': best_match,
                        'total_results': len(search_results),
                        'used_album_lookup': 'album:' in successful_query if successful_query else False
                    }
                }
            else:
                return {
                    'success': False,
                    'message': f'Found the track but failed to play it: {play_result.get("error", "Unknown error")}',
                    'details': {
                        'found_track': selected_track,
                        'play_error': play_result.get('error')
                    }
                }
                
        except Exception as e:
            return {
                'success': False,
                'message': f'Unexpected error processing music request: {str(e)}',
                'details': {'error': str(e)}
            }
    
def get_current_track() -> str:
    """Get information about the currently playing track."""
    agent = MusicAgent()
    result = agent.get_current_track_info()
    
    if result['success']:
        return result['output']
    else:
        return f"❌ Could not get current track info: {result.get('error', 'Unknown error')}"


# Convenience functions for common operations
def pause_music() -> str:
    """Pause music playback."""
    agent = MusicAgent()
    result = agent.execute_sonos_command(['sonos', 'pause'])
    return "⏸️ Paused" if result['success'] else f"❌ Failed to pause: {result.get('error')}"


def resume_music() -> str:
    """Resume music playback."""
    agent = MusicAgent()
    result = agent.execute_sonos_command(['sonos', 'resume'])
    return "▶️ Resumed" if result['success'] else f"❌ Failed to resume: {result.get('error')}"


# Example usage demonstrations
if __name__ == "__main__":
    print("Testing Claude Code Music Interface")
    print("=" * 50)
    print("🚀 NEW LLM-POWERED APPROACH (Recommended for Claude Code):")
    print("=" * 50)
    
    # Example of the new LLM-powered approach
    # In Claude Code, you would first parse the natural language using Task subagent:
    # parsed = Task("Parse music request", prompt="...", subagent_type="general-purpose")
    # Then call: play_music_parsed(parsed['title'], parsed['artist'], parsed['preferences'])
    
    test_parsed_examples = [
        ("fixing her hair", "ani difranco", {}),
        ("harvest", "neil young", {}),
        ("harvest", "neil young", {"prefer_live": True}),
        ("harvest", "neil young", {"prefer_acoustic": True})
    ]
    
    for title, artist, prefs in test_parsed_examples:
        print(f"\n🎵 Testing parsed: title='{title}', artist='{artist}', prefs={prefs}")
        result = play_music_parsed(title, artist, prefs, verbose=True)
        print(f"Result: {result}")
    
    print("\n" + "=" * 50)
    print("📜 LEGACY APPROACH (Regex-based, less reliable):")
    print("=" * 50)
    
    # Test the legacy play_music function
    test_requests = [
        "ani difranco's fixing her hair",
        "play harvest by neil young", 
        "I want to hear a live version of harvest"
    ]
    
    for request in test_requests:
        print(f"\n🎵 Testing legacy: '{request}'")
        result = play_music(request, verbose=True)
        print(f"Result: {result}")
    
    print("\n📍 Current track:")
    print(get_current_track())
