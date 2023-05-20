"""2D Helper functions and classes for FOV Visualization."""
from enum import Enum
from typing import Tuple


class QBits(Enum):
    """Number of Q bits used for quantized slopes and angle ranges."""

    Q64 = 1  # Least granular
    Q128 = 2
    Q256 = 3  # Most granular


class Octant(Enum):
    """Octant for use in FOV calcs. Octant 1 is ENE.  Count CCW."""

    O1 = 1
    O2 = 2
    O3 = 3
    O4 = 4
    O5 = 5
    O6 = 6
    O7 = 7
    O8 = 8

def cells_per_octant(fov: int) -> int:
    """Number of fov_cells in an octant for FOV purposes."""
    return sum(x for x in range(fov + 2))


def octant_transform(x: int, y: int, a: Octant, b: Octant) -> Tuple[int, int]:
    """transforms (x,y) coordinates from one Octant to another.

    This can also be used to tranform vectors, e.g. O1 (1, 0) to O2 (0, 1).
    """
    match a, b:
        # --- Octant 1 --- #
        case (Octant.O1, Octant.O1):
            return x, y
        case (Octant.O1, Octant.O2):
            return y, x
        case (Octant.O1, Octant.O3):
            return -y, x
        case (Octant.O1, Octant.O4):
            return -x, y
        case (Octant.O1, Octant.O5):
            return -x, -y
        case (Octant.O1, Octant.O6):
            return -y, -x
        case (Octant.O1, Octant.O7):
            return y, -x
        case (Octant.O1, Octant.O8):
            return x, -y
        # --- Octant 2 --- #
        case (Octant.O2, Octant.O1):
            return y, x
        case (Octant.O2, Octant.O2):
            return x, y
        case (Octant.O2, Octant.O3):
            return -x, y
        case (Octant.O2, Octant.O4):
            return -y, x
        case (Octant.O2, Octant.O5):
            return -y, -x
        case (Octant.O2, Octant.O6):
            return -x, -y
        case (Octant.O2, Octant.O7):
            return x, -y
        case (Octant.O2, Octant.O8):
            return y, -x
        # --- Octant 3 --- #
        case (Octant.O3, Octant.O3):
            return x, y
        case (Octant.O3, Octant.O4):
            return -y, -x
        case (Octant.O3, Octant.O5):
            return -y, x
        case (Octant.O3, Octant.O6):
            return x, -y
        case (Octant.O3, Octant.O7):
            return -x, -y
        case (Octant.O3, Octant.O8):
            return y, x
        case (Octant.O3, Octant.O1):
            return y, -x
        case (Octant.O3, Octant.O2):
            return -x, y
        # --- Octant 4 --- #
        case (Octant.O4, Octant.O4):
            return x, y
        case (Octant.O4, Octant.O5):
            return x, -y
        case (Octant.O4, Octant.O1):
            return -x, y
        case (Octant.O4, Octant.O8):
            return -x, -y
        case (Octant.O4, Octant.O6):
            return -y, x
        case (Octant.O4, Octant.O3):
            return -y, -x
        case (Octant.O4, Octant.O7):
            return y, x
        case (Octant.O4, Octant.O2):
            return y, -x
        # --- Octant 5 --- #
        case (Octant.O5, Octant.O5):
            return x, y
        case (Octant.O5, Octant.O4):
            return x, -y
        case (Octant.O5, Octant.O8):
            return -x, y
        case (Octant.O5, Octant.O1):
            return -x, -y
        case (Octant.O5, Octant.O7):
            return -y, x
        case (Octant.O5, Octant.O2):
            return -y, -x
        case (Octant.O5, Octant.O3):
            return y, -x
        case (Octant.O5, Octant.O6):
            return y, x
        # --- Octant 6 --- #
        case (Octant.O6, Octant.O6):
            return x, y
        case (Octant.O6, Octant.O3):
            return x, -y
        case (Octant.O6, Octant.O7):
            return -x, y
        case (Octant.O6, Octant.O2):
            return -x, -y
        case (Octant.O6, Octant.O8):
            return -y, x
        case (Octant.O6, Octant.O1):
            return -y, -x
        case (Octant.O6, Octant.O4):
            return y, -x
        case (Octant.O6, Octant.O5):
            return y, x
        # --- Octant 7 --- #
        case (Octant.O7, Octant.O7):
            return x, y
        case (Octant.O7, Octant.O2):
            return x, -y
        case (Octant.O7, Octant.O6):
            return -x, y
        case (Octant.O7, Octant.O3):
            return -x, -y
        case (Octant.O7, Octant.O1):
            return -y, x
        case (Octant.O7, Octant.O8):
            return -y, -x
        case (Octant.O7, Octant.O5):
            return y, -x
        case (Octant.O7, Octant.O4):
            return y, x
        # --- Octant 8 --- #
        case (Octant.O8, Octant.O8):
            return x, y
        case (Octant.O8, Octant.O1):
            return x, -y
        case (Octant.O8, Octant.O5):
            return -x, y
        case (Octant.O8, Octant.O4):
            return -x, -y
        case (Octant.O8, Octant.O2):
            return -y, x
        case (Octant.O8, Octant.O7):
            return -y, -x
        case (Octant.O8, Octant.O6):
            return y, -x
        case (Octant.O8, Octant.O3):
            return y, x

    raise ValueError("Improper Octant coordinates provided!")


