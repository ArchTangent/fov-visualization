"""2D Helper functions and classes for FOV Visualization."""
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Self, Tuple

class Blockers:
    """FOV blocking data for TileMap construction."""

    def __init__(
        self,
        structure: int = 0,
        wall_n: int = 0,
        wall_w: int = 0,
    ) -> None:
        self.structure = structure
        self.wall_n = wall_n
        self.wall_w = wall_w
        

@dataclass
class Coords:
    """2D map integer coordinates."""

    __slots__ = "x", "y"

    def __init__(self, x: int, y: int) -> None:
        self.x = x
        self.y = y

    def __iter__(self):
        return iter((self.x, self.y))

    def __repr__(self) -> str:
        return f"{self.x, self.y}"

    def as_tuple(self):
        return (self.x, self.y)


class FovLineType(Enum):
    """Determines whether bresenham or bresenham_full line is chosen."""

    NORMAL = 1
    FULL = 2


class Line:
    """2D line segment."""

    __slots__ = "x1", "y1", "x2", "y2"

    def __init__(self, x1: int|float, y1: int|float, x2: int|float, y2: int|float) -> None:
        self.x1 = x1
        self.y1 = y1
        self.x2 = x2
        self.y2 = y2

    def __iter__(self):
        return iter((self.x1, self.y1, self.x2, self.y2))

    def __repr__(self) -> str:
        return f"Line {self.x1, self.y1, self.x2, self.y2}"

    def as_tuple(self):
        return (self.x1, self.y1, self.x2, self.y2)

    def intersects(self, other: Self) -> bool:
        """Returns `True` if this line intersects `other` line.

        Segment 1 is from (x1, y1) to (x2, y2), along `t`.
        Segment 2 is from (x3, y3) to (x4, y4), along `u`.
        """
        x1, y1, x2, y2 = self
        x3, y3, x4, y4 = other
        denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
        if denom == 0:
            return False

        # Intersection point must be along `t` and `u`
        t_num = (x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)
        if (t_num > 0 and t_num > denom) or (t_num < 0 and t_num < denom):
            return False

        u_num = (x1 - x3) * (y1 - y2) - (y1 - y3) * (x1 - x2)
        if (u_num > 0 and u_num > denom) or (u_num < 0 and u_num < denom):
            return False

        return True

    def intersection(self, other: Self):
        """Returns intersection point of self and `other` line, else `None`.

        Segment 1 is from (x1, y1) to (x2, y2), along `t`.
        Segment 2 is from (x3, y3) to (x4, y4), along `u`.
        """
        x1, y1, x2, y2 = self
        x3, y3, x4, y4 = other
        denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
        if denom == 0:
            return None

        # Intersection point must be along `t` and `u`
        t_num = (x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)
        if (t_num > 0 and t_num > denom) or (t_num < 0 and t_num < denom):
            return None

        u_num = (x1 - x3) * (y1 - y2) - (y1 - y3) * (x1 - x2)
        if (u_num > 0 and u_num > denom) or (u_num < 0 and u_num < denom):
            return None

        # Choose either `t` or `u` intersection point (`t` chosen)
        t = t_num / denom
        return (x1 + t * (x2 - x1), y1 + t * (y2 - y1))

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


class QBits(Enum):
    """Number of Q bits used for quantized slopes and angle ranges."""

    Q32 = 32  # Least granular
    Q64 = 64
    Q128 = 128 # Most granular
    

class VisibleTile:
    """Describes visible substructures inside a visible tile."""

    __slots__ = "tile", "structure", "wall_n", "wall_w"

    def __init__(self, tile: bool, structure: bool, wall_n: bool, wall_w: bool) -> None:
        self.tile = tile
        self.structure = structure
        self.wall_n = wall_n
        self.wall_w = wall_w

    def __repr__(self) -> str:
        return f"[VT] T: {self.tile}, S: {self.structure}, N: {self.wall_n}, W: {self.wall_w}"

    def update(self, other: Self):
        """Updates fields in `self` with those of `other`."""
        self.tile |= other.tile
        self.structure |= other.structure
        self.wall_n |= other.wall_n
        self.wall_w |= other.wall_w


#   ########  ##    ##  ##    ##   ######   ########  ########   ######   ##    ##
#   ##        ##    ##  ####  ##  ##    ##     ##        ##     ##    ##  ####  ##
#   ######    ##    ##  ## ## ##  ##           ##        ##     ##    ##  ## ## ##
#   ##        ##    ##  ##  ####  ##    ##     ##        ##     ##    ##  ##  ####
#   ##         ######   ##    ##   ######      ##     ########   ######   ##    ##

def boundary_radii(
    ox: int, oy: int, xdims: int, ydims: int, octant: Octant, radius: int
) -> Tuple[int, int]:
    """Get the maximum FOV radius to the primary and secondary boundary.

    Octants are counted from 1 to 8, starting ENE and counting up in CCW fashion.
    """
    match octant:
        case Octant.O1:
            return min(xdims - ox - 1, radius), min(ydims - oy - 1, radius)
        case Octant.O2:
            return min(ydims - oy - 1, radius), min(xdims - ox - 1, radius)
        case Octant.O3:
            return min(ydims - oy - 1, radius), min(ox, radius)
        case Octant.O4:
            return min(ox, radius), min(ydims - oy - 1, radius)
        case Octant.O5:
            return min(ox, radius), min(oy, radius)
        case Octant.O6:
            return min(oy, radius), min(ox, radius)
        case Octant.O7:
            return min(oy, radius), min(xdims - ox - 1, radius)
        case Octant.O8:
            return min(xdims - ox - 1, radius), min(oy, radius)
        

def cells_per_octant(fov: int) -> int:
    """Number of fov_cells in an octant for FOV purposes."""
    return sum(x for x in range(fov + 2))


def line_line_intersection(
    line1: Line, line2: Line
) -> Optional[Tuple[float, float]]:
    """Returns intersection point of line segments 1 and 2, else `None`.

    Segment 1 is from (x1, y1) to (x2, y2), along `t`.
    Segment 2 is from (x3, y3) to (x4, y4), along `u`.
    """
    x1, y1, x2, y2 = line1
    x3, y3, x4, y4 = line2
    denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    if denom == 0:
        return None

    # Intersection point must be along `t` and `u`
    t_num = (x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)
    if (t_num > 0 and t_num > denom) or (t_num < 0 and t_num < denom):
        return None

    u_num = (x1 - x3) * (y1 - y2) - (y1 - y3) * (x1 - x2)
    if (u_num > 0 and u_num > denom) or (u_num < 0 and u_num < denom):
        return None

    # Choose either `t` or `u` intersection point (`t` chosen)
    t = t_num / denom
    return (x1 + t * (x2 - x1), y1 + t * (y2 - y1))


def max_fovtile_index(radius: int) -> int:
    """Returns maximum FOV Octant index for given radius.

    Assumes that TID 0 (index 0) is always visible and that FovTile iteration
    in earnest starts from TID 1 (index 1)
    """
    return sum(n + 1 for n in range(1, radius + 1))


def octant_transform_flt(
    x: float, y: float, a: Octant, b: Octant
) -> Tuple[float, float]:
    """transforms (x,y) coordinates from Octant `a` to `b`.

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


def octant_transform(x: int, y: int, a: Octant, b: Octant) -> Tuple[int, int]:
    """transforms (x,y) coordinates from from Octant `a` to `b`.

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
        (x,y) coordinates of the tile.
    `xdims` : int
        number of x dimensions.
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
