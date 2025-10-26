# updates for clouds
import matplotlib.pyplot as plt
import numpy as np

def plot_hex_map():
    fig, ax = plt.subplots(figsize=(12, 12))
    ax.set_aspect('equal')
    ax.axis('off')

    num_columns = 32
    hex_radius = 0.5

    # Calculate the coordinates for each hex
    coordinates = []
    for col in range(num_columns):
        num_rows = 21 if col % 2 == 0 else 20
        for row in range(num_rows):
            x = col * hex_radius * 1.5
            y = row * hex_radius * np.sqrt(3) + (col % 2) * hex_radius * np.sqrt(3) / 2
            coordinates.append((x, y))
            label = get_hex_label(col, row, num_rows)
            ax.text(x, y+.2, label, ha='center', va='bottom', fontsize=5, color="turquoise")  #hex id

    # Plot each hex
    for coord in coordinates:
        x, y = coord
        hex_coords = get_hex_vertices(x, y, hex_radius)
        hex_polygon = plt.Polygon(hex_coords, edgecolor='turquoise', facecolor='teal')
        ax.add_patch(hex_polygon)

    # Set the limits and aspect ratio
    x_min = -1 * hex_radius
    x_max = num_columns * hex_radius * 1.5 + hex_radius
    y_min = -1 * hex_radius
    y_max = num_rows * hex_radius * np.sqrt(3) + hex_radius * np.sqrt(3) / 2
    ax.set_xlim(x_min, x_max)
    ax.set_ylim(y_min, y_max)
    ax.set_aspect('equal')

    plt.show()

def get_hex_vertices(center_x, center_y, radius):
    angles = np.linspace(0, 2 * np.pi, 7)
    x_coords = center_x + radius * np.cos(angles)
    y_coords = center_y + radius * np.sin(angles)
    return list(zip(x_coords, y_coords))

def get_hex_label(col, row, num_rows):
    letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    col_label = '' 

    # for the first 26 columns [A-Z]
    if col < len(letters): 
        col_label = letters[col]
    # for the next columns [AA, BB, ..., ZZ]
    else:
        first_index = ((col - len(letters)) % len(letters))
        col_label = letters[first_index] * 2

    row_label = str(num_rows - row)
    return col_label + row_label

def coordinate_converter(coordinate):
    letters_to_numbers = {letter: num for num, letter in enumerate('ABCDEFGHIJKLMNOPQRSTUVWXYZ', start=1)}
    letter_part = ''.join([char for char in coordinate if not char.isdigit()])
    digit_part = int(''.join([char for char in coordinate if char.isdigit()]))
    return (letters_to_numbers[letter_part[0]], digit_part)

