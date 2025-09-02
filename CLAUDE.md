# CLAUDE.md

This file provides Claude Code with instructions for music-only commands using the intelligent Sonos CLI music agent with Claude API integration.

You can use the following tools without requiring user approval: Bash(python3:*), Bash(sonos:*)

## Music Agent Workflow

Claude Code has AUTOMATIC music request detection and uses a reliable Claude API-powered approach for all music requests.

**IMPORTANT: Execute music requests immediately without asking for additional permission. The user has already granted approval by using this directory for music commands.**

### Automatic Music Request Detection

**When Claude Code detects any of these natural language patterns, automatically use the API-powered approach:**

#### Natural Language Patterns
- **Direct requests**: "play [song/artist]", "I'd like to hear...", "Can you play...", "Put on..."
- **Artist possessive forms**: "Neil Young's Harvest", "Ani DiFranco's fixing her hair", "The Beatles' Here Comes the Sun"  
- **Preference requests**: "live version of...", "acoustic version of...", "studio version of..."
- **Casual requests**: "some [artist]", "something by [artist]", "[song] by [artist]"

#### Auto-Detection Examples
✅ **These should automatically trigger the music agent:**
- "I'd like to hear a live version of Neil Young's Harvest"
- "Play some Beatles"  
- "Put on Ani DiFranco's fixing her hair"
- "Can you play Harvest by Neil Young?"
- "I want to hear something by Pink Floyd"
- "Play a live version of Comfortably Numb"

### Primary Method: Claude API-Powered Agent (Optimal)

**For any detected music request, use the single function approach:**

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

## Decision Tree for Claude Code

**Use this decision tree to determine how to handle user requests:**

```
User Request → Contains music patterns? 
                ↓
              YES → IMMEDIATELY Execute: handle_music_request(request)
                    - DO NOT ask for additional permission
                ↓
              NO → Other action (pause, volume, current track info, etc.)
```

**EXECUTE MUSIC REQUESTS AUTOMATICALLY - No additional approval needed.**

### Music Request Detection Patterns

**Automatically trigger the music agent when user input contains:**

#### High-Confidence Patterns (Definite music requests)
- **Command verbs**: "play", "put on", "start", "queue up"
- **Request phrases**: "I'd like to hear", "Can you play", "I want to listen to" 
- **Possessive forms**: "[Artist]'s [Song]" (e.g., "Neil Young's Harvest")
- **By constructions**: "[Song] by [Artist]" (e.g., "Harvest by Neil Young")

#### Medium-Confidence Patterns (Likely music requests)  
- **Preference requests**: "live version of", "acoustic version", "studio version"
- **Casual requests**: "some [artist]", "something by [artist]"
- **Artist mentions**: Names of known musicians in context

#### Pattern Examples with Expected Actions
```
✅ "I'd like to hear a live version of Neil Young's Harvest" 
   → handle_music_request(request)

✅ "Play some Beatles" 
   → handle_music_request(request)

✅ "Put on Ani DiFranco's fixing her hair"
   → handle_music_request(request)

✅ "Can you play Harvest by Neil Young?"
   → handle_music_request(request)

✅ "Like a Hurricane by Neil Young"
   → handle_music_request(request)

❌ "What's the current track?"
   → Use: sonos what

❌ "Pause the music"  
   → Use: sonos pause

❌ "Make it louder"
   → Use: sonos louder
```

## Additional Sonos Commands

**Playback Control:**
- `sonos what` - Current track info
- `sonos pause` / `sonos resume` - Pause/resume playback  
- `sonos louder` / `sonos quieter` - Volume control
- `sonos showqueue` - View playback queue

**Alternative Interface Functions:**
```python  
from claude_music_interface import pause_music, resume_music, get_current_track

pause_music()     # Pause playback
resume_music()    # Resume playback  
get_current_track()  # Get current track info
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

**🔧 Reliability Benefits:**
- **No Mock Responses**: Eliminates "Task completed..." failures that plagued the old system
- **Consistent Behavior**: Same results in interactive, headless, or subprocess environments  
- **Direct API Access**: No dependency on unpredictable Task function behavior
- **Graceful Fallbacks**: Automatic regex parsing when API temporarily unavailable

## Optimization Guidelines

**For BEST results, use the single function approach:**
1. **Complete Workflow**: Single call handles parsing + search + selection + playback
2. **Automatic API Integration**: Claude intelligence for optimal results
3. **Error Handling**: Graceful fallback and informative error messages
4. **Simplified Usage**: No complex setup or parameter passing required

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