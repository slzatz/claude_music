# Claude Music Interface

A Sonos track or album request system that uses Claude API to handle specific natural language tasks that arise out of interactions with a separate Sonos CLI application that can perform a variety of Sonos commands. The main uses of an LLM in this context is to 1) understand the user's natural language request to play a certain music track or album and 2) to analyze the results of searching for that track/album to determine the one that most closely matches the user's request.

## Overview

This project provides an API-based interface for understanding the user's natural languame request and identifying the Sonos accessible track that best matches that request. It uses an LLM (Claude) to interpret the various requests that a user can make:
- "play fixing her hair by ani difranco"
- "play neil young's like a hurricane"
- "play bruce springsteen's album born to run"
- "play a live version of patty griffin's burgundy shoes"
....

**Note**: you could write regexes to handle these cases and, in fact, there is fall-back code for when the api is unavailable but it is easier and more convenient and reliable to use an LLM to handle the wide variety of natural language requests that users can make. One simple example:  How would you correctly parse:  "play arbour zena by keith jarrett."  Claude has in its training set that Keith Jarrett has an album called "Arbour Zena" and so it correctly interprets this as a request to play the album "Arbour Zena" by Keith Jarrett.  On the other hand:  "play harvest by neil young" provides no clues to anyone as to whether you are asking for the album or the track so the LLM will select the track and you'll have to explicitly add the work album if that's what you want. Although if you some reason you like typing a few extra characters, you can say "play the record harvest by neil young" and the LLM will correctly interpret that as a request for the album again without any regex coding. If you look at the prompts, they are pretty simple although they can always be improved if you get results that are not what you wanted.

**Note**: This Claude API integration replaces a previous approach that attempted to use built-in Claude Code Task function behavior that turned out to frequently employ mock functions instead of the intended general-purpose agent behavior. Whether Claude would use mock functions or not was unpredictable although toward the end of August 2025, this happened more frequently.  Perhaps the issues that Anthropic has acknowledged were contributing to the problems but in the end it is cleaner to use Claude API calls and cost seems to be on the order of $.005 per "music" request, which includes both parsing the user's input, which determines the search string, and then selecting the best match from the search results that come back.

## Key Features

### Natural Language Understanding
- **Possessive parsing**: "Ani DiFranco's fixing her hair"
- **Version preferences**: "live version of Comfortably Numb" 
- **Casual requests**: "some Beatles", "play Harvest by Neil Young"
- **Complex grammar**: Handles articles, pronouns, and natural speech patterns

### Analyzing Search Results
- **Selecting best match**: Considers track title, artist, expressed preferences (i.e., live, acoustic)
- **Context-aware**: Prefers originals over compilations, studio over live (unless specified)
- **Fuzzy matching**: Should handle typos, incomplete information and still find best match

### Intelligent Error Recovery
- **Smart fallback**: Multiple search strategies with automatic progression
- **No hard-coding**: Scalable solution that works for any song, not just special cases

### Reliable AI Integration
- **Direct Claude API**: Consistent, reliable LLM parsing and selection
- **No Mock Responses**: Eliminates "Task completed..." failures completely
- **Graceful Fallbacks**: Automatic regex parsing when API temporarily unavailable

## Architecture

### Core Components

```
claude_api_client.py         # Claude API client (ClaudeAPIClient class) with LLM parsing and selection methods
claude_music_interface.py    # Main interface including the MusicAgent class, which is derived from the MusicAgent class
music_parsing_prompts.py     # Standardized prompts for consistent behavior
```

### Key Classes

- **`ClaudeAPIClient`**: Direct API client for parsing and track selection
- **`ClaudeCodeMusicAgent`**: Derived from MusicAgent class and connected to ClaudeAPIClient
- **Main function**: `handle_music_request(request)` - simplified, reliable entry point

**Note**: The `ClaudeCodeMusicAgent` class name is a holdover from the previous approach that used Claude Code Task functions. It should be renamed to something like `ClaudeMusicAgent` to avoid confusion.  Also, the `claude_music_interface.py` file name is also a holdover from the previous approach and should be renamed to something like `music_interface.py`. And lastly, not sure if the separate base class of MusicAgent and the derived class of ClaudeCodeMusicAgent is necessary since there is no intention of having other types of agents.  This could be simplified by merging the two classes into one class.

## Installation

### Prerequisites
- Python 3.8+ 
- Sonos CLI installed and configured
- Anthropic API key

### Setup Instructions

1. **Clone and navigate to directory**
   ```bash
   cd /path/to/claude_music
   ```

2. **Set up virtual environment**
   ```bash
   # Create virtual environment
   python -m venv .venv
   # Or use uv (recommended)
   uv venv .venv
   
   # Activate environment
   source .venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   # Using pip
   pip install anthropic python-dotenv
   
   # Or using uv (faster)
   uv pip install anthropic python-dotenv
   ```

