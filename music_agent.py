"""
Music Request Agent for Sonos CLI

This agent uses LLM capabilities to intelligently interpret natural language 
music requests and execute them using the sonos CLI, replacing the rigid 
pattern-matching approach in sonos_helpers.py.
"""

import subprocess
import json
import re
import sys
import os
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple


def log_progress(message: str):
    """Log progress to file for headless mode monitoring."""
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]  # HH:MM:S.mmm format
    log_message = f"[{timestamp}] 🎵 {message}"
    
    # Write to log file for headless mode monitoring
    try:
        log_file = os.path.expanduser("~/.claude_music_progress.log")
        with open(log_file, "a") as f:
            f.write(log_message + "\n")
            f.flush()
    except:
        pass  # Don't fail if we can't write to file


class MusicAgent:
    """
    An intelligent agent that can understand natural language music requests
    and execute them using the sonos CLI tools.
    """
    
    def __init__(self):
        self.last_search_results = []
        
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
        results = []
        lines = search_output.strip().split('\n')
        
        for line in lines:
            # Match pattern: "number. Title-Artist-Album"
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
    
    def handle_parsed_music_request(self, title: str, artist: str = None, preferences: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Process a music request with pre-parsed components.
        
        This method bypasses the parsing step and directly works with structured data.
        It's designed to be used when parsing is done externally by LLM capabilities.
        
        Args:
            title: Song title (required)
            artist: Artist name (optional)
            preferences: Playback preferences (optional)
            
        Returns:
            Dict with success status, message, and details about the track played
        """
        try:
            preferences = preferences or {}
            
            # Step 1: Generate intelligent search queries with fallback strategies
            log_progress("Generating search queries...")
            search_queries = self._generate_smart_search_queries(title, artist, preferences)
            
            # Step 2: Execute searches with error handling
            best_match = None
            search_results = None
            successful_query = None
            
            for query in search_queries:
                log_progress(f"Trying search: '{query}'")
                try:
                    search_result = self.execute_sonos_command(['sonos', 'searchtrack'] + query.split())
                    
                    if search_result['success'] and search_result['output'].strip():
                        results = self.parse_search_results(search_result['output'])
                        
                        if results:
                            log_progress(f"Found {len(results)} results")
                            # Step 3: Analyze results and find best match
                            match_position = self._intelligent_match_selection(
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
                    # Handle known API parsing issues and continue with next query
                    if "string indices must be integers" in str(e):
                        continue
                    else:
                        # Log unexpected errors but continue trying
                        pass
            
            if not best_match:
                return {
                    'success': False,
                    'message': f'Could not find a good match for "{title}" by {artist or "unknown artist"}. Try being more specific or using different search terms.',
                    'details': {
                        'parsed_title': title,
                        'parsed_artist': artist,
                        'queries_tried': search_queries
                    }
                }
            
            # Step 4: Play the selected track
            # Find the track details for confirmation before attempting to play
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
                        'total_results': len(search_results)
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

    
    def generate_search_queries(self, title: str, artist: str = None, preferences: Dict[str, Any] = None) -> List[str]:
        """
        Generate intelligent search queries for the sonos API.
        
        Args:
            title: Song title
            artist: Artist name (optional)
            preferences: Search preferences (e.g., prefer_live)
            
        Returns:
            List of search query strings ordered by likelihood of success
        """
        preferences = preferences or {}
        queries = []
        
        # Base query
        if artist:
            base_query = f"{title} by {artist}"
            queries.append(base_query)
            
            # Additional variations
            queries.append(f"{title} {artist}")
            queries.append(f"{artist} {title}")
            
            # Handle live preferences
            if preferences.get('prefer_live'):
                queries.insert(0, f"live {title} {artist}")
                queries.insert(1, f"{title} live {artist}")
                queries.insert(2, f"{artist} {title} live")
        else:
            queries.append(title)
            if preferences.get('prefer_live'):
                queries.insert(0, f"live {title}")
                queries.insert(1, f"{title} live")
        
        return queries
    
    def analyze_and_select_track(self, results: List[Dict[str, Any]], 
                                target_title: str, target_artist: str = None,
                                preferences: Dict[str, Any] = None) -> Optional[int]:
        """
        Analyze search results and intelligently select the best match.
        
        Args:
            results: Parsed search results
            target_title: Target song title
            target_artist: Target artist name
            preferences: Search preferences
            
        Returns:
            Position number of best match, or None if no good match
        """
        if not results:
            return None
            
        preferences = preferences or {}
        
        # This will use LLM reasoning to analyze results and make the best choice
        # For now, implement basic similarity matching as fallback
        best_match = None
        best_score = 0
        
        for result in results:
            score = 0
            
            # Title similarity
            title_similarity = self._calculate_similarity(
                result['title'].lower(), 
                target_title.lower()
            )
            score += title_similarity * 0.7
            
            # Artist similarity (if provided)
            if target_artist:
                artist_similarity = self._calculate_similarity(
                    result['artist'].lower(),
                    target_artist.lower()
                )
                score += artist_similarity * 0.3
            
            # Preferences handling
            if preferences.get('prefer_live'):
                is_live = ('live' in result['title'].lower() or 
                          'live' in result['album'].lower())
                if is_live:
                    score += 0.2
            
            if score > best_score and score > 0.6:
                best_score = score
                best_match = result['position']
        
        return best_match
    
    def _calculate_similarity(self, str1: str, str2: str) -> float:
        """Calculate simple similarity between two strings."""
        from difflib import SequenceMatcher
        return SequenceMatcher(None, str1, str2).ratio()
    
    def _generate_smart_search_queries(self, title: str, artist: str = None, preferences: Dict[str, Any] = None) -> List[str]:
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
    
    def _intelligent_match_selection(self, results: List[Dict[str, Any]], 
                                   target_title: str, target_artist: str = None,
                                   preferences: Dict[str, Any] = None) -> Optional[int]:
        """
        Use programmatic scoring to select the best track match from search results.
        
        This base implementation uses algorithmic scoring only. Subclasses can override
        to add LLM intelligence when available.
        
        Args:
            results: Parsed search results  
            target_title: Target song title
            target_artist: Target artist name
            preferences: Search preferences
            
        Returns:
            Position of best match or None
        """
        if not results:
            return None
            
        preferences = preferences or {}
        
        # Get programmatic scores for all results
        programmatic_matches = self._get_programmatic_scores(results, target_title, target_artist, preferences)
        
        if not programmatic_matches:
            return None
        
        # Use programmatic selection (base implementation)
        best_match = max(programmatic_matches, key=lambda x: x[1])
        return best_match[0]  # Return position
    
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
        
    def _normalize_for_exact_match(self, text: str) -> str:
        """Normalize text for exact matching by removing all punctuation and extra spaces."""
        if not text:
            return ""
        
        # Remove all punctuation and normalize spacing
        normalized = re.sub(r'[^\w\s]', '', text.lower())
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        return normalized

    def get_current_track_info(self) -> Dict[str, Any]:
        """Get information about currently playing track."""
        result = self.execute_sonos_command(['sonos', 'what'])
        return result
    
    def play_track_by_position(self, position: int) -> Dict[str, Any]:
        """Play a track by its position from the last search results."""
        result = self.execute_sonos_command(['sonos', 'playtrackfromlist', str(position)])
        return result




if __name__ == "__main__":
    # Test the agent with the primary example: "ani difranco's fixing her hair"
    agent = MusicAgent()
    
    test_requests = [
        "ani difranco's fixing her hair",
        "play harvest by neil young", 
        "I want to hear a live version of comfortably numb",
        "the beatles here comes the sun"
    ]
    
    for request in test_requests:
        print(f"\n{'='*60}")
        print(f"Testing: '{request}'")
        print('='*60)
        
        result = agent.handle_music_request(request)
        
        print(f"Success: {result['success']}")
        print(f"Message: {result['message']}")
        
        if result.get('details'):
            details = result['details']
            if 'parsed_title' in details:
                print(f"Parsed title: {details['parsed_title']}")
                print(f"Parsed artist: {details['parsed_artist']}")
            if 'search_query_used' in details:
                print(f"Successful query: {details['search_query_used']}")
            if 'track' in details:
                track = details['track']
                print(f"Selected track: {track['title']} - {track['artist']} - {track['album']}")
                print(f"Position: {details['position_played']}/{details['total_results']}")
        
        if not result['success'] and 'queries_tried' in result.get('details', {}):
            print(f"Queries attempted: {result['details']['queries_tried']}")
    
    print(f"\n{'='*60}")
    print("Testing complete!")
