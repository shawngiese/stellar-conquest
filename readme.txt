INSTALL
Requires - Python 3.7+ and pip (Python package installer)
Clone or Download the Project
Run "pip install -r requirements.txt"


START
Typically takes about 3 minutes to run on a modern PC. 

Attempting to simulate the board game Stellar Conquest. It has always proven hard to audit the game progress so hoping this also helps understand new techniques to track the game state.

RUN 
Execute either the following and see the logs as they are generated
python auto_demo_enhanced_maps.py | tee output/output_statsTEST.txt

or the following, but no onscreen updates for 3 minutes
python auto_demo_enhanced_maps.py > output/outputTEST.txt

Typical run time is 3 minutes, 2 for the simulation and 1 more for writing a lot of map files.

THEN
open map_index.html
maps are SVG so you can zoom your browser in to see details.

OPTIONAL
Other tools 
- audit_players.py
  What it does: Splits any output_statsXX.txt file into individual player files with clean formatting and
  helpful commands.

  Usage:
  python audit_players.py output/outputTEST.txt 
  python audit_players.py --list
  python audit_players.py --help


- audit_taskforce.py
  What it does: Creates detailed movement audit logs for each player's taskforces showing:
  - All 44 turns of activity (or gaps)
  - Complete ship compositions at creation
  - Turn-by-turn movement tracking
  - Missing turn identification

  Usage:
  python audit_taskforce.py output/outputTEST.txt
  python audit_taskforce.py --list


IDEAS
Enable things like
* Game state - Central state manager that tracks the entire game and records all actions for analysis
* Players state - Represents each player with their ships, colonies, technologies, and play style
* Action manager - Handles all game actions (movement, exploration, combat, colonization, production)
* AI decision system - Makes intelligent decisions based on configurable play styles
* Intelligence log - To capture what each player knows about the universe and their opponents

CHANGES
To simplify the simulation some decisions:
* sending ships to battle an opponent star hex first start with a rally starhex for the various desired warships to come together and then travel together for the battle
* There is a 44th round production run. Maybe players build ships in systems that will give them victory points.

TODO
Lots os stuff!
For example:
* Why are there so few combats?
* Nobody tries to conquer another's colonies
* Enable What-If Scenarios to run combat, production and strategy scenarios
* Monte Carlo support - to run thousands of iterations for statistical significance
* Clean up fly distance markings on the map
* Some ships keep trying to go back to their destination very often, ships that flee a warship hex should have a chance to make a new destination.

version 2
* In the off chance a task force with colonists arrives at a star hex and there are no suitable planets, then they must target a new star hex.
* Added more hostilities so warships are sometimes used for battle.
