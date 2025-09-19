# Sample Loops Collection

This directory contains curated example loops demonstrating different musical styles and AI collaboration techniques. Each loop includes metadata with creation prompts to inspire your own musical experiments.

## How to Use These Samples

1. **Load a sample loop:**
   ```bash
   # Copy any sample to your working loop
   cp samples/house/house-chorus-8bar.json loop.json
   
   # Start the server
   source venv/bin/activate
   python3 -m conductor.conductor_server --loop loop.json --port "OP-XY"
   ```

2. **Experiment with the AI prompts:**
   - Try the original creation prompts in the metadata files
   - Use them as starting points for your own variations
   - Ask AI assistants to modify elements you want to change

3. **Learn from the patterns:**
   - Study how different genres use velocity, timing, and note patterns
   - Observe how tracks layer together (drums, bass, melody, chords)
   - Notice the use of microshift timing for groove and humanization

## Sample Categories

### 🏠 House (`house/`)
Classic 4/4 house music patterns with driving kicks, shuffled hi-hats, and chord progressions.

### 🤖 Techno (`techno/`)
Hard-hitting electronic beats with industrial sounds and driving energy.

### 🌙 Downtempo (`downtempo/`)
Slower, more atmospheric pieces perfect for ambient and chill music.

### 📚 Demo (`demo/`)
Educational examples showing progression from basic drums to full arrangements.

## Sample Loop Details

| File | BPM | Style | Tracks | Description |
|------|-----|-------|---------|-------------|
| `house/house-chorus-8bar.json` | 125 | House | Drums, Bass, Chords, Melody | Full house arrangement with classic elements |
| `techno/midnight-express.json` | 138 | Techno | Multiple percussion tracks | Driving techno beat with complex rhythm |
| `downtempo/lullaby-beat.json` | 76 | Ambient | Lead, rhythm elements | Gentle, atmospheric composition in F major |
| `demo/basic-drums.json` | 125 | Educational | Drums only | Simple 4/4 drum pattern for learning |
| `demo/drums-with-bass.json` | 125 | Educational | Drums + Bass | Basic drums with added bassline |

## Creating Your Own Samples

When you create interesting loops, consider contributing them back:

1. **Document your process:**
   - Save the AI prompts that created interesting results
   - Note what musical concepts you were exploring
   - Include any happy accidents or unexpected discoveries

2. **Create clear metadata:**
   - Musical style and influences
   - Key signatures and scales used
   - Tempo and time signature
   - Track breakdown and roles

3. **Share your discoveries:**
   - What AI prompts worked well?
   - What techniques produced interesting results?
   - What would you do differently next time?

---

*These samples demonstrate the collaborative potential between humans and AI in music creation. Use them as inspiration, learning tools, and starting points for your own musical journeys.*