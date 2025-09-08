"""
Standardized prompt templates for music request parsing using LLM capabilities.

This module centralizes all the parsing instructions that were previously written
ad-hoc during Claude Code conversations, making the behavior consistent and maintainable.
"""

STANDARD_MUSIC_PARSING_PROMPT = """
Parse the following natural language music request into structured components:

"{request}"

Extract these components:
1. title: The song title (clean, lowercase, no annotations like "remaster" or "live")
2. artist: The artist name (clean, no possessives or "by" constructions)
3. preferences: Dictionary with boolean flags for user preferences

Handle these common patterns:
- **Play request indicators**: "I'd like to hear", "play", "put on", "I want to hear", "can you play"
- **Possessive forms**: "[Artist]'s [Song]" → artist="[Artist]", title="[Song]"
- **By constructions**: "[Song] by [Artist]" → title="[Song]", artist="[Artist]"
- **Live preferences**: "live version of", "concert version", "live recording" → prefer_live: true
- **Acoustic preferences**: "acoustic version", "unplugged version", "acoustic" → prefer_acoustic: true
- **Studio preferences**: "studio version", "original version", "studio recording" → prefer_studio: true

Special handling:
- Remove possessive "'s" from artist names
- Convert titles to lowercase for consistency
- Don't include version type indicators in the title (e.g., "live", "acoustic") 
- Set preference flags based on explicit version requests

Examples:
- "Neil Young's Harvest" → {{"title": "harvest", "artist": "neil young", "preferences": {{}}}}
- "play a live version of harvest by neil young" → {{"title": "harvest", "artist": "neil young", "preferences": {{"prefer_live": true}}}}
- "I'd like to hear some acoustic Beatles" → {{"title": "some acoustic beatles", "artist": null, "preferences": {{"prefer_acoustic": true}}}}

IMPORTANT: You MUST return ONLY a valid JSON object with exactly these keys: title, artist, preferences
- Do not include any explanatory text before or after the JSON
- Do not wrap the JSON in code blocks or markdown
- The artist can be null if not clearly specified
- Return only the raw JSON, nothing else

Required JSON format:
{{
  "title": "song title here",
  "artist": "artist name here or null", 
  "preferences": {{}}
}}
"""

ENHANCED_MUSIC_PARSING_PROMPT = """
Parse the following natural language music request into structured components:

"{request}"

Extract these components:
1. title: The song title (clean, lowercase, no annotations)
2. artist: The artist name (clean, no possessives)
3. album: The album name if mentioned (clean, no possessives, or null if not specified)
4. preferences: Dictionary with boolean flags for user preferences

Handle these common patterns:
- **Play request indicators**: "I'd like to hear", "play", "put on", "I want to hear", "can you play"
- **Possessive forms**: "[Artist]'s [Song]" → artist="[Artist]", title="[Song]"
- **By constructions**: "[Song] by [Artist]" → title="[Song]", artist="[Artist]"
- **Album indicators**: "from [Album]", "[Album] album", "off [Album]" → album="[Album]"
- **Live preferences**: "live version of", "concert version", "live recording" → prefer_live: true
- **Acoustic preferences**: "acoustic version", "unplugged version", "acoustic" → prefer_acoustic: true
- **Studio preferences**: "studio version", "original version", "studio recording" → prefer_studio: true

Special handling:
- Remove possessive "'s" from artist and album names
- Convert titles and albums to lowercase for consistency
- Don't include version type indicators in the title
- Set preference flags based on explicit version requests

Examples:
- "Neil Young's Harvest from the Harvest album" → {{"title": "harvest", "artist": "neil young", "album": "harvest", "preferences": {{}}}}
- "play a live version of harvest" → {{"title": "harvest", "artist": null, "album": null, "preferences": {{"prefer_live": true}}}}
- "play album dark side of the moon" by pink floyd → {{"title": null, "artist": "pink floyd", "album": "the dark side of the moon", "preferences": {{}}}}

IMPORTANT: You MUST return ONLY a valid JSON object with exactly these keys: title, artist, album, preferences
- Do not include any explanatory text before or after the JSON
- Do not wrap the JSON in code blocks or markdown
- Return only the raw JSON, nothing else

Return the result as a valid JSON object with exactly these keys: title, artist, album, preferences
Any one of title, artist, or album can be null if not clearly specified but at least one must be non-null.

Required JSON format:
{{
  "title": "song title herei or null",
  "artist": "artist name here or null", 
  "album": "album name here or null",
  "preferences": {{}}
}}
"""

