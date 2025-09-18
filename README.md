# OP‑XY Vibe Coding

A real-time music creation system for the OP‑XY that enables collaborative composition with AI agents through a JSON-based loop format.

## Overview

This project allows you to co-create music with AI agents that edit a canonical loop JSON file (`opxyloop‑1.0`) while a Python engine plays it back in real-time to the OP‑XY device. The system prioritizes glitch-free playback, bulletproof note lifecycle management, and observable behavior with tight timing constraints.

## Quick Start

### Prerequisites

- Python 3.7+
- OP‑XY device connected via USB-C
- macOS (primary development platform)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/your-username/op-xy-vibing.git
cd op-xy-vibing
```

2. Install system dependencies (macOS):
```bash
# Install Python if not already installed
brew install python

# Install MIDI system dependencies (required for python-rtmidi)
brew install pkg-config
brew install portmidi
```

3. Install Python dependencies:
```bash
# Install the required packages
pip3 install -r requirements.txt

# Or install individually if needed:
pip3 install mido>=1.3 python-rtmidi>=1.5 websockets>=11 jsonpatch>=1.33
```

4. Verify MIDI setup:
```bash
# Check that your OP-XY is detected
python3 -c "import mido; print('Available MIDI ports:', mido.get_output_names())"
```

### Starting the System

Start the conductor server (simplest method):
```bash
python3 -m conductor.conductor_server --loop loop.json --port "OP-XY"
```

Then serve the UI in another terminal:
```bash
make ui-serve
```

Access the web interface at `http://127.0.0.1:8080`

### Running the System

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