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
        log_file = os.path.expanduser("~/.claude_music_progress.log")
        with open(log_file, "a") as f:
            f.write(log_message + "\n")
            f.flush()
    except:
        pass  # Don't fail if we can't write to file


def is_headless_mode() -> bool:
    """
    Detect if we're running in Claude Code headless mode.
    
    Improved detection logic:
    - True headless mode: claude -p (print mode) - should disable LLM calls
    - Interactive mode: normal Claude Code with subprocess - should allow LLM calls
    
    Returns True only for actual headless mode, False for interactive Claude Code.
    """
    # Check for Claude Code environment variables
    claude_entrypoint = os.getenv('CLAUDE_CODE_ENTRYPOINT')
    claudecode_var = os.getenv('CLAUDECODE')
    
    if claude_entrypoint:
        log_progress(f"🔍 Detected CLAUDE_CODE_ENTRYPOINT: {claude_entrypoint}")
        
        # TTY status (for debugging, but don't use for decision making)
        import sys
        is_tty = sys.stdin.isatty() and sys.stdout.isatty()
        log_progress(f"🔍 TTY status - stdin: {sys.stdin.isatty()}, stdout: {sys.stdout.isatty()}")
        log_progress(f"🔍 CLAUDECODE env var: {claudecode_var}")
        
        # OLD LOGIC (incorrect): 
        # if not is_tty: return True  # This was wrong!
        
        # NEW LOGIC: Only consider it headless if there are specific headless indicators
        # For now, let's be conservative and assume interactive mode unless we have
        # clear evidence of headless mode
        
        # TODO: Add more specific headless mode detection when we identify the patterns
        # For now, always assume interactive mode when we're in Claude Code
        log_progress("🔍 Claude Code detected - assuming interactive mode (LLM enabled)")
        return False
    
    return False


