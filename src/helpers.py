"""2D Helper functions and classes for FOV Visualization."""
import math
import pytest
from enum import Enum
from typing import List, Optional, Self, Tuple


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


class Line:
    """2D line segment."""

    __slots__ = "x1", "y1", "x2", "y2"

    def __init__(
        self, x1: int | float, y1: int | float, x2: int | float, y2: int | float
    ) -> None:
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

    def to_dict(self):
        """Converts `Line` to dictionary for serialization."""
        return {
            "x1": self.x1,
            "y1": self.y1,
            "x2": self.x1,
            "y2": self.y2,
        }

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


class Point:
    """2D map floating point coordinates."""

    __slots__ = "x", "y"

    def __init__(self, x: float, y: float) -> None:
        self.x = x
        self.y = y

    def __iter__(self):
        return iter((self.x, self.y))

    def __repr__(self) -> str:
        return f"P{self.x, self.y}"

    def as_tuple(self):
        return (self.x, self.y)

    def distance(self, other: Self) -> float:
        """Returns distance between self and other."""
        dx_abs = (other.x - self.x) ** 2
        dy_abs = (other.y - self.y) ** 2

        return math.sqrt(dx_abs + dy_abs)

    def rounded(self) -> Self:
        return Point(round(self.x, 3), round(self.y, 3))


class Cmp(Enum):
    """Used for greater than, less than, or equal to in match statements."""

    GT = 1
    LT = 2
    ET = 3


class QBits(Enum):
    """Number of Q bits used for quantized slopes and angle ranges."""

    Q32 = 32  # Least granular
    Q64 = 64
    Q128 = 128  # Most granular


class Octant(Enum):
    """Octant for use in 2D FOV calcs. Octant 1 is ENE.  Count CCW."""

    O1 = 1
    O2 = 2
    O3 = 3
    O4 = 4
    O5 = 5
    O6 = 6
    O7 = 7
    O8 = 8


class Direction(Enum):
    """Eight-way directions for LOS/LOF purposes."""

    N = 1
    S = 2
    E = 4
    W = 8
    NE = 5
    SE = 6
    SW = 10
    NW = 9


class FovLineType(Enum):
    """Determines whether bresenham or bresenham_full line is chosen."""

    NORMAL = 1
    FULL = 2


class Rect:
    """2D axis-aligned rectangle defined by reference point p0, width, and height.

    Reference point is toward the origin (0,0) - width and height are added to it.

    Sides:
    - `p0` to `p1`: width   (s1)
    - `p0` to `p2`: height  (s2)
    - `p2` to `p3`: width   (s3)
    - `p1` to `p3`: height  (s4)
    """

    __slots__ = "left", "right", "bottom", "top"

    def __init__(self, x: int, y: int, width: int, height: int) -> None:
        self.left = x
        self.right = x + width
        self.bottom = y
        self.top = y + height

    def __repr__(self) -> str:
        return f"Rect {self.left, self.bottom}, {self.right, self.bottom}, {self.left, self.top}, {self.right, self.top}"

    def as_tuple(self):
        return (
            (self.left, self.bottom),
            (self.right, self.bottom),
            (self.left, self.top),
            (self.right, self.top),
        )

    def closest_vertex(self, x: int, y: int) -> Tuple[int, int]:
        """Returns closest rectangle vertex to point (x,y)."""
        dleft, dright = (self.left - x) ** 2, (self.right - x) ** 2
        dbottom, dtop = (self.bottom - y) ** 2, (self.top - y) ** 2

        d0 = dleft + dbottom
        d1 = dright + dbottom
        d2 = dleft + dtop
        d3 = dright + dtop

        lowest = d0
        low_pt = self.left, self.bottom

        if d1 < lowest:
            lowest = d1
            low_pt = self.right, self.bottom

        if d2 < lowest:
            lowest = d2
            low_pt = self.left, self.top

        if d3 < lowest:
            low_pt = self.right, self.top

        return low_pt

    def left_side(self) -> Tuple[int, int, int, int]:
        """Returns left side (x closest to origin) as a (x1, y1, x2, y2) line."""
        return (self.left, self.bottom, self.left, self.top)  # s2

    def right_side(self) -> Tuple[int, int, int, int]:
        """Returns right side (x furthest from origin) as a (x1, y1, x2, y2) line."""
        return (self.right, self.bottom, self.right, self.top)  # s4

    def top_side(self) -> Tuple[int, int, int, int]:
        """Returns top side (y furthest from origin) as a (x1, y1, x2, y2) line."""
        return (self.left, self.top, self.right, self.top)  # s3

    def bottom_side(self) -> Tuple[int, int, int, int]:
        """Returns bottom side (y closest to origin) as a (x1, y1, x2, y2) line."""
        return (self.left, self.bottom, self.right, self.bottom)  # s1

    def lines(self) -> List[Tuple[int, int, int, int]]:
        """Returns list of (x1, y1, x2, y2) lines comprising the rectangle."""
        return [
            (self.left, self.bottom, self.right, self.bottom),  # s1
            (self.left, self.bottom, self.left, self.top),  # s2
            (self.left, self.top, self.right, self.top),  # s3
            (self.right, self.bottom, self.right, self.top),  # s4
        ]


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


