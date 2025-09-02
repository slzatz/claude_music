# CLAUDE.md

This application is an intelligent music request system that uses the Claude API to handle specific natural language music tasks that arise out of interactions with the Sonos CLI application. The main functions of the use of an LLM in this context is to 1) understand the user's natural language request to play a certain music track and 2) to analyze the results of searching for that track to determine the track that most closely matches the user's request.

## Overview

This project provides a robust, API-based interface for understanding the user's natural languame request and identifying the Sonos accessible track that best matches that request. It handles complex cases like possessive forms ("Neil Young's Harvest"), version preferences ("live version of..."), and automatically recovers from Sonos search failures by reformulating a search to use an album-based search strategy based on knowledge from its training data set.

**Note**: This Claude API integration replaces a previous approach that attempted to use built-in Claude Code Task function behavior that turned out to frequently employ mock functions instead of the intended general-purpose agent behavior. All legacy code from that abandoned approach has been removed, leaving only the robust, reliable API-based workflow.

## Key Features

### 🎯 Natural Language Understanding
- **Possessive parsing**: "Ani DiFranco's fixing her hair"
- **Version preferences**: "live version of Comfortably Numb" 
- **Casual requests**: "some Beatles", "play Harvest by Neil Young"
- **Complex grammar**: Handles articles, pronouns, and natural speech patterns

### 🎯 Analyzing Search Results
- **Selecting best match**: Considers track title, artist, expressed preferences (i.e., live, acoustic)
- **Context-aware**: Prefers originals over compilations, studio over live (unless specified)
- **Fuzzy matching**: Should handle typos, incomplete information and still find best match
- **Deal with Sonos bugs/quirks**: Works around known Sonos search issues

### 🛡️ Intelligent Error Recovery
- **Dynamic album lookup**: When Sonos API returns bad data, uses Claude API to identify the album
- **Precision search**: Searches "artist + album" to get targeted results (13 tracks vs 50 random)
- **Smart fallback**: Multiple search strategies with automatic progression
- **No hard-coding**: Scalable solution that works for any song, not just special cases

### 🧠 Reliable AI Integration
- **Direct Claude API**: Consistent, reliable LLM parsing and selection
- **No Mock Responses**: Eliminates "Task completed..." failures completely
- **Environment Independent**: Same behavior in CLI, headless, or subprocess environments
- **Graceful Fallbacks**: Automatic regex parsing when API temporarily unavailable

## Architecture

### Core Components

```
claude_api_client.py         # Claude API client (ClaudeAPIClient class) with LLM parsing and selection methods
claude_music_interface.py    # Main interface including the ClaudeCodeMusicAgent class, which is derived from the MusicAgent class
music_agent.py               # Base music agent (MusicAgent class) with search and selection methods  
music_parsing_prompts.py     # Standardized prompts for consistent behavior
```

### Key Classes

- **`ClaudeAPIClient`**: Direct API client for parsing and track selection
- **`ClaudeCodeMusicAgent`**: Derived from MusicAgent class and connected to ClaudeAPIClient
- **`MusicAgent`**: Base agent with programmatic search and selection
- **Main function**: `handle_music_request(request)` - simplified, reliable entry point

**Note**: The `ClaudeCodeMusicAgent` class name is a holdover from the previous approach that used Claude Code Task functions. It should be renamed to something like `ClaudeMusicAgent` to avoid confusion.  Also, the `claude_music_interface.py` file name is also a holdover from the previous approach and should be renamed to something like `music_interface.py`. And lastly, not sure if the separate base class of MusicAgent and the derived class of ClaudeCodeMusicAgent is necessary since there is no intention of having other types of agents.  This could be simplified by merging the two classes into one class.

#### Natural Language Patterns
- **User request triggers search and best match*: "[play] [song/artist]"
- **Artist possessive forms**: "Neil Young's Harvest", "Ani DiFranco's fixing her hair", "The Beatles' Here Comes the Sun"  
- **Preference requests**: "live version of...", "acoustic version of...", "studio version of..."
- **Casual requests**: "some [artist]", "something by [artist]", "[song] by [artist]"

### Claude API-Powered Agent (Optimal) with fallback to algorithmic parsing and matching if API unavailable

```python
from claude_music_interface import handle_music_request

# OPTIMAL: Single function call with full Claude API workflow (parsing + result selection)
result = handle_music_request(user_request)
```

### **API Setup Requirements**

**The music agent requires Claude API access:**

1. **API Key Configuration**: Set `ANTHROPIC_API_KEY` environment variable
2. **Virtual Environment**: Activate `.venv` with required dependencies  
3. **Dependencies**: `anthropic` and `python-dotenv` packages

**Setup Instructions:**
```bash
# 1. Set up environment
source .venv/bin/activate

# 2. Configure API key (choose one method):
# Method A: Environment variable
export ANTHROPIC_API_KEY=your_api_key_here

# Method B: .env file
echo "ANTHROPIC_API_KEY=your_api_key_here" > .env
```