def should_use_llm() -> bool:
    """
    Determine if we should attempt LLM calls based on mode detection.
    
    Returns False in headless mode (where LLM calls return mocks),
    True in interactive mode (where LLM calls work properly).
    """
    headless = is_headless_mode()
    log_progress(f"🤖 LLM usage decision: headless={headless}, use_llm={not headless}")
    return not headless


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
    Enhanced MusicAgent that integrates with Claude Code's Task subagent capabilities.
    
    This subclass overrides methods to use standardized prompts instead of ad-hoc prompts,
    and integrates with Claude Code's Task tool for LLM-powered result selection.
    """
    
    def __init__(self, task_function=None):
        super().__init__()
        self.task_function = task_function
    
    def _call_selection_subagent(self, prompt: str, _retry_count=0) -> str:
        """
        Call Claude Code Task subagent for intelligent music selection.
        
        This method uses the Task function when available (provided during initialization)
        or falls back to programmatic selection.
        """
        log_progress(f"🔧 _call_selection_subagent called with task_function: {self.task_function is not None} (attempt {_retry_count + 1})")
        
        if self.task_function:
            try:
                log_progress(f"🤖 Calling Task subagent for LLM selection...")
                # Add variation to avoid Claude Code thinking this is a repeated test
                variation_suffix = ["", " (retry attempt)", " (final attempt)"][min(_retry_count, 2)]
                result = self.task_function(
                    description=f"Choose best music track for real playback (not test){variation_suffix}",
                    prompt=prompt,
                    subagent_type="general-purpose"
                )
                log_progress(f"🤖 Task subagent returned: type={type(result)}, value='{result}', length={len(str(result)) if result else 0}")
                
                # Check for mock responses and retry if detected
                if result and "mock" in str(result).lower():
                    log_progress(f"🤖 DETECTED MOCK RESPONSE in selection: '{result}' - Claude Code is using mock implementation")
                    
                    if _retry_count < 2:  # Allow up to 3 total attempts
                        log_progress(f"🔄 RETRYING LLM selection (attempt {_retry_count + 2}/3) to get real LLM response...")
                        import time
                        time.sleep(1)  # Brief pause before retry
                        return self._call_selection_subagent(prompt, _retry_count + 1)
                    else:
                        log_progress("🚫 Max retries reached for LLM selection, mock responses persist - will use programmatic fallback")
                        return ""
                
                return result if result else ""
            except Exception as e:
                log_progress(f"❌ Task subagent failed with exception: {type(e).__name__}: {e}")
                log_progress(f"❌ Task subagent traceback: {traceback.format_exc()}")
                return ""
        else:
            log_progress(f"❌ No task_function available, returning empty string")
            return ""
    
    def _llm_select_best_match(self, results, target_title: str, 
                              target_artist: str = None, preferences = None):
        """
        Use standardized prompt template for LLM-powered result selection.
        
        This overrides the base class method to use consistent prompt templates
        instead of ad-hoc prompt generation.
        """
        # Log mode for debugging purposes but always try LLM selection
        mode = "headless" if is_headless_mode() else "interactive"
        log_progress(f"🔍 Detected mode: {mode} - attempting LLM selection")
        
        try:
            from music_parsing_prompts import format_result_selection_prompt
            
            # Generate standardized prompt using template
            base_prompt = format_result_selection_prompt(
                title=target_title,
                artist=target_artist, 
                preferences=preferences or {},
                results=results
            )
            prompt = f"REAL REQUEST - NOT A TEST OR MOCK: This is an actual user request for music selection.\n\n{base_prompt}"
            
            if not prompt:
                return None
                
            # Call Task subagent for selection
            log_progress(f"Calling LLM with prompt (first 200 chars): '{prompt[:200]}...'")
            result = self._call_selection_subagent(prompt)
            log_progress(f"Raw LLM result type: {type(result)}, length: {len(str(result)) if result else 0}")
            
            # Parse result to get position number
            if result and result.strip():
                log_progress(f"LLM returned: '{result.strip()}'")
                try:
                    position_str = result.strip().split()[0]
                    log_progress(f"First word from LLM: '{position_str}'")
                    position = int(position_str)  # Get first number
                    log_progress(f"Parsed position: {position}")
                    
                    # Debug: Show available positions
                    available_positions = [r['position'] for r in results]
                    log_progress(f"Available positions: {available_positions[:10]}...")  # Show first 10
                    
                    # Validate position is in results
                    if any(r['position'] == position for r in results):
                        log_progress(f"✅ Position {position} found in results - returning success")
                        return position
                    else:
                        log_progress(f"❌ Position {position} NOT found in available positions")
                        log_progress(f"Available positions: {available_positions}")
                except (ValueError, IndexError) as e:
                    log_progress(f"❌ Failed to parse LLM position response: {e}")
                    log_progress(f"LLM response was: '{result}'")
            else:
                log_progress(f"❌ LLM returned empty result: result='{result}', stripped='{result.strip() if result else None}'")
            
        except ImportError:
            print("music_parsing_prompts not found, falling back to programmatic selection")
            return None
        except Exception as e:
            print(f"Standardized LLM selection error: {e}")
        
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
    
    def _get_album_for_song(self, title: str, artist: str = None, _retry_count=0) -> str:
        """
        Use LLM to identify the primary album that contains a specific song.
        
        This method is called when API parsing fails, allowing us to search by album
        instead of song title, which often avoids parsing issues.
        
        Args:
            title: Song title
            artist: Artist name (optional but recommended)
            _retry_count: Internal retry counter
            
        Returns:
            Album name string, or empty string if lookup fails
        """
        if not self.task_function:
            log_progress("❌ No task_function available for album lookup")
            return ""
        
        try:
            artist_part = f" by {artist}" if artist else ""
            
            # Create a focused prompt for album identification
            prompt = f"""Identify the primary album that contains the song "{title}"{artist_part}.

