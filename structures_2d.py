# Structures for 2D FOV

from enum import Enum

class Structure(Enum):
    """2D tilemap structure that blocks sight and/or movement.
    
    Structures are placed in the *center* of the tile, unlike Walls, which
    are on the tile edges.
    """
    ERROR = -1  # Invalid structure type
    NONE = 0    # No structure
    FULL = 1    # Fills entire tile in x, y, and z directions
    WIDE = 2    # Fills tile halfway along x, y; fully in z
    THIN = 3    # Fills tile 1/4 of the way along x, y; fully in z

    @staticmethod
    def from_str(name: str):
        """Creates an instance from a (JSON, YAML, TOML) string."""
        match name.upper():
            case "NONE":
                return Structure.NONE
            case "FULL":
                return Structure.FULL
            case "WIDE":
                return Structure.WIDE
            case "THIN":
                return Structure.THIN
            case _:
                print(f"Invalid Structure name `{name}`!")
                return Structure.ERROR


class Wall(Enum):
    """2D tilemap structure that blocks sight and/or movement along edges.
    
    Walls are placed on the *edges* of a tile.
    """
    ERROR = -1  # Invalid wall type
    NONE = 0    # No wall
    FULL = 1    # Full 
    HALF = 2    # Half height wall along a given edge
    WINDOW = 3  # Allows sight, but blocks movement along a given edge

    @staticmethod
    def from_str(name: str):
        """Creates an instance from a (JSON, YAML, TOML) string."""
        match name.upper():
            case "NONE":
                return Wall.NONE
            case "FULL":
                return Wall.FULL
            case "HALF":
                return Wall.HALF
            case "WINDOW":
                return Wall.WINDOW
            case _:
                print(f"Invalid Wall name `{name}`!")
                return Wall.ERROR 


def test_structure_str():
    suite = [
        ("none", Structure.NONE),
        ("NONE", Structure.NONE),
        ("full", Structure.FULL),
        ("FULL", Structure.FULL),
        ("wide", Structure.WIDE),
        ("WIDE", Structure.WIDE),
        ("thin", Structure.THIN),
        ("THIN", Structure.THIN),
        ("abcd", Structure.ERROR),
        ("WXYZ", Structure.ERROR),
    ]
    for input, expected in suite:
        actual = Structure.from_str(input)
        assert actual == expected

def test_wall_str():
    suite = [
        ("none", Wall.NONE),
        ("NONE", Wall.NONE),
        ("full", Wall.FULL),
        ("FULL", Wall.FULL),
        ("half", Wall.HALF),
        ("HALF", Wall.HALF),
        ("window", Wall.WINDOW),
        ("WINDOW", Wall.WINDOW),
        ("efgh", Wall.ERROR),
        ("STUV", Wall.ERROR),
    ]
    for input, expected in suite:
        actual = Wall.from_str(input)
        assert actual == expected