def cmp(a: int | float, b: int | float) -> Cmp:
    """Compares two numbers and returns `Cmp` enum."""
    if a < b:
        return Cmp.LT
    elif a > b:
        return Cmp.GT
    else:
        return Cmp.ET


def max_fovtile_index(radius: int) -> int:
    """Returns maximum FOV Octant index for given radius.

    Assumes that TID 0 (index 0) is always visible and that FovTile iteration
    in earnest starts from TID 1 (index 1)
    """
    return sum(n + 1 for n in range(1, radius + 1))


def line_line_intersection(line1: Line, line2: Line) -> Optional[Tuple[float, float]]:
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


def slope_q16(numer: float, denom: float) -> int:
    """Creates a Q16 quantized i16 slope value, accurate to the 1000ths place.

    Allows for slopes from -32.768 to +32.767.  Max z_levels allowed: 32.

    Account for zero denominator:
    - fully up: i16.max -> +32767 (+32.767)
    - fully down: i16.min -> -32768 (-32.768)
    """
    if denom == 0:
        return 32767 if numer >= 0 else -32768
    else:
        return int(numer / denom * 1000)


def slope_q16u(n: float, d: float, slope_min: float, slope_max: float) -> int:
    """Creates a Q16 quantized u16 slope value using interpolation.

    Defined values range from (u16.min + 1) to (u16.max - 1): 1 to 65534.
    Values are shifted by slope_min to normalize the range.

    Undefined values (zero denominator) are handled as follows:
      (-) numerator: u16.min -> 0
      (+) numerator: u16.max -> 65535

    Where:
    - slope_range: max_slope - min_slope possible (for dsec/dpri, this is 5.0)
    - value_range: range of the integer used. For u16, 65534.
    """
    slope_range = slope_max - slope_min

    if d != 0:
        slope = n / d

        if slope < slope_min:
            raise Exception(f"slope of {slope} is < minimum of {slope_min}")
        if slope > slope_max:
            raise Exception(f"slope of {slope} is > minimum of {slope_max}")

        return int((slope - slope_min) / slope_range * 65534)
    else:
        return 65535 if n >= 0 else 0


def slope_q8u(n: float, d: float, slope_min: float, slope_max: float) -> int:
    """Creates a Q8 quantized u8 slope value using interpolation.

    Defined values range from (u8.min + 1) to (u8.max - 1): 1 to 254.
    Values are shifted by slope_min to normalize the range.

    Undefined values (zero denominator) are handled as follows:
      (-) numerator: u8.min -> 0
      (+) numerator: u8.max -> 255

    Where:
    - slope_range: max_slope - min_slope possible (for dsec/dpri, this is 5.0)
    - value_range: range of the integer used. For u8, 254.
    """
    slope_range = slope_max - slope_min

    if d != 0:
        slope = n / d

        if slope < slope_min:
            raise Exception(f"slope of {slope} is < minimum of {slope_min}")
        if slope > slope_max:
            raise Exception(f"slope of {slope} is > minimum of {slope_max}")

        return int((slope - slope_min) / slope_range * 254)
    else:
        return 255 if n >= 0 else 0


