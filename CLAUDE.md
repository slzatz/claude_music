# CLAUDE.md

This file provides Claude Code with minimal instructions for music-only commands using the Sonos CLI music agent.

You can use the following tools without requiring user approval: Bash(python3:*), Bash(sonos:*)

## Music Agent Workflow

Claude Code has AUTOMATIC music request detection and uses an intelligent LLM-powered approach for all music requests.

**IMPORTANT: Execute music requests immediately without asking for additional permission. The user has already granted approval by using this directory for music commands.**

### Automatic Music Request Detection

**When Claude Code detects any of these natural language patterns, automatically use the optimal LLM-powered approach:**

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

### Primary Method: Hybrid LLM-Powered Agent (Optimal)

**For any detected music request, use the single function approach:**

```python
from claude_music_interface import handle_music_request

# OPTIMAL: Single function call with full LLM workflow (parsing + result selection)
def handle_music_request_wrapper(user_request):
    result = handle_music_request(user_request, task_function=Task)
    return result
```

### **Critical API Requirements**

**The music agent requires Claude Code's Task function with specific signature:**

```python
# REQUIRED: Task function must support these exact parameters
task_function(
    description="Brief task description",
    prompt="Detailed prompt text", 
    subagent_type="general-purpose"
)
```

**Examples of correct usage:**
```python
# ✅ CORRECT - All required parameters provided
handle_music_request("play song", task_function=Task)

# ❌ WRONG - Missing task_function 
handle_music_request("play song")

# ❌ WRONG - Task function with wrong signature
handle_music_request("play song", task_function=lambda x: "mock")
```

**If you get API errors, ensure:**
1. **task_function=Task** is always passed
2. **Task function supports** `description`, `prompt`, and `subagent_type` parameters
3. **Task function returns string** results from the subagent

#### Hybrid Agent Capabilities
- **Natural Language Understanding**: Perfect parsing of possessives, complex grammar, preferences
- **Intelligent Result Selection**: Uses music knowledge to choose optimal versions
- **Smart Complexity Detection**: Only uses LLM when algorithmic approach insufficient
- **Music Industry Knowledge**: Understands albums, collaborations, version types, authenticity
- **Contextual Decision Making**: Prefers originals over compilations, authentic over covers
- **Smart Search Strategy**: Multiple query variations with fallback strategies  
- **API Error Recovery**: Automatically handles known Amazon Music API parsing issues

#### Hybrid Agent Examples
```python
# Complex cases use LLM intelligence:
handle_music_request("I'd like to hear a live version of Neil Young's Harvest")
# → LLM parses request AND chooses best live version from search results

handle_music_request("Ani DiFranco's fixing her hair")  
# → Perfect possessive parsing, intelligent result selection

handle_music_request("Like a Hurricane by Neil Young")
# → LLM chooses original studio album over compilations/covers

# Simple cases use fast algorithmic selection:
handle_music_request("Bohemian Rhapsody by Queen")  
# → Fast selection without LLM overhead for obvious matches
```

## Decision Tree for Claude Code

**Use this decision tree to determine how to handle user requests:**

```
User Request → Contains music patterns? 
                ↓
              YES → IMMEDIATELY Execute: handle_music_request(request, task_function=Task)
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
   → handle_music_request(request, task_function=Task)

✅ "Play some Beatles" 
   → handle_music_request(request, task_function=Task)

✅ "Put on Ani DiFranco's fixing her hair"
   → handle_music_request(request, task_function=Task)

✅ "Can you play Harvest by Neil Young?"
   → handle_music_request(request, task_function=Task)

✅ "Like a Hurricane by Neil Young"
   → handle_music_request(request, task_function=Task)

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

## Standardized Prompt System

The music request parsing uses **standardized prompt templates** for consistent behavior:

```python
from claude_music_interface import parse_music_request_llm

# Use standardized parsing (requires Claude Code Task function)
parsed = parse_music_request_llm(
    "I'd like to hear a live version of Neil Young's Harvest",
    task_function=Task  # Claude Code provides this
)

# Returns consistent format:
# {
#   "title": "harvest",
#   "artist": "neil young", 
#   "preferences": {"prefer_live": true}
# }
```

### Key Advantages of Hybrid Approach

**🎯 Intelligent Result Selection Examples:**
- **"Like a Hurricane by Neil Young"**: Chooses original "American Stars 'N Bars" album over Greatest Hits compilation
- **"Harvest Moon live"**: Finds live recordings from concert albums like "Live at Massey Hall" 
- **"Unplugged version of..."**: Understands MTV Unplugged albums are acoustic performances
- **Multiple remasters**: Prefers original releases over anniversary/deluxe editions when no preference specified

## Optimization Guidelines

**For BEST results, use the single function approach:**
1. **Complete Workflow**: Single call handles parsing + search + selection + playback
2. **Automatic LLM Integration**: Hybrid intelligence for optimal results
3. **Error Handling**: Graceful fallback and informative error messages
4. **Simplified Usage**: No need to manage multi-step workflows manually

## Troubleshooting

### **Common API Errors and Fixes**

**Error: "Task function required"**
```python
# Fix: Always pass task_function=Task
handle_music_request("play song", task_function=Task)
```

**Error: "got an unexpected keyword argument 'description'"**
```python
# Fix: Ensure Task function accepts all required parameters
# Your Task function must support:
Task(description="...", prompt="...", subagent_type="general-purpose")
```

**Error: "LLM returned non-JSON response"**
- This is handled automatically with fallback parsing
- The system will continue to work using regex parsing

**Multiple Process Retries:**
- Normal behavior when API discovery is happening
- After first successful call, subsequent calls should be fast
- Each retry helps Claude Code learn the correct API usage