4. **Configure API key**
   ```bash
   # Method A: Environment variable
   export ANTHROPIC_API_KEY=your_api_key_here
   
   # Method B: .env file (recommended)
   echo "ANTHROPIC_API_KEY=your_api_key_here" > .env
   ```

5. **Test installation**
   ```bash
   python -c "from claude_music_interface import handle_music_request; print('✅ Setup successful')"
   ```

## Quick Start

### Basic Usage

```python
from claude_music_interface import handle_music_request

# Simple, reliable API-based processing
result = handle_music_request("play Neil Young's Harvest")
print(result)  # "Now playing: Harvest by Neil Young"

# Complex requests handled automatically
result = handle_music_request("I'd like to hear a live version of Comfortably Numb")
print(result)  # "Now playing: Comfortably Numb (Live) by Pink Floyd"
```

### Command Line Testing

```bash
# Quick test
source .venv/bin/activate
python -c "from claude_music_interface import handle_music_request; print(handle_music_request('ani difranco\\'s fixing her hair'))"

# Expected: "Now playing: Fixing Her Hair by Ani DiFranco"
```

## How It Works

### 1. Request Processing Flow

```
User Request → Claude API → Search Generation → Result Selection → Playback
     ↓            ↓              ↓                ↓                ↓
"play fixing  → {title: "fixing → ["fixing her    → Position 3    → Sonos play
 her hair by     her hair",       hair by ani        (best match)
 ani difranco"   artist: "ani     difranco", ...]      
                 difranco"}                            
```

### 2. API-Based Error Recovery

When Sonos API parsing fails (e.g., "string indices must be integers"):

```
API Failure → Claude Album Lookup → Album Search → Normal Selection → Success
     ↓              ↓                  ↓              ↓               ↓
"TypeError:    → Claude API:         → "ani difranco → Position 3     → "Fixing Her
 string         "What album           Imperfectly"    (from 13        Hair" plays
 indices..."    contains fixing       (13 tracks)     tracks)         correctly
                her hair?" →                          
                "Imperfectly"                          
```

### 3. Search Strategy Hierarchy

1. **Primary**: Direct song/artist search (`"fixing her hair by ani difranco"`)
2. **Variations**: Alternative phrasings (`"ani difranco fixing her hair"`)  
3. **Album lookup**: When API fails → Claude identifies album → targeted search
4. **Artist fallback**: Broad artist search as last resort

## Usage Examples

### Main Interface

```python
from claude_music_interface import handle_music_request

# All these work reliably without complex setup
handle_music_request("play some Beatles")
handle_music_request("Neil Young's Harvest Moon")  
handle_music_request("acoustic version of Black by Pearl Jam")
handle_music_request("I want to hear Like a Hurricane")
```

### Advanced Usage

```python
from claude_music_interface import ClaudeCodeMusicAgent
from claude_api_client import get_api_client

# Create API client (optional - auto-created if not provided)
api_client = get_api_client()

# Create enhanced agent with API client
agent = ClaudeCodeMusicAgent(api_client=api_client)

# Parse natural language
parsed = agent.parse_music_request("live version of Comfortably Numb")
# Returns: {'title': 'comfortably numb', 'artist': None, 'preferences': {'prefer_live': True}}

# Handle parsed request
result = agent.handle_parsed_music_request("harvest", "neil young", {})
```

### Utility Functions

```python
from claude_music_interface import pause_music, resume_music, get_current_track

pause_music()                    # Pause playback
resume_music()                   # Resume playback  
current = get_current_track()    # Get current track info
```

## Configuration

### Required Environment

- **Sonos CLI**: Must be installed and configured (`sonos` command available)
- **Claude API Key**: Valid Anthropic API key for LLM capabilities
- **Music Service**: Amazon Music or other Sonos-compatible service

### Environment Variables

```bash
# Required
ANTHROPIC_API_KEY=your_api_key_here

# Optional
CLAUDE_MODEL=claude-3-5-sonnet-20241022  # Override default model
```

### API Key Setup