def cells_per_octet(fov: int) -> int:
    """Number of fov_cells in an octant for FOV purposes."""
    return sum(x for x in range(fov + 2))


def octet_sublice_ixs(fov: int, dx: int, dy: int, z_lvl: int) -> Tuple[int, int]:
    """Gets (inclusive) start and end index for a sublice into a list of FovCells.

    If there are 4 in-game dz levels and 50 FOV:
    - there are 4 * 1326 = 5304 FOV fov_cells in that octant
    - z0 runs from

    Octets can be truncated by the min(max(dx, dy), fov)
    - If dx is 5, y is 7, and FOV is 50:
        - end index is: min(max(5, 7), 50) = cells_per_octet(7) = start_ix + 36

    Starting index is always 0, "inclusive" means the ending index must be included.

    `dx`: x distance to map edge
    `dy`: y distance to map edge
    """
    cells_per_z_lvl = cells_per_octet(fov)
    ix_shift = min(max(dx, dy), cells_per_z_lvl)
    start_ix = z_lvl * cells_per_z_lvl
    end_ix = start_ix + ix_shift

    return start_ix, end_ix


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


def to_coords(tile_id: int, xdims: int) -> Tuple[int, int]:
    """Converts a 2D Tile ID to (x,y) coordinates based on X dimensions.

    Parameters
    ---
    `tile_id` : int
        encoded representation of the cell according to coordinates and map dimensions.
        The index of the tile within a tilemap.
    `xdims` : int
        number of x dimensions.
    """
    # Integer divide cell ID by y_shift to get y value
    y = tile_id // xdims
    # The remainder is the x value
    x = tile_id % xdims
    # Return the coordinates
    return x, y


def tryout_indexes(fov: int, dx: int, dy: int, z_lvls: int):
    """Test function to get all indexes in dx, dy, dz range."""
    print(f"\n----- FOV {fov}, dx {dx}, dy {dy} -----")
    _dx = min(dx, fov) + 1
    _dy = min(dy, fov) + 1

    cid = 0
    for z in range(z_lvls):
        for x in range(_dx):
            for y in range(min(x + 1, _dy)):
                print(f"Cell {cid} ({x}, {y}, {z})")
                cid += 1


#   ########  ########   ######   ########
#      ##     ##        ##           ##
#      ##     ######     ######      ##
#      ##     ##              ##     ##
#      ##     ########  #######      ##


