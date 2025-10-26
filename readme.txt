INSTALL
Requires - Python 3.7+ and pip (Python package installer)
Clone or Download the Project
Run "pip install -r requirements.txt"


START
Typically takes about 3 minutes to run on a modern PC. 

Attempting to simulate the board game Stellar Conquest. It has always proven hard to audit the game progress so hoping this also helps understand new techniques to track the game state.

RUN 
Execute either the following and see the logs as they are generated
python3 auto_demo_enhanced_maps.py | tee output/output_statsTEST.txt

or the following, but no onscreen updates for 3 minutes
python auto_demo_enhanced_maps.py > output/outputTEST.txt

Typical run time is 3 minutes, 2 for the simulation and 1 more for writing a lot of map files.

THEN
open map_index.html

OPTIONAL
Other tools 
- audit_players.py
  What it does: Splits any output_statsXX.txt file into individual player files with clean formatting and
  helpful commands.

  Usage:
  python3 audit_players.py output/outputTEST.txt 
  python3 audit_players.py --list
  python3 audit_players.py --help


- audit_taskforce.py
  What it does: Creates detailed movement audit logs for each player's taskforces showing:
  - All 44 turns of activity (or gaps)
  - Complete ship compositions at creation
  - Turn-by-turn movement tracking
  - Missing turn identification

  Usage:
  python3 audit_taskforce.py output/outputTEST.txt
  python3 audit_taskforce.py --list


IDEAS
Enable things like
* Game state - Central state manager that tracks the entire game and records all actions for analysis
* Players state - Represents each player with their ships, colonies, technologies, and play style
* Action manager - Handles all game actions (movement, exploration, combat, colonization, production)
* AI decision system - Makes intelligent decisions based on configurable play styles
* Intelligence log - To capture what each player knows about the universe and their opponents



TODO
Lots os stuff!
For example:
* Why are there so few combats?
* Nobody tries to conquer another's colonies
* Enable What-If Scenarios to run combat, production and strategy scenarios
* Monte Carlo support - to run thousands of iterations for statistical significance