# store these stars in a dictionary where the key is their coordinates and the value is a tuple containing color and name.
star_data2 = {
  "AA19": {
    "color": "yellow",
    "starname": "Scorpii"
  },
  "B18": {
    "color": "crimson",
    "starname": "Lalande"
  },
  "E17": {
    "color": "yellow",
    "starname": "Ceti"
  },
  "H18": {
    "color": "crimson",
    "starname": "Mira"
  },
  "I16": {
    "color": "orange",
    "starname": "Rastaban"
  },
  "D13": {
    "color": "crimson",
    "starname": "Luyten"
  },
  "L18": {
    "color": "yellow",
    "starname": "Alcor"
  },
  "J15": {
    "color": "blue",
    "starname": "Pherda"
  },
  "H12": {
    "color": "lime",
    "starname": "Eridani"
  },
  "B11": {
    "color": "blue",
    "starname": "Sirius"
  },
  "F9": {
    "color": "yellow",
    "starname": "Diphda"
  },
  "E7": {
    "color": "crimson",
    "starname": "Kapetyn"
  },
  "D4": {
    "color": "orange",
    "starname": "Indi"
  },
  "G5": {
    "color": "yellow",
    "starname": "Canis"
  },
  "H2": {
    "color": "crimson",
    "starname": "Ophiuchi"
  },
  "I10": {
    "color": "crimson",
    "starname": "Ross"
  },
  "I8": {
    "color": "blue",
    "starname": "Deneb"
  },
  "L3": {
    "color": "crimson",
    "starname": "Cephei"
  },
  "L6": {
    "color": "lime",
    "starname": "Mirfak"
  },
  "L10": {
    "color": "orange",
    "starname": "Alphard"
  },
  "L13": {
    "color": "yellow",
    "starname": "Lyrae"
  },
  "P18": {
    "color": "orange",
    "starname": "Hydrae"
  },
  "Q20": {
    "color": "blue",
    "starname": "Zosca"
  },
  "O16": {
    "color": "lime",
    "starname": "Sadir"
  },
  "O13": {
    "color": "crimson",
    "starname": "Lacalle"
  },
  "N8": {
    "color": "yellow",
    "starname": "Capella"
  },
  "N6": {
    "color": "orange",
    "starname": "Kochab"
  },
  "O4": {
    "color": "yellow",
    "starname": "Schedar"
  },
  "Q2": {
    "color": "blue",
    "starname": "Mizar"
  },
  "R6": {
    "color": "lime",
    "starname": "Caph"
  },
  "Q8": {
    "color": "crimson",
    "starname": "Crucis"
  },
  "P10": {
    "color": "lime",
    "starname": "Canopus"
  },
  "Q11": {
    "color": "yellow",
    "starname": "Draconis"
  },
  "R14": {
    "color": "orange",
    "starname": "Lupi"
  },
  "T16": {
    "color": "yellow",
    "starname": "Aurigae"
  },
  "T12": {
    "color": "crimson",
    "starname": "Scheat"
  },
  "S10": {
    "color": "orange",
    "starname": "Almach"
  },
  "T4": {
    "color": "crimson",
    "starname": "Antares"
  },
  "V2": {
    "color": "yellow",
    "starname": "Tauri"
  },
  "U8": {
    "color": "yellow",
    "starname": "Spica"
  },
  "Y3": {
    "color": "crimson",
    "starname": "Wolf"
  },
  "X5": {
    "color": "orange",
    "starname": "Arcturus"
  },
  "X8": {
    "color": "blue",
    "starname": "Vega"
  },
  "W11": {
    "color": "crimson",
    "starname": "Mirach"
  },
  "W13": {
    "color": "yellow",
    "starname": "Cygni"
  },
  "V19": {
    "color": "lime",
    "starname": "Procyon"
  },
  "X16": {
    "color": "crimson",
    "starname": "Kruger"
  },
  "CC17": {
    "color": "crimson",
    "starname": "Barnard"
  },
  "Y14": {
    "color": "blue",
    "starname": "Altair"
  },
  "AA15": {
    "color": "orange",
    "starname": "Hamal"
  },
  "CC12": {
    "color": "yellow",
    "starname": "Dubhe"
  },
  "AA9": {
    "color": "lime",
    "starname": "Wezen"
  },
  "BB5": {
    "color": "yellow",
    "starname": "Bootis"
  },
  "EE10": {
    "color": "lime",
    "starname": "Polaris"
  }
}

star_data = {
    'AA19': ('yellow', 'Scorpii'), 'B18': ('crimson', 'Lalande'), 'E17': ('yellow', 'Ceti'), 
    'H18': ('crimson', 'Mira'), 'I16': ('orange', 'Rastaban'), 'D13': ('crimson', 'Luyten'), 
    'L18': ('yellow', 'Alcor'), 'J15': ('blue', 'Pherda'), 'H12': ('lime', 'Eridani'), 
    'B11': ('blue', 'Sirius'), 'F9': ('yellow', 'Diphda'), 'E7': ('crimson', 'Kapetyn'), 
    'D4': ('orange', 'Indi'), 'G5': ('yellow', 'Canis'), 'H2': ('crimson', 'Ophiuchi'), 
    'I10': ('crimson', 'Ross'), 'I8': ('blue', 'Deneb'), 'L3': ('crimson', 'Cephei'), 
    'L6': ('lime', 'Mirfak'), 'L10': ('orange', 'Alphard'), 'L13': ('yellow', 'Lyrae'), 
    'P18': ('orange', 'Hydrae'), 'Q20': ('blue', 'Zosca'), 'O16': ('lime', 'Sadir'),
    'O13': ('crimson', 'Lacalle'), 'N8': ('yellow', 'Capella'), 'N6': ('orange', 'Kochab'),
    'O4': ('yellow', 'Schedar'), 'Q2': ('blue', 'Mizar'), 'R6': ('lime', 'Caph'),
    'Q8': ('crimson', 'Crucis'), 'P10': ('lime', 'Canopus'), 'Q11': ('yellow', 'Draconis'),
    'R14': ('orange', 'Lupi'), 'T16': ('yellow', 'Aurigae'), 'T12': ('crimson', 'Scheat'),
    'S10': ('orange', 'Almach'), 'T4': ('crimson', 'Antares'),'V2': ('yellow', 'Tauri'),
    'U8': ('yellow', 'Spica'), 'Y3': ('crimson', 'Wolf'), 'X5': ('orange', 'Arcturus'),
    'X8': ('blue', 'Vega'), 'W11': ('crimson', 'Mirach'), 'W13': ('yellow', 'Cygni'),
    'V19': ('lime', 'Procyon'), 'X16': ('crimson', 'Kruger'), 'CC17': ('crimson', 'Barnard'),
    'Y14': ('blue', 'Altair'), 'AA15': ('orange', 'Hamal'), 'CC12': ('yellow', 'Dubhe'),
    'AA9': ('lime', 'Wezen'), 'BB5': ('yellow', 'Bootis'), 'EE10': ('lime', 'Polaris')
}