def test_octant_transform():
    x1, y1 = 2, 1
    assert octant_transform_flt(x1, y1, Octant.O1, Octant.O1) == (2, 1)
    assert octant_transform_flt(x1, y1, Octant.O1, Octant.O2) == (1, 2)
    assert octant_transform_flt(x1, y1, Octant.O1, Octant.O3) == (-1, 2)
    assert octant_transform_flt(x1, y1, Octant.O1, Octant.O4) == (-2, 1)
    assert octant_transform_flt(x1, y1, Octant.O1, Octant.O5) == (-2, -1)
    assert octant_transform_flt(x1, y1, Octant.O1, Octant.O6) == (-1, -2)
    assert octant_transform_flt(x1, y1, Octant.O1, Octant.O7) == (1, -2)
    assert octant_transform_flt(x1, y1, Octant.O1, Octant.O8) == (2, -1)

    x2, y2 = 1, 2
    assert octant_transform_flt(x2, y2, Octant.O2, Octant.O2) == (1, 2)
    assert octant_transform_flt(x2, y2, Octant.O2, Octant.O3) == (-1, 2)
    assert octant_transform_flt(x2, y2, Octant.O2, Octant.O4) == (-2, 1)
    assert octant_transform_flt(x2, y2, Octant.O2, Octant.O5) == (-2, -1)
    assert octant_transform_flt(x2, y2, Octant.O2, Octant.O6) == (-1, -2)
    assert octant_transform_flt(x2, y2, Octant.O2, Octant.O7) == (1, -2)
    assert octant_transform_flt(x2, y2, Octant.O2, Octant.O8) == (2, -1)
    assert octant_transform_flt(x2, y2, Octant.O2, Octant.O1) == (2, 1)

    x3, y3 = -1, 2
    assert octant_transform_flt(x3, y3, Octant.O3, Octant.O3) == (-1, 2)
    assert octant_transform_flt(x3, y3, Octant.O3, Octant.O4) == (-2, 1)
    assert octant_transform_flt(x3, y3, Octant.O3, Octant.O5) == (-2, -1)
    assert octant_transform_flt(x3, y3, Octant.O3, Octant.O6) == (-1, -2)
    assert octant_transform_flt(x3, y3, Octant.O3, Octant.O7) == (1, -2)
    assert octant_transform_flt(x3, y3, Octant.O3, Octant.O8) == (2, -1)
    assert octant_transform_flt(x3, y3, Octant.O3, Octant.O1) == (2, 1)
    assert octant_transform_flt(x3, y3, Octant.O3, Octant.O2) == (1, 2)

    x4, y4 = -2, 1
    assert octant_transform_flt(x4, y4, Octant.O4, Octant.O4) == (-2, 1)
    assert octant_transform_flt(x4, y4, Octant.O4, Octant.O5) == (-2, -1)
    assert octant_transform_flt(x4, y4, Octant.O4, Octant.O6) == (-1, -2)
    assert octant_transform_flt(x4, y4, Octant.O4, Octant.O7) == (1, -2)
    assert octant_transform_flt(x4, y4, Octant.O4, Octant.O8) == (2, -1)
    assert octant_transform_flt(x4, y4, Octant.O4, Octant.O1) == (2, 1)
    assert octant_transform_flt(x4, y4, Octant.O4, Octant.O2) == (1, 2)
    assert octant_transform_flt(x4, y4, Octant.O4, Octant.O3) == (-1, 2)

    x5, y5 = -2, -1
    assert octant_transform_flt(x5, y5, Octant.O5, Octant.O5) == (-2, -1)
    assert octant_transform_flt(x5, y5, Octant.O5, Octant.O6) == (-1, -2)
    assert octant_transform_flt(x5, y5, Octant.O5, Octant.O7) == (1, -2)
    assert octant_transform_flt(x5, y5, Octant.O5, Octant.O8) == (2, -1)
    assert octant_transform_flt(x5, y5, Octant.O5, Octant.O1) == (2, 1)
    assert octant_transform_flt(x5, y5, Octant.O5, Octant.O2) == (1, 2)
    assert octant_transform_flt(x5, y5, Octant.O5, Octant.O3) == (-1, 2)
    assert octant_transform_flt(x5, y5, Octant.O5, Octant.O4) == (-2, 1)

    x6, y6 = -1, -2
    assert octant_transform_flt(x6, y6, Octant.O6, Octant.O6) == (-1, -2)
    assert octant_transform_flt(x6, y6, Octant.O6, Octant.O7) == (1, -2)
    assert octant_transform_flt(x6, y6, Octant.O6, Octant.O8) == (2, -1)
    assert octant_transform_flt(x6, y6, Octant.O6, Octant.O1) == (2, 1)
    assert octant_transform_flt(x6, y6, Octant.O6, Octant.O2) == (1, 2)
    assert octant_transform_flt(x6, y6, Octant.O6, Octant.O3) == (-1, 2)
    assert octant_transform_flt(x6, y6, Octant.O6, Octant.O4) == (-2, 1)
    assert octant_transform_flt(x6, y6, Octant.O6, Octant.O5) == (-2, -1)

    x7, y7 = 1, -2
    assert octant_transform_flt(x7, y7, Octant.O7, Octant.O7) == (1, -2)
    assert octant_transform_flt(x7, y7, Octant.O7, Octant.O8) == (2, -1)
    assert octant_transform_flt(x7, y7, Octant.O7, Octant.O1) == (2, 1)
    assert octant_transform_flt(x7, y7, Octant.O7, Octant.O2) == (1, 2)
    assert octant_transform_flt(x7, y7, Octant.O7, Octant.O3) == (-1, 2)
    assert octant_transform_flt(x7, y7, Octant.O7, Octant.O4) == (-2, 1)
    assert octant_transform_flt(x7, y7, Octant.O7, Octant.O5) == (-2, -1)
    assert octant_transform_flt(x7, y7, Octant.O7, Octant.O6) == (-1, -2)

    x8, y8 = 2, -1
    assert octant_transform_flt(x8, y8, Octant.O8, Octant.O8) == (2, -1)
    assert octant_transform_flt(x8, y8, Octant.O8, Octant.O1) == (2, 1)
    assert octant_transform_flt(x8, y8, Octant.O8, Octant.O2) == (1, 2)
    assert octant_transform_flt(x8, y8, Octant.O8, Octant.O3) == (-1, 2)
    assert octant_transform_flt(x8, y8, Octant.O8, Octant.O4) == (-2, 1)
    assert octant_transform_flt(x8, y8, Octant.O8, Octant.O5) == (-2, -1)
    assert octant_transform_flt(x8, y8, Octant.O8, Octant.O6) == (-1, -2)
    assert octant_transform_flt(x8, y8, Octant.O8, Octant.O7) == (1, -2)