def pri_sec_to_relative(pri: int, sec: int, octant: Octant) -> Tuple[int, int]:
    """transforms (pri,sec) values into relative (x,y) coordinates based on Octant."""
    match octant:
        case Octant.O1:
            return pri, sec
        case Octant.O2:
            return sec, pri
        case Octant.O3:
            return -sec, pri
        case Octant.O4:
            return -pri, sec
        case Octant.O5:
            return -pri, -sec
        case Octant.O6:
            return -sec, -pri
        case Octant.O7:
            return sec, -pri
        case Octant.O8:
            return pri, -sec

    raise ValueError("Improper pri/sec coordinates provided!")


def to_coords(tile_id: int, xdims: int) -> Tuple[int, int]:
    """Converts a 2D Tile ID to (x,y) coordinates based on X dimensions.

    Parameters
    ---
    `tile_id` : int
        encoded representation of the cell according to coordinates and map dimensions.
        The index of the tile within a tilemap.
    `xdims` : int
        amount by which y values are separated in the encoded structure.  Equal to the
        number of x dimensions in the map.
    """
    # Integer divide cell ID by y_shift to get y value
    y = tile_id // xdims
    # The remainder is the x value
    x = tile_id % xdims
    # Return the coordinates
    return x, y


def to_tile_id(x: int, y: int, xdims: int):
    """Takes 2D tile (x,y) coordinates and converts them into a tile ID.

    Parameters
    ---
    `x, y` : int
        (x,y) coordinates of the cell
    `xdims` : int
        shift value for y dimension.  Equal to number of x dimensions in the map
    """
    return x + y * xdims


#   ########  ########   ######   ########
#      ##     ##        ##           ##
#      ##     ######     ######      ##
#      ##     ##              ##     ##
#      ##     ########  #######      ##


