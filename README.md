# OP‑XY Vibe Coding

**Create music collaboratively with AI agents and your OP‑XY in real-time.**

## What is this?

OP‑XY Vibe Coding lets you make music by talking to AI assistants like Claude or Codex. Instead of clicking around in a DAW, you describe what you want ("make the kick punchier", "add a subtle hi-hat shuffle", "try a darker pad sound") and the AI edits your music loop in real-time while you listen.

**How it works:**
1. Your music loop is stored as a JSON file that describes drums, bass, chords, and effects
2. A Python server reads this file and plays it on your OP‑XY via USB-C  
3. AI assistants edit the JSON while you listen, making changes instantly audible
4. You collaborate with the AI to refine the loop until it sounds exactly right

**Perfect for:**
- Quick musical idea exploration and prototyping
- Learning music production concepts through conversation  
- Breaking through creative blocks with AI collaboration
- Rapid iteration on beats, basslines, and chord progressions

## First Time Setup

**What you'll need:**
- An OP‑XY device connected via USB-C
- A Mac computer (primary platform - other platforms may work but aren't tested)
- 5-10 minutes for setup

### Step 1: Get the Code

```bash
git clone https://github.com/your-username/op-xy-vibing.git
cd op-xy-vibing
```

### Step 2: Install Dependencies

**Install system tools (if not already installed):**
```bash
# Install Python and MIDI support
brew install python pkg-config portmidi
```

**Set up Python environment:**
```bash
# Create isolated environment (recommended)
python3 -m venv venv
source venv/bin/activate

# Install music software dependencies
pip install -r requirements.txt
```

### Step 3: Test Your Setup

**Make sure your OP‑XY is detected:**
```bash
# Should show "OP-XY" in the list
python3 -c "import mido; print('MIDI ports:', mido.get_output_names())"
```

If you don't see "OP-XY" in the list, check that:
- Your OP‑XY is powered on and connected via USB-C
- The USB-C cable supports data (not just charging)
- You're using a USB-C port, not just USB-A with an adapter

### Step 4: Start Making Music

**Launch the server (keep this terminal open):**
```bash
# Activate your Python environment first
source venv/bin/activate

# Start the music server
python3 -m conductor.conductor_server --loop loop.json --port "OP-XY"
```

You should see:
```
[http] serving UI on http://127.0.0.1:8080  
[ws] Conductor listening on ws://127.0.0.1:8765
```

**Open the web interface:**
- Go to http://127.0.0.1:8080 in your browser
- You should see a loop grid with drums, bass, and other tracks
- Press play to hear the current loop on your OP‑XY

**🎉 You're ready!** The system is now running and you can start collaborating with AI assistants.

## Working with AI Assistants

This system is designed to work with AI coding assistants like Claude, Codex, or ChatGPT. The AI can help you:

**🎵 Edit your music in real-time:**
- "Make the kick drum hit harder on beats 1 and 3"
- "Add a subtle swing to the hi-hats"  
- "Try a darker, more mysterious chord progression"
- "Speed up the tempo to 128 BPM"

**🔧 Manage the system:**
- Start and stop the server
- Debug MIDI connection issues
- Add new features to the loop format
- Run tests and validate changes

**📖 Learn and explore:**
- "Explain how LFOs work in this system"
- "Show me different drum patterns I could try"
- "What's the difference between internal and external clock?"

### For AI Assistants

If you're an AI assistant helping someone with this system, check the `CLAUDE.md` file for detailed guidance on:
- How to safely start and stop the server
- The loop JSON format and how to edit it
- MIDI device safety and troubleshooting
- Testing and validation procedures

## Advanced Usage

#### Basic Playback
Play a loop with internal clock:
```bash
make play-internal LOOP=loop.json BPM=120 PORT="OP-XY"
```

Play with external clock (OP‑XY as master):
```bash
make play-external LOOP=loop.json PORT="OP-XY"
```

#### Full Conductor Server (with WebSocket API)
Alternative using Makefile:
```bash
make conductor-run LOOP=loop.json PORT="OP-XY" BPM=120 CLOCK=external
```

Direct command with all options:
```bash
python3 -m conductor.conductor_server \
  --loop loop.json \
  --port "OP-XY" \
  --bpm 120 \
  --clock-source external \
  --ws-host 127.0.0.1 \
  --ws-port 8765
```

### Testing the Installation

Run clock timing tests:
```bash
make clock-smoke
```

Test note lifecycle:
```bash
make demo-note
```

Run the full test suite:
```bash
make test
```

Validate loop fixtures:
```bash
make validate-fixtures
```

## System Architecture

```
Human ⇄ LLM (Agent)
          │
          ▼
   Conductor (single origin)
     ├── HTTP UI (static)
     ├── WebSocket API (doc/state/metrics)
     ├── File watcher (atomic write/watch)
     ├── Git (batched commits)
     └── Playbook Engine ⇄ OP‑XY (USB‑C MIDI)

Spec: docs/opxyloop-1.0.md (normative)
```

## Key Features

- **Real-time MIDI playback** with external or internal clock sync
- **JSON-based loop format** optimized for AI agent collaboration
- **WebSocket API** for live editing and state monitoring
- **Atomic file operations** with Git version control
- **Robust note lifecycle** management with panic recovery
- **CC and LFO automation** with phase-locked modulation
- **Web-based UI** for visual loop editing

## Loop Format

Loops are defined using the `opxyloop‑1.0` JSON specification. See `docs/opxyloop-1.0.md` for the complete format documentation.

Example minimal loop:
```json
{
  "version": "opxyloop-1.0",
  "meta": {
    "tempo": 120,
    "ppq": 96,
    "stepsPerBar": 16
  },
  "tracks": [
    {
      "type": "drum",
      "channel": 10,
      "steps": [
        {"vel": 110}, null, null, null,
        {"vel": 90}, null, null, null,
        {"vel": 110}, null, null, null,
        {"vel": 90}, null, null, null
      ]
    }
  ]
}
```

## Available Commands

### Playback
- `make play-internal` - Play with internal clock
- `make play-external` - Play with external clock (OP‑XY master)
- `make conductor-run` - Start full conductor server

### Development
- `make test` - Run test suite  
- `make clock-smoke` - Test timing accuracy
- `make demo-note` - Test note lifecycle
- `make validate` - Validate a loop file
- `make validate-fixtures` - Validate all test fixtures

### Utilities
- `make panic` - Send MIDI panic (All Notes Off)
- `make kill-procs` - Kill running processes
- `make ui-serve` - Serve web interface

### WebSocket Control
- `make ws-tempo BPM=130` - Change tempo via WebSocket
- `make ws-patch-vel VEL=105` - Modify velocity via JSON patch

## Development Status

This project is in active development. See `PROJECT_PLAN.md` for detailed roadmap and current milestone progress.

### Current Features ✅
- Loop JSON validation and canonical formatting
- Real-time MIDI playback engine
- Internal and external clock synchronization
- Note lifecycle management with panic recovery
- WebSocket API for live control
- Basic web UI for loop visualization

### Planned Features 🚧
- Advanced web UI with step sequencer grid
- Multi-track drum support with choke groups
- Enhanced LFO and automation features
- Seek/catch-up functionality
- Device profile management

## File Structure

```
conductor/          # Core playback engine and server
├── midi_engine.py  # Real-time MIDI scheduling
├── clock.py        # Internal/external clock handling  
├── ws_server.py    # WebSocket API server
├── validator.py    # Loop JSON validation
└── tests/          # Test suite and fixtures

ui/                 # Web interface
├── index.html      # Main UI page
└── app.js         # Frontend JavaScript

docs/               # Documentation
├── opxyloop-1.0.md # Loop format specification
└── ...            # Additional documentation

tools/              # Utilities
├── wsctl.py       # WebSocket client for testing
└── panic.py       # Emergency MIDI panic

favorites/          # Example loops
├── demo-loop-*.json
└── ...
```

## Contributing

1. Read the `PROJECT_PLAN.md` for architecture and milestone details
2. Check the test suite runs: `make test`
3. Validate timing: `make clock-smoke`
4. Follow the loop specification in `docs/opxyloop-1.0.md`

## License

This project is open source. See `LICENSE` file for details.

## Troubleshooting

### Installation Issues

#### Python/pip not found
```bash
# On macOS, install Python via Homebrew
brew install python

# Use python3 and pip3 explicitly
python3 --version
pip3 --version
```

#### python-rtmidi installation fails
```bash
# Install system dependencies first
brew install pkg-config portmidi

# Then retry pip install
pip3 install python-rtmidi>=1.5
```

#### ModuleNotFoundError
```bash
# Make sure you're in the project directory
cd op-xy-vibing

# Verify dependencies are installed
pip3 list | grep -E "(mido|rtmidi|websockets|jsonpatch)"

# Reinstall if needed
pip3 install -r requirements.txt
```

### MIDI Connection Issues
- Ensure OP‑XY is connected via USB-C
- Check MIDI port name: `python3 -c "import mido; print(mido.get_output_names())"`
- Use correct port name in `PORT` parameter

### Timing Problems
- Run `make clock-smoke` to check timing accuracy
- External clock issues: verify OP‑XY is sending MIDI clock
- High jitter: close other applications, check CPU load

### WebSocket Errors
- Kill existing processes: `make kill-procs`
- Check port 8765 availability: `make kill-ws-port`
- Restart conductor: `make conductor-run`

### Note Hanging
- Send MIDI panic: `make panic PORT="OP-XY"`
- Check active notes are properly tracked in logs
- Verify All Notes Off on transport stop