def test_octant_sublice_ixs():
    assert octet_sublice_ixs(3, 2, 1, 0) == (0, 2)
    assert octet_sublice_ixs(3, 2, 1, 1) == (10, 12)
    assert octet_sublice_ixs(3, 2, 1, 2) == (20, 22)
    assert octet_sublice_ixs(3, 2, 1, 3) == (30, 32)


def test_cell_per_octant():
    assert cells_per_octet(0) == 1
    assert cells_per_octet(1) == 3
    assert cells_per_octet(2) == 6
    assert cells_per_octet(3) == 10
    assert cells_per_octet(4) == 15


def test_slope_q16():
    # Min and Max (where denominator is 0)
    assert slope_q16(1, 0) == 32767
    assert slope_q16(-1, 0) == -32768
    # Normal Slopes
    assert slope_q16(3, 2) == 1500
    assert slope_q16(-3, 2) == -1500
    assert slope_q16(1, 3) == 333
    assert slope_q16(-1, 3) == -333
    assert slope_q16(50, 2) == 25000
    assert slope_q16(-50, 2) == -25000


def test_slope_q16u():
    # Defined values
    assert slope_q16u(-1, 1, -1.0, 4.0) == 0
    assert slope_q16u(0, 1, -1.0, 4.0) == 13106
    assert slope_q16u(1, 1, -1.0, 4.0) == 26213
    assert slope_q16u(2, 1, -1.0, 4.0) == 39320
    assert slope_q16u(3, 1, -1.0, 4.0) == 52427
    assert slope_q16u(4, 1, -1.0, 4.0) == 65534
    # Undefined values
    assert slope_q16u(-1, 0, -1.0, 4.0) == 0
    assert slope_q16u(1, 0, -1.0, 4.0) == 65535
    # Out of bounds values
    with pytest.raises(Exception) as _err_info:
        slope_q16u(-2, 1, -1.0, 4.0)
        slope_q16u(5, 1, -1.0, 4.0)


def test_slope_q8u():
    # Defined values
    assert slope_q8u(-1, 1, -1.0, 4.0) == 0
    assert slope_q8u(0, 1, -1.0, 4.0) == 50
    assert slope_q8u(1, 1, -1.0, 4.0) == 101
    assert slope_q8u(2, 1, -1.0, 4.0) == 152
    assert slope_q8u(3, 1, -1.0, 4.0) == 203
    assert slope_q8u(4, 1, -1.0, 4.0) == 254
    # Undefined values
    assert slope_q8u(-1, 0, -1.0, 4.0) == 0
    assert slope_q8u(1, 0, -1.0, 4.0) == 255
    # Out of bounds values
    with pytest.raises(Exception) as _err_info:
        slope_q8u(-2, 1, -1.0, 4.0)
        slope_q8u(5, 1, -1.0, 4.0)


if __name__ == "__main__":
    print(octet_sublice_ixs(3, 2, 1, 0))
    print(octet_sublice_ixs(3, 2, 1, 1))
    print(octet_sublice_ixs(3, 2, 1, 2))
    print(octet_sublice_ixs(3, 2, 1, 3))

    tryout_indexes(5, 3, 2, 1)
    tryout_indexes(2, 2, 2, 1)

    print("--- Cells per Octet ---")
    for fov_radius in (10, 20, 30, 40, 50):
        print(cells_per_octet(fov_radius))