Return ONLY the album name, nothing else. If the song appears on multiple albums, return the original studio album (not compilations, greatest hits, or live albums unless that's the only version).

Examples:
- "Harvest" by Neil Young → Harvest
- "Comfortably Numb" by Pink Floyd → The Wall
- "Fixing Her Hair" by Ani DiFranco → Imperfectly

Song: "{title}"{artist_part}
Album:"""
            
            log_progress(f"🔍 Looking up album for '{title}'{artist_part}...")
            
            # Add variation to avoid Claude Code thinking this is a repeated test
            variation_suffix = ["", " (retry attempt)", " (final attempt)"][min(_retry_count, 2)]
            result = self.task_function(
                description=f"Find album containing song '{title}'{variation_suffix}",
                prompt=prompt,
                subagent_type="general-purpose"
            )
            
            # Check for mock responses and retry if detected
            if result and "mock" in str(result).lower():
                log_progress(f"🤖 DETECTED MOCK RESPONSE in album lookup: '{result}' - retrying...")
                
                if _retry_count < 2:  # Allow up to 3 total attempts
                    log_progress(f"🔄 RETRYING album lookup (attempt {_retry_count + 2}/3)...")
                    import time
                    time.sleep(1)  # Brief pause before retry
                    return self._get_album_for_song(title, artist, _retry_count + 1)
                else:
                    log_progress("🚫 Max retries reached for album lookup, mock responses persist")
                    return ""
            
            if result and result.strip():
                album_name = result.strip()
                log_progress(f"✅ Album lookup successful: '{album_name}'")
                return album_name
            else:
                log_progress(f"❌ Album lookup returned empty result")
                return ""
                
        except Exception as e:
            log_progress(f"❌ Album lookup failed with exception: {type(e).__name__}: {e}")
            return ""
    
    def parse_music_request(self, request: str, _retry_count=0) -> Dict[str, Any]:
        """
        Parse a natural language music request using LLM capabilities with consistent Task function access.
        
        This method is now part of the agent class to ensure consistent task_function usage.
        
        Args:
            request: Natural language music request (e.g., "play Bruce Springsteen's Thunder Road")
            _retry_count: Internal retry counter
            
        Returns:
            Dict with parsed components: {'title': str, 'artist': str|None, 'preferences': dict}
        """
        if not self.task_function:
            return {
                'error': 'Task function required - this must be called from Claude Code session',
                'original_request': request,
                'message': 'Agent must be created with task_function=Task when calling from Claude Code'
            }
        
        # Log mode for debugging purposes but always try LLM first
        mode = "headless" if is_headless_mode() else "interactive"
        log_progress(f"🔍 Detected mode: {mode} - attempting LLM parsing")
        
        try:
            from music_parsing_prompts import STANDARD_MUSIC_PARSING_PROMPT
            
            # Format the standardized prompt with the actual request
            base_prompt = STANDARD_MUSIC_PARSING_PROMPT.format(request=request)
            prompt = f"REAL REQUEST - NOT A TEST OR MOCK: This is an actual user request for music playback.\n\n{base_prompt}"
            
            # Call Claude Code's Task tool with standardized prompt
            log_progress(f"Calling LLM parsing subagent... (attempt {_retry_count + 1})")
            # Add variation to avoid Claude Code thinking this is a repeated test
            variation_suffix = ["", " (retry attempt)", " (final attempt)"][min(_retry_count, 2)]
            
            # Use self.task_function for consistency with other agent methods
            result = self.task_function(
                description=f"Extract song title and artist from: '{request[:50]}...'{variation_suffix}",
                prompt=prompt,
                subagent_type="general-purpose"
            )
            
            # Check for mock responses and retry if detected
            if result and "mock" in str(result).lower():
                log_progress(f"🤖 DETECTED MOCK RESPONSE: '{result}' - Claude Code is using mock implementation")
                
                if _retry_count < 2:  # Allow up to 3 total attempts
                    log_progress(f"🔄 RETRYING LLM parsing (attempt {_retry_count + 2}/3) to get real LLM response...")
                    import time
                    time.sleep(1)  # Brief pause before retry
                    return self.parse_music_request(request, _retry_count + 1)
                else:
                    log_progress("🚫 Max retries reached, mock responses persist - falling back to regex parsing")
            
            # Also check for clearly non-JSON responses and retry
            elif result and isinstance(result, str):
                # Quick check if this looks like a non-JSON response
                result_lower = str(result).lower().strip()
                non_json_indicators = [
                    "task completed", "i can help", "here is", "the song", 
                    "based on", "analyzing", "this appears", "i'll parse"
                ]
                
                if any(indicator in result_lower for indicator in non_json_indicators):
                    log_progress(f"🤖 DETECTED NON-JSON RESPONSE: '{result[:50]}...' - LLM returned explanatory text instead of JSON")
                    
                    if _retry_count < 2:  # Allow up to 3 total attempts
                        log_progress(f"🔄 RETRYING LLM parsing (attempt {_retry_count + 2}/3) to get proper JSON response...")
                        import time
                        time.sleep(1)  # Brief pause before retry
                        return self.parse_music_request(request, _retry_count + 1)
                    else:
                        log_progress("🚫 Max retries reached, non-JSON responses persist - falling back to regex parsing")
            
            log_progress("LLM parsing completed")
            
            # The LLM should return JSON, but handle string responses too
            if isinstance(result, str):
                import json
                try:
                    parsed_result = json.loads(result)
                    return parsed_result
                except json.JSONDecodeError as e:
                    # If not valid JSON, try to extract useful info anyway
                    log_progress(f"LLM parsing returned non-JSON: '{result}' (JSON error: {str(e)})")
                    log_progress("Falling back to simple regex parsing")
                    
                    # Try to extract basic info from the non-JSON response
                    try:
                        # Maybe the LLM returned something like "title: 'late for the sky', artist: 'jackson browne'"
                        import re
                        title_match = re.search(r"title[:\s]*['\"]([^'\"]+)['\"]", result.lower())
                        artist_match = re.search(r"artist[:\s]*['\"]([^'\"]+)['\"]", result.lower())
                        
                        if title_match:
                            return {
                                'title': title_match.group(1),
                                'artist': artist_match.group(1) if artist_match else None,
                                'preferences': {}
                            }
                    except:
                        pass
                    
                    return _fallback_simple_parse(request)
            else:
                # Result is already a dict/object
                return result
                
        except ImportError:
            return {
                'error': 'music_parsing_prompts module not found',
                'original_request': request
            }
        except Exception as e:
            return {
                'error': f'Parsing failed: {str(e)}',
                'original_request': request
            }
    
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

# one of two key functions; doesn't depend on MusicAgent
def parse_music_request_llm(request: str, task_function=None, _retry_count=0) -> Dict[str, Any]:
    """
    Parse a natural language music request using LLM capabilities with standardized prompts.
    
    This function uses standardized prompt templates to ensure consistent parsing behavior
    instead of ad-hoc prompts written during Claude Code conversations.
    
    Args:
        request: Natural language music request
        task_function: Claude Code's Task function (required for LLM parsing)
        _retry_count: Internal parameter for retry tracking
        
    Returns:
        Dict with parsed components: {'title': str, 'artist': str|None, 'preferences': dict}
        
    Example:
        # Called from Claude Code with Task function:
        parsed = parse_music_request_llm("Neil Young's Harvest", task_function=Task)
        # Returns: {'title': 'harvest', 'artist': 'neil young', 'preferences': {}}
    """
    if not task_function:
        return {
            'error': 'Task function required - this must be called from Claude Code session',
            'original_request': request,
            'message': 'Pass task_function=Task when calling from Claude Code',
            'required_signature': 'task_function(description="...", prompt="...", subagent_type="general-purpose")',
            'example': 'parse_music_request_llm("play song", task_function=Task)'
        }
    
    # Check if we should use LLM based on mode detection
    if not should_use_llm():
        log_progress("⚡ Headless mode detected - skipping LLM parsing, using regex directly")
        return _fallback_simple_parse(request)
    
    try:
        from music_parsing_prompts import STANDARD_MUSIC_PARSING_PROMPT
        
        # Format the standardized prompt with the actual request
        base_prompt = STANDARD_MUSIC_PARSING_PROMPT.format(request=request)
        prompt = f"REAL REQUEST - NOT A TEST OR MOCK: This is an actual user request for music playback.\n\n{base_prompt}"
        
        # Call Claude Code's Task tool with standardized prompt
        log_progress(f"Calling LLM parsing subagent... (attempt {_retry_count + 1})")
        # Add variation to avoid Claude Code thinking this is a repeated test
        variation_suffix = ["", " (retry attempt)", " (final attempt)"][min(_retry_count, 2)]
        result = task_function(
            description=f"Extract song title and artist from: '{request[:50]}...'{variation_suffix}",
            prompt=prompt,
            subagent_type="general-purpose"
        )
        
        # Check for mock responses and retry if detected
        if result and "mock" in str(result).lower():
            log_progress(f"🤖 DETECTED MOCK RESPONSE: '{result}' - Claude Code is using mock implementation")
            
            if _retry_count < 2:  # Allow up to 3 total attempts
                log_progress(f"🔄 RETRYING LLM parsing (attempt {_retry_count + 2}/3) to get real LLM response...")
                import time
                time.sleep(1)  # Brief pause before retry
                return parse_music_request_llm(request, task_function, _retry_count + 1)
            else:
                log_progress("🚫 Max retries reached, mock responses persist - falling back to regex parsing")
        
        # Also check for clearly non-JSON responses and retry
        elif result and isinstance(result, str):
            # Quick check if this looks like a non-JSON response
            result_lower = str(result).lower().strip()
            non_json_indicators = [
                "task completed", "i can help", "here is", "the song", 
                "based on", "analyzing", "this appears", "i'll parse"
            ]
            
            if any(indicator in result_lower for indicator in non_json_indicators):
                log_progress(f"🤖 DETECTED NON-JSON RESPONSE: '{result[:50]}...' - LLM returned explanatory text instead of JSON")
                
                if _retry_count < 2:  # Allow up to 3 total attempts
                    log_progress(f"🔄 RETRYING LLM parsing (attempt {_retry_count + 2}/3) to get proper JSON response...")
                    import time
                    time.sleep(1)  # Brief pause before retry
                    return parse_music_request_llm(request, task_function, _retry_count + 1)
                else:
                    log_progress("🚫 Max retries reached, non-JSON responses persist - falling back to regex parsing")
        
        log_progress("LLM parsing completed")
        
        # The LLM should return JSON, but handle string responses too
        if isinstance(result, str):
            import json
            try:
                parsed_result = json.loads(result)
                return parsed_result
            except json.JSONDecodeError as e:
                # If not valid JSON, try to extract useful info anyway
                log_progress(f"LLM parsing returned non-JSON: '{result[:100]}...' (JSON error: {str(e)})")
                log_progress("Falling back to simple regex parsing")
                
                # Try to extract basic info from the non-JSON response
                try:
                    # Maybe the LLM returned something like "title: 'late for the sky', artist: 'jackson browne'"
                    import re
                    title_match = re.search(r"title[:\s]*['\"]([^'\"]+)['\"]", result.lower())
                    artist_match = re.search(r"artist[:\s]*['\"]([^'\"]+)['\"]", result.lower())
                    
                    if title_match:
                        return {
                            'title': title_match.group(1),
                            'artist': artist_match.group(1) if artist_match else None,
                            'preferences': {}
                        }
                except:
                    pass
                
                # Fall back to simple parsing of the original request
                log_progress("Falling back to simple regex parsing")
                return _fallback_simple_parse(request)
        else:
            # Result is already a dict/object
            return result
            
    except ImportError:
        return {
            'error': 'music_parsing_prompts module not found',
            'original_request': request
        }
    except Exception as e:
        return {
            'error': f'Parsing failed: {str(e)}',
            'original_request': request
        }

# second main function; depends on MusicAgent
def play_music_parsed_with_llm(title: str, artist: str = None, preferences: Dict[str, Any] = None, 
                              verbose: bool = False, task_function=None) -> str:
    """
    Play music using pre-parsed components with LLM-powered result selection.
    
    This version accepts a task_function parameter that allows Claude Code to pass
    the Task function for LLM-powered result selection when needed.
    
    Args:
        title: Song title (required)
        artist: Artist name (optional)
        preferences: Dict with preference keys (optional)
        verbose: Whether to return detailed information
        task_function: Function to call Task subagent (provided by Claude Code)
        
    Returns:
        Human-readable message about the result
    """
    # Use Claude Code-enhanced agent with LLM selection capability
    log_progress("Starting music search and playback...")
    agent = ClaudeCodeMusicAgent(task_function=task_function)
    result = agent.handle_parsed_music_request(title, artist, preferences or {})
    
    if result['success']:
        log_progress("Music playback initiated")
        if verbose:
            details = result.get('details', {})
            message = result['message']
            if 'search_query_used' in details:
                message += f"\n(Used search query: '{details['search_query_used']}')"
            if 'total_results' in details:
                message += f"\n(Found {details['total_results']} total results)"
            if preferences:
                prefs_str = ", ".join(f"{k.replace('prefer_', '')}" for k, v in preferences.items() if v)
                if prefs_str:
                    message += f"\n(Applied preferences: {prefs_str})"
            return message
        else:
            return result['message']
    else:
        log_progress(f"Music playback failed: {result['message']}")
        if verbose:
            error_details = result.get('details', {})
            message = result['message']
            if 'queries_tried' in error_details:
                message += f"\n(Tried {len(error_details['queries_tried'])} different search queries)"
            return message
        else:
            return f"❌ {result['message']}"


def handle_music_request(user_request: str, task_function=None, verbose: bool = False) -> str:
    """
    Complete end-to-end music request handler for Claude Code.
    
    This is the main entry point that matches the workflow described in CLAUDE.md.
    Combines LLM parsing with intelligent music selection for optimal results.
    
    Args:
        user_request: Natural language music request (e.g., "play Bruce Springsteen's Thunder Road")
        task_function: Claude Code's Task function (required for LLM features)
        verbose: Whether to return detailed information about the process
        
    Returns:
        Human-readable message about the result
        
    Example:
        result = handle_music_request("play Bruce Springsteen's Thunder Road", task_function=Task)
    """
    # Early exception catching to identify early failures
    try:
        start_time = datetime.now()
        
        # Debug: Track call stack to detect loops
        import os
        call_stack = traceback.extract_stack()
        handle_music_request_calls = [frame for frame in call_stack if 'handle_music_request' in frame.name]
        
        # Show process info to understand multiple calls
        pid = os.getpid()
        log_progress(f"🎯 [ENTRY] Processing music request: '{user_request}' (PID: {pid})")
    except Exception as e:
        # If we can't even get to basic logging, catch and report it
        try:
            log_progress(f"💥 CRITICAL: Early failure in handle_music_request: {type(e).__name__}: {e}")
            log_progress(f"💥 CRITICAL: Traceback: {traceback.format_exc()}")
        except:
            # Last resort - print to stderr if even logging fails
            import sys
            print(f"FATAL: Complete failure in handle_music_request: {e}", file=sys.stderr)
        return f"❌ Critical error: {e}"
    
    if len(handle_music_request_calls) > 1:
        log_progress(f"🔄 WARNING: handle_music_request called recursively! Call depth: {len(handle_music_request_calls)}")
        for i, frame in enumerate(handle_music_request_calls):
            log_progress(f"  {i+1}. {frame.filename}:{frame.lineno} in {frame.name}")
    
    # Show relevant stack frames to understand the calling context
    relevant_frames = [frame for frame in call_stack[-10:] if not frame.filename.endswith('traceback.py')]
    log_progress(f"📍 Call stack (last 5 frames):")
    for i, frame in enumerate(relevant_frames[-5:]):
        filename = os.path.basename(frame.filename)
        log_progress(f"  {i+1}. {filename}:{frame.lineno} in {frame.name}")
    
    if not task_function:
        log_progress("❌ No task_function provided - this is the failure point!")
        return "❌ Task function required. Must call: handle_music_request(request, task_function=Task) where Task supports task_function(description='...', prompt='...', subagent_type='general-purpose')"
    
    log_progress(f"✅ Task function available: {type(task_function)}")
    
    try:
        # Step 1: Create agent first for consistent Task function access
        log_progress("Creating music agent with Task function...")
        agent = ClaudeCodeMusicAgent(task_function=task_function)
        
        # Step 2: Parse the natural language request using agent's LLM method
        log_progress("Parsing request with LLM...")
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
            return result['message']
        else:
            return f"❌ {result['message']}"
        
    except Exception as e:
        elapsed = (datetime.now() - start_time).total_seconds()
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