ENHANCED_MUSIC_PARSING_PROMPT_ORIG = """
Parse the following natural language music request into structured components:

"{request}"

Extract these components:
1. title: The song title (clean, lowercase, no annotations)
2. artist: The artist name (clean, no possessives)
3. album: The album name if mentioned (clean, no possessives, or null if not specified)
4. preferences: Dictionary with boolean flags for user preferences

Handle these common patterns:
- **Play request indicators**: "I'd like to hear", "play", "put on", "I want to hear", "can you play"
- **Possessive forms**: "[Artist]'s [Song]" → artist="[Artist]", title="[Song]"
- **By constructions**: "[Song] by [Artist]" → title="[Song]", artist="[Artist]"
- **Album indicators**: "from [Album]", "[Album] album", "off [Album]" → album="[Album]"
- **Live preferences**: "live version of", "concert version", "live recording" → prefer_live: true
- **Acoustic preferences**: "acoustic version", "unplugged version", "acoustic" → prefer_acoustic: true
- **Studio preferences**: "studio version", "original version", "studio recording" → prefer_studio: true

Special handling:
- Remove possessive "'s" from artist and album names
- Convert titles and albums to lowercase for consistency
- Don't include version type indicators in the title
- Set preference flags based on explicit version requests

Examples:
- "Neil Young's Harvest from the Harvest album" → {{"title": "harvest", "artist": "neil young", "album": "harvest", "preferences": {{}}}}
- "play a live version of harvest" → {{"title": "harvest", "artist": null, "album": null, "preferences": {{"prefer_live": true}}}}

Return the result as a valid JSON object with exactly these keys: title, artist, album, preferences
The artist and album can be null if not clearly specified.
"""

# Template for result selection (used in complex cases with multiple search results)
TITLE_RESULT_SELECTION_PROMPT_TEMPLATE = """
You are a music expert helping select the best track from search results.

TARGET SONG: "{title}" by {artist_text}
PREFERENCES: {preferences_text}

SEARCH RESULTS:
{results_list}

ANALYSIS INSTRUCTIONS:
- THE MOST IMPORTANT CRITERION IS TO MATCH THE TITLE AS EXACTLY AS POSSIBLE
- Prefer the artist as exectly as possible (not covers or tributes by other artists)
- Apply user preferences for version type (live, acoustic, studio)
- For live preferences: look for "(Live)" in title or live venue/album names
- For acoustic preferences: look for "Acoustic", "Unplugged", or similar
- Prefer original albums over compilation albums when no preference specified
- Avoid covers, tributes, or instrumental versions unless specifically requested

Which position number (1-{max_position}) best matches the request?

Return ONLY the position number, no explanation.
"""

ALBUM_RESULT_SELECTION_PROMPT_TEMPLATE = """
You are a music expert helping select the best track from search results.

TARGET ALBUM: "{album}" by {artist_text}
PREFERENCES: {preferences_text}

SEARCH RESULTS:
{results_list}

ANALYSIS INSTRUCTIONS:
- THE MOST IMPORT CRITERION IS TO MATCH THE ALBUM AS EXACTLY AS POSSIBLE
- Match the the artist as exactly as possible (not covers or tributes by other artists)
- Apply user preferences for version type (live, acoustic, studio)
- For live preferences: look for "(Live)" in album or live venue/album names
- For acoustic preferences: look for "Acoustic", "Unplugged", or similar
- Prefer original albums over compilation albums when no preference specified
- Avoid covers, tributes, or instrumental versions unless specifically requested

Which position number (1-{max_position}) best matches the request?

Return ONLY the position number, no explanation.
"""