Get your API key from [Anthropic Console](https://console.anthropic.com/account/keys):

1. Sign up/login to Anthropic Console
2. Create new API key
3. Add to environment or `.env` file
4. Test with: `python -c "from claude_api_client import get_api_client; print(get_api_client().test_connection())"`

## Error Handling

### Common Issues and Solutions

**API Authentication Errors**: 
- **Problem**: `authentication_error: invalid x-api-key`
- **Solution**: Check API key is correct and has sufficient credits
- **Action**: Get new key from Anthropic Console

**No API Key Provided**:
- **Problem**: `ValueError: No API key provided`
- **Solution**: Set `ANTHROPIC_API_KEY` environment variable or create `.env` file
- **Test**: Run setup verification command

**API Rate Limiting**:
- **Problem**: `rate_limit_error` responses
- **Solution**: System automatically retries with backoff
- **Fallback**: Temporary regex parsing maintains functionality

**Sonos CLI Issues**:
- **Problem**: `sonos` command not found or music service auth expired
- **Solution**: Check Sonos CLI installation and music service authentication
- **Test**: Run `sonos what` to verify connection

## Advanced Features

### Intelligent Selection Logic

The Claude API analyzes multiple factors to select the best match:

- **Title similarity**: Exact vs fuzzy matching with normalization
- **Artist matching**: Full name and partial matches  
- **Version preferences**: Live, acoustic, studio detection
- **Album context**: Original vs compilation prioritization
- **Quality indicators**: Remaster vs original preference

### Performance Optimizations

- **Smart API usage**: Only uses Claude API when regex parsing insufficient
- **Targeted searches**: Album-based searches return fewer, more relevant results
- **Early termination**: Stops searching after finding good match
- **Graceful degradation**: Falls back to regex when API unavailable

### Logging and Monitoring

All operations are logged to `.claude_music_progress.log`:

```
[HH:MM:SS.mmm] 🎵 API Processing music request: 'fixing her hair by ani difranco'
[HH:MM:SS.mmm] 🎯 Parsing with API: 'fixing her hair by ani difranco...'
[HH:MM:SS.mmm] ✅ API parsing completed successfully
[HH:MM:SS.mmm] 🎯 Using API for track selection from 13 results
[HH:MM:SS.mmm] ✅ API selected position: 3
[HH:MM:SS.mmm] 🎵 Playing track: Fixing Her Hair by Ani DiFranco
```

## Benefits Over Previous Approach

### 🎯 Reliability Improvements
- **No Mock Responses**: Eliminates "Task completed..." failures completely
- **Consistent Behavior**: Same results in all environments (CLI, headless, subprocess)
- **Predictable Processing**: Direct API calls with clear error handling

### 🚀 Performance Benefits  
- **Faster Setup**: No complex Task function configuration required
- **Simpler Usage**: Single function call handles entire workflow
- **Better Debugging**: Clear API responses instead of mysterious mock behavior

### 🔧 Maintenance Benefits
- **Standard API Patterns**: Well-documented Anthropic SDK usage
- **Clear Error Messages**: API errors are specific and actionable
- **Environment Independent**: Works anywhere Python + API key available

## Development

### Testing

```python
# Test basic functionality (requires API key)
python test_api_implementation.py

# Test without API key (falls back to regex)
python -c "
from claude_music_interface import handle_music_request
result = handle_music_request('neil young harvest')
print(result)
"

# Test API client directly
python -c "
from claude_api_client import get_api_client
client = get_api_client()
print(client.test_connection())
"
```

### Extending the System

To add new music request patterns:
1. Update parsing prompts in `music_parsing_prompts.py`
2. Add preference handling in `_generate_smart_search_queries()`
3. Update selection logic in `_calculate_match_score()` if needed
4. Test with: `client.parse_music_request("your new pattern")`

### API Client Customization

```python
from claude_api_client import ClaudeAPIClient

# Custom model or settings
client = ClaudeAPIClient(
    api_key="your_key",
    model="claude-3-5-sonnet-20241022"  # or other models
)

# Use with music agent
from claude_music_interface import ClaudeCodeMusicAgent
agent = ClaudeCodeMusicAgent(api_client=client)
```

## Troubleshooting

### API-Related Issues

1. **"No API key provided"**
   - Set `ANTHROPIC_API_KEY` environment variable
   - Or create `.env` file with your key
   - Verify with: `echo $ANTHROPIC_API_KEY`

2. **"Authentication error"** 
   - Check API key is valid and has credits
   - Get new key from [Anthropic Console](https://console.anthropic.com/account/keys)
   - Test connection: `python -c "from claude_api_client import get_api_client; print(get_api_client().test_connection())"`

3. **Import errors**
   - Activate virtual environment: `source .venv/bin/activate`
   - Install dependencies: `pip install anthropic python-dotenv`
   - Check current directory contains the music interface files

### Sonos-Related Issues

1. **No music plays**: Check Sonos CLI configuration and music service auth
2. **Wrong song plays**: Check search results in logs, may need better search terms  
3. **"sonos command not found"**: Install and configure Sonos CLI

### Debug Mode

Monitor `.claude_music_progress.log` for detailed execution flow:
- API calls and responses
- Search strategies used
- Selection reasoning
- Error details and fallback behavior

### Performance Issues

- **Slow responses**: Check API rate limiting, may need to reduce request frequency
- **Inconsistent results**: Ensure API key has sufficient credits for reliable service
- **Memory usage**: Virtual environment isolation prevents conflicts

---

*This system transforms unreliable Task function-based music search into a robust, API-powered solution that provides consistent intelligent music processing across all environments.*
