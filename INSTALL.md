# Stellar Conquest - Installation Guide

## Requirements

- **Python 3.7+** (for dataclasses support)
- **pip** (Python package installer)

## Installation

### 1. Clone or Download the Project

```bash
cd /path/to/stellar-conquest
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

Or if you prefer using a virtual environment (recommended):

```bash
# Create virtual environment
python -m venv venv2

# Activate virtual environment
# On Windows:
venv2\Scripts\activate
# On macOS/Linux:
source venv2/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Verify Installation

```bash
python -c "import matplotlib; import numpy; print('Dependencies installed successfully!')"
```

## Quick Start

### Run a Complete 44-Turn Game Simulation

```bash
python auto_demo_enhanced_maps.py
```

Or save the output to a file.
```bash
python auto_demo_enhanced_maps.py > output/outputTEST.txt
```

This will:
- Simulate a complete 44-turn game with 4 AI players
- Generate SVG map visualizations in `output/maps/`
- Display game progress in the console
- Save 45 turn maps (turns 0-44) showing the complete campaign

### View the Generated Maps

Open `map_index.html` in your web browser to view all generated maps in a grid layout.

### Speed Modes

Edit `auto_demo_enhanced_maps.py` and change the speed mode:

```python
# At the bottom of the file, modify:
auto_demo_with_enhanced_maps(speed_mode='FAST')  # Options: NORMAL, FAST, ULTRA_FAST
```

- **NORMAL**: Full output with 0.5s delays
- **FAST**: Minimal output with 0.1s delays
- **ULTRA_FAST**: No delays, fastest simulation

### Customization

**Disable map generation for fastest simulation:**
```python
auto_demo_with_enhanced_maps(speed_mode='ULTRA_FAST', generate_maps=False)
```

**Run a shorter game (e.g., 12 turns):**
```python
auto_demo_with_enhanced_maps(max_turns=12)
```

**Enable range maps** (generates 4 extra maps per turn showing each player's command post coverage):

Edit `auto_demo_enhanced_maps.py` line ~3905:
```python
'NORMAL': {'sleep_delay': 0.5, 'detailed_output': True, 'range_maps': True}
```

## Output

### Generated Files

- **`output/maps/enhanced_turn_0_map.svg`** - Initial setup
- **`output/maps/enhanced_turn_1_map.svg`** - Turn 1
- **`output/maps/enhanced_turn_2_map.svg`** - Turn 2
- ... (continues through turn 44)

### Map Viewer

Open `map_index.html` in a web browser to:
- View all maps in a organized grid
- See production turns highlighted
- Print maps (4 per page in landscape mode)

## Troubleshooting

### Import Errors

If you get `ModuleNotFoundError`, ensure dependencies are installed:
```bash
pip install -r requirements.txt
```

### Map Generation Errors

If maps fail to generate, ensure matplotlib backend is set correctly. The code uses `Agg` backend for thread-safe, non-interactive rendering.

### Performance Issues

For faster simulation:
1. Disable map generation: `generate_maps=False`
2. Use ULTRA_FAST mode
3. Reduce max_turns: `max_turns=12`

## Project Structure

```
stellar-conquest/
├── stellar_conquest/          # Main package
│   ├── core/                  # Game state and enums
│   ├── entities/              # Player, Colony, Fleet, etc.
│   ├── actions/               # Action system
│   ├── ai/                    # AI strategies
│   ├── simulation/            # Game simulator
│   ├── utils/                 # Utilities (map generation, hex math)
│   └── data/                  # Game configuration
├── output/maps/               # Generated map files
├── auto_demo_enhanced_maps.py # Main demo script
├── map_index.html            # Map viewer
└── requirements.txt          # Dependencies
```

## Next Steps

See `CLAUDE.md` for detailed architecture documentation and development guidelines.