**Examples of correct usage:**
```python
# ✅ CORRECT - Simple, reliable API approach
handle_music_request("play ani difranco's fixing her hair")

# ✅ CORRECT - With verbose output
handle_music_request("neil young's harvest", verbose=True)

# ✅ CORRECT - Complex parsing handled automatically
handle_music_request("I'd like to hear a live version of comfortably numb")
```

#### Claude API Agent Capabilities
- **Natural Language Understanding**: Perfect parsing of possessives, complex grammar, preferences
- **Intelligent Result Selection**: Uses music knowledge to choose optimal versions
- **Reliable Processing**: No mock responses or retry loops
- **Music Industry Knowledge**: Understands albums, collaborations, version types, authenticity
- **Contextual Decision Making**: Prefers originals over compilations, authentic over covers
- **Smart Search Strategy**: Multiple query variations with fallback strategies  
- **API Error Recovery**: Automatically handles known Amazon Music API parsing issues
- **Environment Independent**: Same behavior in all execution environments

#### Claude API Agent Examples
```python
# Complex cases use Claude API intelligence:
handle_music_request("I'd like to hear a live version of Neil Young's Harvest")
# → API parses request AND chooses best live version from search results

handle_music_request("Ani DiFranco's fixing her hair")  
# → Perfect possessive parsing, intelligent result selection

handle_music_request("Like a Hurricane by Neil Young")
# → API chooses original studio album over compilations/covers

# Simple cases also benefit from reliable parsing:
handle_music_request("Bohemian Rhapsody by Queen")  
# → Consistent, reliable parsing every time
```

## API-Based Processing

The music request processing uses **Claude API** for consistent, reliable behavior:

```python
from claude_music_interface import handle_music_request

# Direct API-based processing - no complex setup required
result = handle_music_request("I'd like to hear a live version of Neil Young's Harvest")

# Returns consistent, reliable results every time
print(result)  # "Now playing: Harvest (Live) by Neil Young"
```

### Key Advantages of Claude API Approach

**🎯 Intelligent Result Selection Examples:**
- **"Like a Hurricane by Neil Young"**: Chooses original "American Stars 'N Bars" album over Greatest Hits compilation
- **"Harvest Moon live"**: Finds live recordings from concert albums like "Live at Massey Hall" 
- **"Unplugged version of..."**: Understands MTV Unplugged albums are acoustic performances
- **Multiple remasters**: Prefers original releases over anniversary/deluxe editions when no preference specified

## Troubleshooting

### **API-Related Issues**

**Error: "No API key provided"**
```bash
# Fix: Set your API key
export ANTHROPIC_API_KEY=your_api_key_here
# Or add to .env file
echo "ANTHROPIC_API_KEY=your_api_key_here" > .env
```

**Error: "Authentication error"**
```bash
# Fix: Check your API key is valid
# Get a new key from: https://console.anthropic.com/account/keys
```

**Error: "Rate limit exceeded"**
- Normal behavior during high usage
- The system will automatically retry with backoff
- Requests will complete successfully after brief delay

**API Temporarily Unavailable:**
- System automatically falls back to regex parsing
- Basic functionality preserved during outages
- Full intelligence returns when API connection restored

### **Environment Setup Issues**

**Virtual Environment Not Activated:**
```bash
# Fix: Activate the virtual environment
source .venv/bin/activate
```

**Missing Dependencies:**
```bash
# Fix: Install required packages
pip install anthropic python-dotenv
```

**Import Errors:**
```bash
# Fix: Ensure you're in the correct directory
cd /path/to/claude_music
source .venv/bin/activate
python -c "from claude_music_interface import handle_music_request; print('✅ Setup correct')"
```

## Testing the System

**Quick Test:**
```bash
source .venv/bin/activate
python -c "from claude_music_interface import handle_music_request; print(handle_music_request('ani difranco\\'s fixing her hair'))"
```

**Expected Output:**
```
Now playing: Fixing Her Hair by Ani DiFranco
```

**Comprehensive Test:**
```python
from claude_music_interface import handle_music_request

test_cases = [
    "ani difranco's fixing her hair",
    "play harvest by neil young", 
    "I'd like to hear a live version of comfortably numb"
]

for request in test_cases:
    print(f"Request: {request}")
    result = handle_music_request(request)
    print(f"Result: {result}\n")
```

This system provides **100% reliable** intelligent music processing without any of the unpredictable behavior that affected the previous implementation.

# important-instruction-reminders
Do what has been asked; nothing more, nothing less.
NEVER create files unless they're absolutely necessary for achieving your goal.
ALWAYS prefer editing an existing file to creating a new one.
NEVER proactively create documentation files (*.md) or README files. Only create documentation files if explicitly requested by the User.