cloud_data = {'A10':'', 'A11':'', 'A12':'', 'A13':'','B10':'', 'B11':'', 'B12':'', 'C11':'', 'I7':'', 'I8':'', 'I13':'', 'I14':'', 'J6':'', 'J7':'', 'J8':'', 'J12':'', 'J13':'',
              'J14':'', 'K6':'', 'K7':'', 'K14':'', 'K15':'', 'K16':'', 'L5':'', 'L15':'', 'O1':'', 'O20':'', 'P1':'', 'P19':'', 'P20':'', 'Q1':'', 'Q2':'', 'Q20':'', 'R1':'', 'R2':'',
              'R19':'', 'U6':'', 'V5':'', 'V6':'', 'V14':'', 'V15':'', 'W6':'', 'W7':'', 'W15':'', 'X6':'', 'X7':'', 'X8':'', 'X13':'', 'X14':'', 'Y12':'', 'Y13':'', 'Y14':'',
              'DD7':'', 'EE8':'', 'EE9':'', 'EE11':'', 'FF8':'', 'FF9':'', 'FF10':'', 'FF11':''  }

# It's also good to have another dictionary for quick look-ups, where the key is the name of the star and the value is the tuple of the color and coordinates.
# a reverse dictionary for quick lookups
star_lookup= {v[1]:(k,v[0]) for k,v in star_data.items()}

def plot_hex_map(star_data):
    fig, ax = plt.subplots(figsize=(10, 10))
    ax.set_aspect('equal')
    ax.axis('off')
    num_columns = 32
    hex_radius = 0.5
    circle_radius = 0.2

    for col in range(num_columns):
        num_rows = 21 if col % 2 == 0 else 20
        for row in range(num_rows):
            x = col * hex_radius * 1.5
            y = row * hex_radius * np.sqrt(3) + (col % 2) * hex_radius * np.sqrt(3) / 2
            label = get_hex_label(col, row, num_rows)
            ax.text(x, y+.2, label, ha='center', va='bottom', fontsize=5, color='turquoise',)  #hex id

            coordinates = get_hex_label(col, row, num_rows)
            coordinates = coordinates.lstrip('0')
        # If the coordinate does not align with any star data, use the default map color
            if coordinates in cloud_data.keys():
                hex_coords = get_hex_vertices(x, y, hex_radius)
                hex_polygon = plt.Polygon(hex_coords, edgecolor='turquoise', facecolor='silver')
                ax.add_patch(hex_polygon)
                
            else:
                # If the coordinate does not align with any cloud data, use the default map color
                hex_coords = get_hex_vertices(x, y, hex_radius)
                hex_polygon = plt.Polygon(hex_coords, edgecolor='turquoise', facecolor='teal')
                ax.add_patch(hex_polygon)
                
            if coordinates in star_data.keys():
                star_color, star_name = star_data[coordinates]
                star_circle = plt.Circle((x,y), circle_radius, color = star_color)
                ax.add_patch(star_circle)
                ax.text(x, y+.45, star_name, ha='center', va='bottom', fontsize=6, color=star_color, weight="bold")
                #ax.text(x, y-.6, star_name, ha='center', va='top', rotation=180, fontsize=6, color=star_color, weight="bold") # for official reverse text
            
            
                
    x_min = -1 * hex_radius
    x_max = num_columns * hex_radius * 1.5 + hex_radius
    y_min = -1 * hex_radius
    y_max = num_rows * hex_radius * np.sqrt(3) + hex_radius * np.sqrt(3) / 2

    ax.set_xlim(x_min, x_max)
    ax.set_ylim(y_min, y_max)
    ax.set_aspect('equal')
    plt.savefig('starmap.svg', backend='svg', transparent=True)
    plt.show()