def test_octant_transform():
    x1, y1 = 2, 1
    assert octant_transform(x1, y1, Octant.O1, Octant.O1) == (2, 1)
    assert octant_transform(x1, y1, Octant.O1, Octant.O2) == (1, 2)
    assert octant_transform(x1, y1, Octant.O1, Octant.O3) == (-1, 2)
    assert octant_transform(x1, y1, Octant.O1, Octant.O4) == (-2, 1)
    assert octant_transform(x1, y1, Octant.O1, Octant.O5) == (-2, -1)
    assert octant_transform(x1, y1, Octant.O1, Octant.O6) == (-1, -2)
    assert octant_transform(x1, y1, Octant.O1, Octant.O7) == (1, -2)
    assert octant_transform(x1, y1, Octant.O1, Octant.O8) == (2, -1)

    x2, y2 = 1, 2
    assert octant_transform(x2, y2, Octant.O2, Octant.O2) == (1, 2)
    assert octant_transform(x2, y2, Octant.O2, Octant.O3) == (-1, 2)
    assert octant_transform(x2, y2, Octant.O2, Octant.O4) == (-2, 1)
    assert octant_transform(x2, y2, Octant.O2, Octant.O5) == (-2, -1)
    assert octant_transform(x2, y2, Octant.O2, Octant.O6) == (-1, -2)
    assert octant_transform(x2, y2, Octant.O2, Octant.O7) == (1, -2)
    assert octant_transform(x2, y2, Octant.O2, Octant.O8) == (2, -1)
    assert octant_transform(x2, y2, Octant.O2, Octant.O1) == (2, 1)

    x3, y3 = -1, 2
    assert octant_transform(x3, y3, Octant.O3, Octant.O3) == (-1, 2)
    assert octant_transform(x3, y3, Octant.O3, Octant.O4) == (-2, 1)
    assert octant_transform(x3, y3, Octant.O3, Octant.O5) == (-2, -1)
    assert octant_transform(x3, y3, Octant.O3, Octant.O6) == (-1, -2)
    assert octant_transform(x3, y3, Octant.O3, Octant.O7) == (1, -2)
    assert octant_transform(x3, y3, Octant.O3, Octant.O8) == (2, -1)
    assert octant_transform(x3, y3, Octant.O3, Octant.O1) == (2, 1)
    assert octant_transform(x3, y3, Octant.O3, Octant.O2) == (1, 2)

    x4, y4 = -2, 1
    assert octant_transform(x4, y4, Octant.O4, Octant.O4) == (-2, 1)
    assert octant_transform(x4, y4, Octant.O4, Octant.O5) == (-2, -1)
    assert octant_transform(x4, y4, Octant.O4, Octant.O6) == (-1, -2)
    assert octant_transform(x4, y4, Octant.O4, Octant.O7) == (1, -2)
    assert octant_transform(x4, y4, Octant.O4, Octant.O8) == (2, -1)
    assert octant_transform(x4, y4, Octant.O4, Octant.O1) == (2, 1)
    assert octant_transform(x4, y4, Octant.O4, Octant.O2) == (1, 2)
    assert octant_transform(x4, y4, Octant.O4, Octant.O3) == (-1, 2)

    x5, y5 = -2, -1
    assert octant_transform(x5, y5, Octant.O5, Octant.O5) == (-2, -1)
    assert octant_transform(x5, y5, Octant.O5, Octant.O6) == (-1, -2)
    assert octant_transform(x5, y5, Octant.O5, Octant.O7) == (1, -2)
    assert octant_transform(x5, y5, Octant.O5, Octant.O8) == (2, -1)
    assert octant_transform(x5, y5, Octant.O5, Octant.O1) == (2, 1)
    assert octant_transform(x5, y5, Octant.O5, Octant.O2) == (1, 2)
    assert octant_transform(x5, y5, Octant.O5, Octant.O3) == (-1, 2)
    assert octant_transform(x5, y5, Octant.O5, Octant.O4) == (-2, 1)

    x6, y6 = -1, -2
    assert octant_transform(x6, y6, Octant.O6, Octant.O6) == (-1, -2)
    assert octant_transform(x6, y6, Octant.O6, Octant.O7) == (1, -2)
    assert octant_transform(x6, y6, Octant.O6, Octant.O8) == (2, -1)
    assert octant_transform(x6, y6, Octant.O6, Octant.O1) == (2, 1)
    assert octant_transform(x6, y6, Octant.O6, Octant.O2) == (1, 2)
    assert octant_transform(x6, y6, Octant.O6, Octant.O3) == (-1, 2)
    assert octant_transform(x6, y6, Octant.O6, Octant.O4) == (-2, 1)
    assert octant_transform(x6, y6, Octant.O6, Octant.O5) == (-2, -1)

    x7, y7 = 1, -2
    assert octant_transform(x7, y7, Octant.O7, Octant.O7) == (1, -2)
    assert octant_transform(x7, y7, Octant.O7, Octant.O8) == (2, -1)
    assert octant_transform(x7, y7, Octant.O7, Octant.O1) == (2, 1)
    assert octant_transform(x7, y7, Octant.O7, Octant.O2) == (1, 2)
    assert octant_transform(x7, y7, Octant.O7, Octant.O3) == (-1, 2)
    assert octant_transform(x7, y7, Octant.O7, Octant.O4) == (-2, 1)
    assert octant_transform(x7, y7, Octant.O7, Octant.O5) == (-2, -1)
    assert octant_transform(x7, y7, Octant.O7, Octant.O6) == (-1, -2)

    x8, y8 = 2, -1
    assert octant_transform(x8, y8, Octant.O8, Octant.O8) == (2, -1)
    assert octant_transform(x8, y8, Octant.O8, Octant.O1) == (2, 1)
    assert octant_transform(x8, y8, Octant.O8, Octant.O2) == (1, 2)
    assert octant_transform(x8, y8, Octant.O8, Octant.O3) == (-1, 2)
    assert octant_transform(x8, y8, Octant.O8, Octant.O4) == (-2, 1)
    assert octant_transform(x8, y8, Octant.O8, Octant.O5) == (-2, -1)
    assert octant_transform(x8, y8, Octant.O8, Octant.O6) == (-1, -2)
    assert octant_transform(x8, y8, Octant.O8, Octant.O7) == (1, -2)


def test_cell_per_octant():
    assert cells_per_octant(0) == 1
    assert cells_per_octant(1) == 3
    assert cells_per_octant(2) == 6
    assert cells_per_octant(3) == 10
    assert cells_per_octant(4) == 15