def format_result_selection_title_prompt(title: str, artist: str = None, preferences: dict = None, results: list = None) -> str:
    """
    Format the result selection prompt with actual search data.
    
    Args:
        title: Target track title
        artist: Target artist name (can be None)
        preferences: User preferences dict
        results: List of search results with position, title, artist, album
        
    Returns:
        Formatted prompt string ready for LLM
    """
    if not results:
        return ""
    
    # Format artist text
    artist_text = artist if artist else "unknown artist"
    
    # Format preferences text
    if preferences:
        prefs = []
        if preferences.get('prefer_live'):
            prefs.append('live version')
        if preferences.get('prefer_acoustic'):
            prefs.append('acoustic version')  
        if preferences.get('prefer_studio'):
            prefs.append('studio version')
        preferences_text = ", ".join(prefs) if prefs else "no specific version preference"
    else:
        preferences_text = "no specific version preference"
    
    # Format results list
    results_lines = []
    for result in results:
        if isinstance(result, dict):
            pos = result.get('position', '?')
            title_text = result.get('title', 'Unknown')
            artist_text_result = result.get('artist', 'Unknown')
            album = result.get('album', 'Unknown')
            results_lines.append(f"{pos}. {title_text}-{artist_text_result}-{album}")
        else:
            # Handle tuple format (position, title, artist, album)
            pos, title_text, artist_text_result, album = result[:4]
            results_lines.append(f"{pos}. {title_text}-{artist_text_result}-{album}")
    
    results_list = "\n".join(results_lines)
    max_position = len(results)
    
    return TITLE_RESULT_SELECTION_PROMPT_TEMPLATE.format(
        title=title,
        artist_text=artist_text,
        preferences_text=preferences_text,
        results_list=results_list,
        max_position=max_position
    )

def format_result_selection_album_prompt(album: str, artist: str = None, preferences: dict = None, results: list = None) -> str:
    """
    Format the result selection prompt with actual search data.
    
    Args:
        album: Target album 
        artist: Target artist name (can be None)
        preferences: User preferences dict
        results: List of search results with position, title, artist, album
        
    Returns:
        Formatted prompt string ready for LLM
    """
    if not results:
        return ""
    
    # Format artist text
    artist_text = artist if artist else "unknown artist"
    
    # Format preferences text
    if preferences:
        prefs = []
        if preferences.get('prefer_live'):
            prefs.append('live version')
        if preferences.get('prefer_acoustic'):
            prefs.append('acoustic version')  
        if preferences.get('prefer_studio'):
            prefs.append('studio version')
        preferences_text = ", ".join(prefs) if prefs else "no specific version preference"
    else:
        preferences_text = "no specific version preference"
    
    # Format results list
    results_lines = []
    for result in results:
        if isinstance(result, dict):
            pos = result.get('position', '?')
            album_text = result.get('album', 'Unknown')
            artist_text_result = result.get('artist', 'Unknown')
            #album = result.get('album', 'Unknown')
            results_lines.append(f"{pos}. {album_text}-{artist_text_result}")
        else:
            # Handle tuple format (position, title, artist, album)
            pos, album_text, artist_text_result = result[:3]
            results_lines.append(f"{pos}. {title_text}-{artist_text_result}")
    
    results_list = "\n".join(results_lines)
    max_position = len(results)
    
    return ALBUM_RESULT_SELECTION_PROMPT_TEMPLATE.format(
        album=album,
        artist_text=artist_text,
        preferences_text=preferences_text,
        results_list=results_list,
        max_position=max_position
    )
