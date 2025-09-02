"""
Simple interface for Claude Code to handle music requests using the intelligent agent.

This module provides a clean, easy-to-use interface that Claude Code can invoke
to handle natural language music requests without needing to understand the
internal workings of the agent.
"""

from music_agent import MusicAgent
from typing import Optional, Dict, Any
import json
import sys
import os
import re
import traceback
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


class ClaudeCodeMusicAgent(MusicAgent):
    """
    Enhanced MusicAgent that integrates with Claude API for reliable LLM capabilities.
    
    This subclass overrides methods to use direct Claude API calls instead of
    the unreliable Task function, eliminating mock response issues.
    """
    
    def __init__(self, api_client=None):
        super().__init__()
        # Import here to avoid circular imports
        if api_client is None:
            try:
                from claude_api_client import get_api_client
                api_client = get_api_client()
            except Exception as e:
                log_progress(f"❌ Could not initialize API client: {e}")
                api_client = None
        self.api_client = api_client
    
    
    def _llm_select_best_match(self, results, target_title: str, 
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
    
    def _intelligent_match_selection(self, results, target_title: str, target_artist: str = None, preferences = None):
        """
        Override to add LLM-powered intelligent selection on top of base programmatic selection.
        
        This method brings back the hybrid intelligence that was removed from the base class.
        Uses LLM selection when complexity indicators suggest it would be beneficial.
        """
        if not results:
            return None
            
        preferences = preferences or {}
        
        # First, get programmatic scores for all results (from base class)
        programmatic_matches = self._get_programmatic_scores(results, target_title, target_artist, preferences)
        
        if not programmatic_matches:
            return None
        
        # Determine if we should use LLM selection
        if self._should_use_llm_selection(programmatic_matches, preferences):
            try:
                log_progress("Using LLM to select best match...")
                llm_selection = self._llm_select_best_match(results, target_title, target_artist, preferences)
                if llm_selection:
                    log_progress("LLM selection completed")
                    return llm_selection
                else:
                    log_progress("LLM selection returned no result, using programmatic fallback")
            except Exception as e:
                # Fallback to programmatic if LLM fails
                log_progress(f"LLM selection failed ({e}), falling back to programmatic selection")
        
        # Use programmatic selection (fallback to base class implementation)
        return super()._intelligent_match_selection(results, target_title, target_artist, preferences)
    
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
    
    def _get_album_for_song(self, title: str, artist: str = None) -> str:
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
    
    def parse_music_request(self, request: str) -> Dict[str, Any]:
        """
        Parse a natural language music request using Claude API.
        
        This method now uses direct API calls for reliable, consistent parsing
        without the mock response issues of the Task function approach.
        
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
    
    def handle_parsed_music_request(self, title: str, artist: str = None, preferences: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Enhanced version that uses LLM album lookup when API parsing fails.
        
        This overrides the base class method to add intelligent album-based fallback
        when the standard search queries cause API parsing exceptions.
        """
        try:
            preferences = preferences or {}
            
            # Step 1: Generate intelligent search queries with fallback strategies
            log_progress("Generating search queries...")
            search_queries = self._generate_smart_search_queries(title, artist, preferences)
            
            # Step 2: Execute searches with enhanced error handling
            best_match = None
            search_results = None
            successful_query = None
            api_parsing_failed = False
            
            for query in search_queries:
                log_progress(f"Trying search: '{query}'")
                try:
                    search_result = self.execute_sonos_command(['sonos', 'searchtrack'] + query.split())
                    
                    # Check for API parsing failure in error message (since exceptions are caught by execute_sonos_command)
                    if not search_result['success'] and search_result.get('error') and "string indices must be integers" in search_result['error']:
                        log_progress(f"🚫 API parsing failed for query '{query}': {search_result['error']}")
                        api_parsing_failed = True
                        
                        # Immediately try album lookup instead of continuing with broad searches
                        if self.task_function:
                            log_progress("🔍 API parsing failed, immediately trying LLM album lookup...")
                            album_name = self._get_album_for_song(title, artist)
                            
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
                                        # For album search results, use simple programmatic matching (no LLM needed)
                                        # since we have a focused set of tracks from the specific album
                                        match_position = super()._intelligent_match_selection(
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
            
            # Step 3: Play the selected track
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
        log_progress("Creating music agent with API client...")
        agent = ClaudeCodeMusicAgent(api_client=api_client)
        
        # Step 2: Parse the natural language request using API
        log_progress("Parsing request with API...")
        parsed = agent.parse_music_request(user_request)
        
        # Handle parsing errors
        if 'error' in parsed:
            log_progress(f"Parsing failed: {parsed['error']}")
            return f"❌ Could not understand request: {parsed['error']}"
        
        log_progress(f"Parsed: title='{parsed['title']}', artist='{parsed.get('artist', 'none')}'")
        
        # Step 3: Play music with parsed components using the same agent instance
        log_progress("Searching and playing...")
        result = agent.handle_parsed_music_request(
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

def get_current_track() -> str:
    """Get information about the currently playing track."""
    agent = ClaudeCodeMusicAgent()
    result = agent.get_current_track_info()
    
    if result['success']:
        return result['output']
    else:
        return f"❌ Could not get current track info: {result.get('error', 'Unknown error')}"


# Convenience functions for common operations
def pause_music() -> str:
    """Pause music playback."""
    agent = ClaudeCodeMusicAgent()
    result = agent.execute_sonos_command(['sonos', 'pause'])
    return "⏸️ Paused" if result['success'] else f"❌ Failed to pause: {result.get('error')}"


def resume_music() -> str:
    """Resume music playback."""
    agent = ClaudeCodeMusicAgent()
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
