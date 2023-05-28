"""Helper classes and functions for 3D FOV Visualization."""
# TODO: test Z-primary functions
# TODO: test different eye levels for DZDP functions (for X and Y axis)

from dataclasses import dataclass
from enum import Enum
from typing import Tuple

#    ######   ##           ##      ######    ######   ########   ######
#   ##    ##  ##         ##  ##   ##        ##        ##        ##
#   ##        ##        ##    ##   ######    ######   ######     ######
#   ##    ##  ##        ########        ##        ##  ##              ##
#    ######   ########  ##    ##  #######   #######   ########  #######


@dataclass
class Coords:
    """3D map coordinates."""

    __slots__ = "x", "y", "z"

    def __init__(self, x: int, y: int, z: int) -> None:
        self.x = x
        self.y = y
        self.z = z

    def __iter__(self):
        return iter((self.x, self.y, self.z))

    def __repr__(self) -> str:
        return f"{self.x, self.y, self.z}"

    def as_tuple(self):
        return (self.x, self.y, self.z)


class Octant(Enum):
    """Octants for use in 3D FOV. Octant 1 is (+++)."""

    O1 = 1
    O2 = 2
    O3 = 3
    O4 = 4
    O5 = 5
    O6 = 6
    O7 = 7
    O8 = 8

    def __iter__(self):
        return iter(
            (self.O1, self.O2, self.O3, self.O4, self.O5, self.O6, self.O7, self.O8)
        )


class Axis(Enum):
    """Primary axes for 3D FOV."""

    X = 1
    Y = 2
    Z = 4

    def __iter__(self):
        return iter((self.X, self.Y, self.Z))


class QBits(Enum):
    """Number of Q bits used for quantized slopes and angle ranges."""

    Q64 = 1  # Least granular
    Q128 = 2
    Q256 = 3  # Most granular


#   ########  ##    ##  ##    ##   ######   ########  ########   ######   ##    ##
#   ##        ##    ##  ####  ##  ##    ##     ##        ##     ##    ##  ####  ##
#   ######    ##    ##  ## ## ##  ##           ##        ##     ##    ##  ## ## ##
#   ##        ##    ##  ##  ####  ##    ##     ##        ##     ##    ##  ##  ####
#   ##         ######   ##    ##   ######      ##     ########   ######   ##    ##


def clamp(value: float, min_value: float, max_value: float) -> float:
    """Clamps floating point value between min and max."""
    if min_value > max_value:
        raise ValueError("minimum value cannot be larger than maximum!")

    return max(min(value, max_value), min_value)


def octant_coords_to_relative(
    dpri: int, dsec: int, dz: int, octant: Octant, axis: Axis
) -> Coords:
    """Converts coordinates from FovCell's Octant form to relative CellMap form.

    Note: if Z is the primary axis, X and Y will always be dpri and dsec, respectively.
    """
    match octant:
        case Octant.O1:
            rz = dz
            match axis:
                case Axis.X | Axis.Z:
                    rx, ry = dpri, dsec
                case _:
                    rx, ry = dsec, dpri
        case Octant.O2:
            rz = dz
            match axis:
                case Axis.X | Axis.Z:
                    rx, ry = -dpri, dsec
                case _:
                    rx, ry = -dsec, dpri
        case Octant.O3:
            rz = dz
            match axis:
                case Axis.X | Axis.Z:
                    rx, ry = -dpri, -dsec
                case _:
                    rx, ry = -dsec, -dpri
        case Octant.O4:
            rz = dz
            match axis:
                case Axis.X | Axis.Z:
                    rx, ry = dpri, -dsec
                case _:
                    rx, ry = dsec, -dpri
        case Octant.O5:
            rz = -dz
            match axis:
                case Axis.X | Axis.Z:
                    rx, ry = dpri, dsec
                case _:
                    rx, ry = dsec, dpri
        case Octant.O6:
            rz = -dz
            match axis:
                case Axis.X | Axis.Z:
                    rx, ry = -dpri, dsec
                case _:
                    rx, ry = -dsec, dpri
        case Octant.O7:
            rz = -dz
            match axis:
                case Axis.X | Axis.Z:
                    rx, ry = -dpri, -dsec
                case _:
                    rx, ry = -dsec, -dpri
        case Octant.O8:
            rz = -dz
            match axis:
                case Axis.X | Axis.Z:
                    rx, ry = dpri, -dsec
                case _:
                    rx, ry = dsec, -dpri

    return Coords(rx, ry, rz)


def to_cell_id(x: int, y: int, z: int, xdims: int, ydims: int):
    """
    Takes 3D cell (x,y,z) coordinates and converts them into a cell ID.

    Where:
        - cell_id = x * x_shift + y * y_shift + z * z_shift
        - x_shift = 1
        - y_shift = x_dims
        - z_shift = y_dims * x_dims

    Parameters
    ----------
    x, y, z : int
        (x,y,z) coordinates of the cell.
    `xdims` : int
        number of x dimensions.
    `ydims` : int
        number of y dimensions.
    """
    y_shift = xdims
    z_shift = ydims * xdims

    return x + y * y_shift + z * z_shift


#    ######   ##         ######   #######   ########
#   ##        ##        ##    ##  ##    ##  ##
#    ######   ##        ##    ##  #######   ######
#         ##  ##        ##    ##  ##        ##
#   #######   ########   ######   ##        ########


def dsdp_slopes_cell(dpri: int, dsec: int) -> Tuple[float, float]:
    """Gets `dsec/dpri` slope range to entire cell range for all Octants.

    This covers both structure and floor ranges.
    """
    if dpri == 0:
        return (0.0, 1.0)
    if dsec == 0:
        s1 = clamp((dsec - 0.5) / (dpri - 0.5), 0.0, 1.0)
        s2 = clamp((dsec + 0.5) / (dpri - 0.5), 0.0, 1.0)
    else:
        s1 = clamp((dsec - 0.5) / (dpri + 0.5), 0.0, 1.0)
        s2 = clamp((dsec + 0.5) / (dpri - 0.5), 0.0, 1.0)

    return min(s1, s2), max(s1, s2)


def dsdp_slopes_north(
    dpri: int, dsec: int, octant: Octant, axis: Axis
) -> Tuple[float, float]:
    """Gets `dsec/dpri` slope range to cell's North side based on Octant."""
    match axis:
        case Axis.X:
            match octant:
                case Octant.O1 | Octant.O2 | Octant.O5 | Octant.O6:
                    if dpri == 0:
                        return (0.0, 0.0)
                    s1 = clamp((dsec - 0.5) / (dpri + 0.5), 0.0, 1.0)
                    s2 = clamp((dsec - 0.5) / (dpri - 0.5), 0.0, 1.0)
                case Octant.O3 | Octant.O4 | Octant.O7 | Octant.O8:
                    if dpri == 0:
                        return (1.0, 1.0)
                    s1 = clamp((dsec + 0.5) / (dpri + 0.5), 0.0, 1.0)
                    s2 = clamp((dsec + 0.5) / (dpri - 0.5), 0.0, 1.0)
        case Axis.Y:
            match octant:
                case Octant.O1 | Octant.O2 | Octant.O5 | Octant.O6:
                    if dpri == 0:
                        return (0.0, 0.0)
                    s1 = clamp((dsec - 0.5) / (dpri - 0.5), 0.0, 1.0)
                    s2 = clamp((dsec + 0.5) / (dpri - 0.5), 0.0, 1.0)
                case Octant.O3 | Octant.O4 | Octant.O7 | Octant.O8:
                    s1 = clamp((dsec - 0.5) / (dpri + 0.5), 0.0, 1.0)
                    s2 = clamp((dsec + 0.5) / (dpri + 0.5), 0.0, 1.0)
        case Axis.Z:
            raise ValueError("Axis Z calculations not yet complete!")

    return min(s1, s2), max(s1, s2)


def dsdp_slopes_west(
    dpri: int, dsec: int, octant: Octant, axis: Axis
) -> Tuple[float, float]:
    """Gets `dsec/dpri` slope range to cell's West side based on Octant."""

    match axis:
        case Axis.X:
            match octant:
                case Octant.O1 | Octant.O4 | Octant.O5 | Octant.O8:
                    if dpri == 0:
                        return (0.0, 0.0)
                    s1 = clamp((dsec - 0.5) / (dpri - 0.5), 0.0, 1.0)
                    s2 = clamp((dsec + 0.5) / (dpri - 0.5), 0.0, 1.0)
                case Octant.O2 | Octant.O3 | Octant.O6 | Octant.O7:
                    s1 = clamp((dsec - 0.5) / (dpri + 0.5), 0.0, 1.0)
                    s2 = clamp((dsec + 0.5) / (dpri + 0.5), 0.0, 1.0)
        case Axis.Y:
            match octant:
                case Octant.O1 | Octant.O4 | Octant.O5 | Octant.O8:
                    if dpri == 0:
                        return (0.0, 0.0)
                    s1 = clamp((dsec - 0.5) / (dpri + 0.5), 0.0, 1.0)
                    s2 = clamp((dsec - 0.5) / (dpri - 0.5), 0.0, 1.0)
                case Octant.O2 | Octant.O3 | Octant.O6 | Octant.O7:
                    s1 = clamp((dsec + 0.5) / (dpri + 0.5), 0.0, 1.0)
                    s2 = clamp((dsec + 0.5) / (dpri - 0.5), 0.0, 1.0)
        case Axis.Z:
            raise ValueError("Axis Z calculations not yet complete!")

    return min(s1, s2), max(s1, s2)


def dzdp_slopes_cell(
    dpri: int, dz: int, wall_ht: float, eye_ht: float, octant: Octant, axis: Axis
) -> Tuple[float, float]:
    """Gets `dz/dpri` slope range based on octant, for an entire cell (structure).

    `eye_ht` is FOV level as % of cell height. If max cell ht is 8 and eye height
    is 6 (standing), eye_ht height is 0.75. `wall_ht` is similar (1.0 = full ht),
    representing the height of the structure (rather than a wall).

    If dz >= 0, the "high" slope reaches the upper part of the wall.  If dz < 0,
    the "high" slope reaches the bottom of the cell (the floor).
    """
    if axis == Axis.Z:
        raise ValueError("dzdp slopes do not apply to the Z axis!")

    match octant:
        case Octant.O1 | Octant.O2 | Octant.O3 | Octant.O4:
            s1 = clamp((dz - eye_ht) / (dpri - 0.5), 0.0, 1.0)
            s2 = clamp((dz + wall_ht - eye_ht) / (dpri - 0.5), 0.0, 1.0)
        case Octant.O5 | Octant.O6 | Octant.O7 | Octant.O8:
            if dpri == 0:
                return (0.0, 1.0)
            s1 = clamp((dz + eye_ht - wall_ht) / (dpri + 0.5), 0.0, 1.0)
            s2 = clamp((dz + eye_ht) / (dpri - 0.5), 0.0, 1.0)

    return min(s1, s2), max(s1, s2)


def dzdp_slopes_floor(
    dpri: int, dz: int, eye_ht: float, octant: Octant, axis: Axis
) -> Tuple[float, float]:
    """Gets `dz/dpri` slope range based on octant, for all walls.

    `eye_ht` is FOV level as % of cell height. If max cell ht is 8 and eye height
    is 6 (standing), eye_ht height is 0.75.
    """
    if axis == Axis.Z:
        raise ValueError("dzdp slopes do not apply to the Z axis!")

    match octant:
        case Octant.O1 | Octant.O2 | Octant.O3 | Octant.O4:
            # Own floor doesn't block when looking up
            if dpri == 0:
                return (0.0, 0.0)
            s1 = clamp((dz - eye_ht) / (dpri + 0.5), 0.0, 1.0)
            s2 = clamp((dz - eye_ht) / (dpri - 0.5), 0.0, 1.0)
        case Octant.O5 | Octant.O6 | Octant.O7 | Octant.O8:
            # Own floor blocks only diagonal corner when looking down
            if dpri == 0:
                return (1.0, 1.0)
            s1 = clamp((dz + eye_ht) / (dpri + 0.5), 0.0, 1.0)
            s2 = clamp((dz + eye_ht) / (dpri - 0.5), 0.0, 1.0)

    return min(s1, s2), max(s1, s2)


def dzdp_slopes_north(
    dpri: int, dz: int, wall_ht: float, eye_ht: float, octant: Octant, axis: Axis
) -> Tuple[float, float]:
    """Gets `dz/dpri` slope range based on octant, to the North wall.

    `eye_ht` is FOV level as % of cell height. If max cell ht is 8 and eye height
    is 6 (standing), eye_ht height is 0.75. `wall_ht` is similar (1.0 = full ht).

    If dz >= 0, the "high" slope reaches the upper part of the wall.  If dz < 0,
    the "high" slope reaches the bottom of the cell (the floor).

    For dzdp, choose the primary distance that gives the most accurate Z-slope range.
    To visualize, try using a side view.
    """
    # NOTE: X: 1,2,3,4 should all use
    o = octant

    match octant, axis:
        case (_, Axis.Z):
            raise ValueError("dzdp slopes do not apply to the Z Axis!")
        case (o.O3, Axis.Y) | (o.O4, Axis.Y):
            # Upper Octants far from North wall
            s1 = clamp((dz - eye_ht) / (dpri + 0.5), 0.0, 1.0)
            s2 = clamp((dz + wall_ht - eye_ht) / (dpri + 0.5), 0.0, 1.0)
        case (o.O7, Axis.Y) | (o.O8, Axis.Y):
            # Lower Octants far from North wall
            s1 = clamp((dz + eye_ht - wall_ht) / (dpri + 0.5), 0.0, 1.0)
            s2 = clamp((dz + eye_ht) / (dpri + 0.5), 0.0, 1.0)
        case (o.O1, _) | (o.O2, _) | (o.O3, Axis.X) | (o.O4, Axis.X):
            # Upper Octants close to North wall
            s1 = clamp((dz - eye_ht) / (dpri - 0.5), 0.0, 1.0)
            s2 = clamp((dz + wall_ht - eye_ht) / (dpri - 0.5), 0.0, 1.0)
        case (o.O5, _) | (o.O6, _) | (o.O7, Axis.X) | (o.O8, Axis.X):
            # Lower Octants close to North wall
            s1 = clamp((dz + eye_ht - wall_ht) / (dpri - 0.5), 0.0, 1.0)
            s2 = clamp((dz + eye_ht) / (dpri - 0.5), 0.0, 1.0)
        case _:
            raise ValueError("Logic error! Function doesn't cover all cases!")

    return min(s1, s2), max(s1, s2)


def dzdp_slopes_west(
    dpri: int, dz: int, wall_ht: float, eye_ht: float, octant: Octant, axis: Axis
) -> Tuple[float, float]:
    """Gets `dz/dpri` slope range based on octant, to the West wall.

    `eye_ht` is FOV level as % of cell height. If max cell ht is 8 and eye height
    is 6 (standing), eye_ht height is 0.75. `wall_ht` is similar (1.0 = full ht).

    If dz >= 0, the "high" slope reaches the upper part of the wall.  If dz < 0,
    the "high" slope reaches the bottom of the cell (the floor).
    """
    o = octant

    match octant, axis:
        case (_, Axis.Z):
            raise ValueError("dzdp doesn't apply for Z Axis!")
        case (o.O2, Axis.X) | (o.O3, Axis.X):
            # Upper Octants far from West wall
            s1 = clamp((dz - eye_ht) / (dpri + 0.5), 0.0, 1.0)
            s2 = clamp((dz + wall_ht - eye_ht) / (dpri + 0.5), 0.0, 1.0)
        case (o.O6, Axis.X) | (o.O7, Axis.X):
            # Lower Octants far from West wall
            s1 = clamp((dz + eye_ht - wall_ht) / (dpri + 0.5), 0.0, 1.0)
            s2 = clamp((dz + eye_ht) / (dpri + 0.5), 0.0, 1.0)
        case (o.O1, _) | (o.O4, _) | (o.O2, Axis.Y) | (o.O3, Axis.Y):
            # Upper Octants close to West wall
            s1 = clamp((dz - eye_ht) / (dpri - 0.5), 0.0, 1.0)
            s2 = clamp((dz + wall_ht - eye_ht) / (dpri - 0.5), 0.0, 1.0)
        case (o.O5, _) | (o.O8, _) | (o.O6, Axis.Y) | (o.O7, Axis.Y):
            # Lower Octants close to West wall
            s1 = clamp((dz + eye_ht - wall_ht) / (dpri - 0.5), 0.0, 1.0)
            s2 = clamp((dz + eye_ht) / (dpri - 0.5), 0.0, 1.0)
        case _:
            raise ValueError("Logic error! Function doesn't cover all cases!")

    return min(s1, s2), max(s1, s2)


def octant_slope_summary(dpri: int, dsec: int, dz: int, wall_ht: float, eye_ht: float):
    """Prints a summary of (low,high) slopes for given octant coordinates."""
    for octant in [
        Octant.O1,
        Octant.O2,
        Octant.O3,
        Octant.O4,
        Octant.O5,
        Octant.O6,
        Octant.O7,
        Octant.O8,
    ]:
        for axis in [Axis.X, Axis.Y, Axis.Z]:
            cell = dsdp_slopes_cell(dpri, dsec)
            north = dsdp_slopes_north(dpri, dsec, octant, axis)
            west = dsdp_slopes_west(dpri, dsec, octant, axis)
            zwest = dzdp_slopes_west(dpri, dz, wall_ht, eye_ht, octant, axis)
            znorth = dzdp_slopes_north(dpri, dz, wall_ht, eye_ht, octant, axis)
            print(
                f"{octant}[{axis}] {dpri, dsec}\n  cell: {cell}\n  north: {north}\n  west: {west}\n  zwest: {zwest}\n  znorth: {znorth}"
            )


#   ########  ########   ######   ########
#      ##     ##        ##           ##
#      ##     ######     ######      ##
#      ##     ##              ##     ##
#      ##     ########  #######      ##


def test_dsdp_slopes_cell():
    """Test dsdp slopes to the entire Cell with all octants and axes."""
    cells = [(0, 0, 0), (1, 0, 0), (1, 1, 0), (1, 0, 1), (1, 1, 1)]
    actual = [dsdp_slopes_cell(dp, ds) for (dp, ds, _) in cells]
    expected = [(0.0, 1.0), (0.0, 1.0), (1 / 3, 1.0), (0.0, 1.0), (1 / 3, 1.0)]

    assert actual == expected


def test_dsdp_slopes_north():
    """Test dsdp slopes to the North wall with all octants and axes.

    Expected: octants (1,2,5,6) and (3,4,7,8) should have same slope ranges.
    """
    cells = [(0, 0, 0), (1, 0, 0), (1, 1, 0), (1, 0, 1), (1, 1, 1)]

    o1aX = [dsdp_slopes_north(dp, ds, Octant.O1, Axis.X) for (dp, ds, _) in cells]
    o1aY = [dsdp_slopes_north(dp, ds, Octant.O1, Axis.Y) for (dp, ds, _) in cells]
    o2aX = [dsdp_slopes_north(dp, ds, Octant.O2, Axis.X) for (dp, ds, _) in cells]
    o2aY = [dsdp_slopes_north(dp, ds, Octant.O2, Axis.Y) for (dp, ds, _) in cells]
    o3aX = [dsdp_slopes_north(dp, ds, Octant.O3, Axis.X) for (dp, ds, _) in cells]
    o3aY = [dsdp_slopes_north(dp, ds, Octant.O3, Axis.Y) for (dp, ds, _) in cells]
    o4aX = [dsdp_slopes_north(dp, ds, Octant.O4, Axis.X) for (dp, ds, _) in cells]
    o4aY = [dsdp_slopes_north(dp, ds, Octant.O4, Axis.Y) for (dp, ds, _) in cells]

    o5aX = [dsdp_slopes_north(dp, ds, Octant.O5, Axis.X) for (dp, ds, _) in cells]
    o5aY = [dsdp_slopes_north(dp, ds, Octant.O5, Axis.Y) for (dp, ds, _) in cells]
    o6aX = [dsdp_slopes_north(dp, ds, Octant.O6, Axis.X) for (dp, ds, _) in cells]
    o6aY = [dsdp_slopes_north(dp, ds, Octant.O6, Axis.Y) for (dp, ds, _) in cells]
    o7aX = [dsdp_slopes_north(dp, ds, Octant.O7, Axis.X) for (dp, ds, _) in cells]
    o7aY = [dsdp_slopes_north(dp, ds, Octant.O7, Axis.Y) for (dp, ds, _) in cells]
    o8aX = [dsdp_slopes_north(dp, ds, Octant.O8, Axis.X) for (dp, ds, _) in cells]
    o8aY = [dsdp_slopes_north(dp, ds, Octant.O8, Axis.Y) for (dp, ds, _) in cells]

    expected_o1aX = [(0.0, 0.0), (0.0, 0.0), (1 / 3, 1.0), (0.0, 0.0), (1 / 3, 1.0)]
    expected_o1aY = [(0.0, 0.0), (0.0, 1.0), (1.0, 1.0), (0.0, 1.0), (1.0, 1.0)]
    expected_o2aX = [(0.0, 0.0), (0.0, 0.0), (1 / 3, 1.0), (0.0, 0.0), (1 / 3, 1.0)]
    expected_o2aY = [(0.0, 0.0), (0.0, 1.0), (1.0, 1.0), (0.0, 1.0), (1.0, 1.0)]
    expected_o3aX = [(1.0, 1.0), (1 / 3, 1.0), (1.0, 1.0), (1 / 3, 1.0), (1.0, 1.0)]
    expected_o3aY = [(0.0, 1.0), (0.0, 1 / 3), (1 / 3, 1.0), (0.0, 1 / 3), (1 / 3, 1.0)]
    expected_o4aX = [(1.0, 1.0), (1 / 3, 1.0), (1.0, 1.0), (1 / 3, 1.0), (1.0, 1.0)]
    expected_o4aY = [(0.0, 1.0), (0.0, 1 / 3), (1 / 3, 1.0), (0.0, 1 / 3), (1 / 3, 1.0)]

    expected_o5aX = [(0.0, 0.0), (0.0, 0.0), (1 / 3, 1.0), (0.0, 0.0), (1 / 3, 1.0)]
    expected_o5aY = [(0.0, 0.0), (0.0, 1.0), (1.0, 1.0), (0.0, 1.0), (1.0, 1.0)]
    expected_o6aX = [(0.0, 0.0), (0.0, 0.0), (1 / 3, 1.0), (0.0, 0.0), (1 / 3, 1.0)]
    expected_o6aY = [(0.0, 0.0), (0.0, 1.0), (1.0, 1.0), (0.0, 1.0), (1.0, 1.0)]
    expected_o7aX = [(1.0, 1.0), (1 / 3, 1.0), (1.0, 1.0), (1 / 3, 1.0), (1.0, 1.0)]
    expected_o7aY = [(0.0, 1.0), (0.0, 1 / 3), (1 / 3, 1.0), (0.0, 1 / 3), (1 / 3, 1.0)]
    expected_o8aX = [(1.0, 1.0), (1 / 3, 1.0), (1.0, 1.0), (1 / 3, 1.0), (1.0, 1.0)]
    expected_o8aY = [(0.0, 1.0), (0.0, 1 / 3), (1 / 3, 1.0), (0.0, 1 / 3), (1 / 3, 1.0)]

    assert o1aX == expected_o1aX
    assert o1aY == expected_o1aY
    assert o2aX == expected_o2aX
    assert o2aY == expected_o2aY
    assert o3aX == expected_o3aX
    assert o3aY == expected_o3aY
    assert o4aX == expected_o4aX
    assert o4aY == expected_o4aY

    assert o5aX == expected_o5aX
    assert o5aY == expected_o5aY
    assert o6aX == expected_o6aX
    assert o6aY == expected_o6aY
    assert o7aX == expected_o7aX
    assert o7aY == expected_o7aY
    assert o8aX == expected_o8aX
    assert o8aY == expected_o8aY


def test_dsdp_slopes_west():
    """Test dsdp slopes to the West wall with all octants and axes.

    Expected: octants (1,4,5,8) and (2,3,6,7) should have same slope ranges.
    """
    cells = [(0, 0, 0), (1, 0, 0), (1, 1, 0), (1, 0, 1), (1, 1, 1)]

    o1aX = [dsdp_slopes_west(dp, ds, Octant.O1, Axis.X) for (dp, ds, _) in cells]
    o1aY = [dsdp_slopes_west(dp, ds, Octant.O1, Axis.Y) for (dp, ds, _) in cells]
    o4aX = [dsdp_slopes_west(dp, ds, Octant.O4, Axis.X) for (dp, ds, _) in cells]
    o4aY = [dsdp_slopes_west(dp, ds, Octant.O4, Axis.Y) for (dp, ds, _) in cells]
    o5aX = [dsdp_slopes_west(dp, ds, Octant.O5, Axis.X) for (dp, ds, _) in cells]
    o5aY = [dsdp_slopes_west(dp, ds, Octant.O5, Axis.Y) for (dp, ds, _) in cells]
    o8aX = [dsdp_slopes_west(dp, ds, Octant.O8, Axis.X) for (dp, ds, _) in cells]
    o8aY = [dsdp_slopes_west(dp, ds, Octant.O8, Axis.Y) for (dp, ds, _) in cells]

    o2aX = [dsdp_slopes_west(dp, ds, Octant.O2, Axis.X) for (dp, ds, _) in cells]
    o2aY = [dsdp_slopes_west(dp, ds, Octant.O2, Axis.Y) for (dp, ds, _) in cells]
    o3aX = [dsdp_slopes_west(dp, ds, Octant.O3, Axis.X) for (dp, ds, _) in cells]
    o3aY = [dsdp_slopes_west(dp, ds, Octant.O3, Axis.Y) for (dp, ds, _) in cells]
    o6aX = [dsdp_slopes_west(dp, ds, Octant.O6, Axis.X) for (dp, ds, _) in cells]
    o6aY = [dsdp_slopes_west(dp, ds, Octant.O6, Axis.Y) for (dp, ds, _) in cells]
    o7aX = [dsdp_slopes_west(dp, ds, Octant.O7, Axis.X) for (dp, ds, _) in cells]
    o7aY = [dsdp_slopes_west(dp, ds, Octant.O7, Axis.Y) for (dp, ds, _) in cells]

    expected_o1aX = [(0.0, 0.0), (0.0, 1.0), (1.0, 1.0), (0.0, 1.0), (1.0, 1.0)]
    expected_o1aY = [(0.0, 0.0), (0.0, 0.0), (1 / 3, 1.0), (0.0, 0.0), (1 / 3, 1.0)]
    expected_o4aX = [(0.0, 0.0), (0.0, 1.0), (1.0, 1.0), (0.0, 1.0), (1.0, 1.0)]
    expected_o4aY = [(0.0, 0.0), (0.0, 0.0), (1 / 3, 1.0), (0.0, 0.0), (1 / 3, 1.0)]
    expected_o5aX = [(0.0, 0.0), (0.0, 1.0), (1.0, 1.0), (0.0, 1.0), (1.0, 1.0)]
    expected_o5aY = [(0.0, 0.0), (0.0, 0.0), (1 / 3, 1.0), (0.0, 0.0), (1 / 3, 1.0)]
    expected_o8aX = [(0.0, 0.0), (0.0, 1.0), (1.0, 1.0), (0.0, 1.0), (1.0, 1.0)]
    expected_o8aY = [(0.0, 0.0), (0.0, 0.0), (1 / 3, 1.0), (0.0, 0.0), (1 / 3, 1.0)]

    expected_o2aX = [(0.0, 1.0), (0.0, 1 / 3), (1 / 3, 1.0), (0.0, 1 / 3), (1 / 3, 1.0)]
    expected_o2aY = [(0.0, 1.0), (1 / 3, 1.0), (1.0, 1.0), (1 / 3, 1.0), (1.0, 1.0)]
    expected_o3aX = [(0.0, 1.0), (0.0, 1 / 3), (1 / 3, 1.0), (0.0, 1 / 3), (1 / 3, 1.0)]
    expected_o3aY = [(0.0, 1.0), (1 / 3, 1.0), (1.0, 1.0), (1 / 3, 1.0), (1.0, 1.0)]
    expected_o6aX = [(0.0, 1.0), (0.0, 1 / 3), (1 / 3, 1.0), (0.0, 1 / 3), (1 / 3, 1.0)]
    expected_o6aY = [(0.0, 1.0), (1 / 3, 1.0), (1.0, 1.0), (1 / 3, 1.0), (1.0, 1.0)]
    expected_o7aX = [(0.0, 1.0), (0.0, 1 / 3), (1 / 3, 1.0), (0.0, 1 / 3), (1 / 3, 1.0)]
    expected_o7aY = [(0.0, 1.0), (1 / 3, 1.0), (1.0, 1.0), (1 / 3, 1.0), (1.0, 1.0)]

    assert o1aX == expected_o1aX
    assert o1aY == expected_o1aY
    assert o2aX == expected_o2aX
    assert o2aY == expected_o2aY
    assert o3aX == expected_o3aX
    assert o3aY == expected_o3aY
    assert o4aX == expected_o4aX
    assert o4aY == expected_o4aY

    assert o5aX == expected_o5aX
    assert o5aY == expected_o5aY
    assert o6aX == expected_o6aX
    assert o6aY == expected_o6aY
    assert o7aX == expected_o7aX
    assert o7aY == expected_o7aY
    assert o8aX == expected_o8aX
    assert o8aY == expected_o8aY


def test_dzdp_slopes_cell():
    """Test dzdp slopes to the entire Cell with all octants and axes.

    Expected: octants (1,2,3,4) and (5,6,7,8) should have same slope ranges.
    """
    cells = [(0, 0, 0), (1, 0, 0), (1, 1, 0), (1, 0, 1), (1, 1, 1)]

    upper = [Octant.O1, Octant.O2, Octant.O3, Octant.O4]
    lower = [Octant.O5, Octant.O6, Octant.O7, Octant.O8]

    expected_upper = [(0.0, 1.0), (0.0, 1.0), (0.0, 1.0), (1.0, 1.0), (1.0, 1.0)]
    expected_lower = [(0.0, 1.0), (0.0, 1.0), (0.0, 1.0), (1 / 3, 1.0), (1 / 3, 1.0)]

    for octant in upper:
        for axis in (Axis.X, Axis.Y):
            actual = [
                dzdp_slopes_cell(dp, dz, 1.0, 0.5, octant, axis)
                for (dp, _, dz) in cells
            ]
            assert actual == expected_upper

    for octant in lower:
        for axis in (Axis.X, Axis.Y):
            actual = [
                dzdp_slopes_cell(dp, dz, 1.0, 0.5, octant, axis)
                for (dp, _, dz) in cells
            ]
            assert actual == expected_lower


def test_dzdp_slopes_floor():
    """Test dzdp slopes to the entire Cell with all octants and axes.

    Expected: octants (1,2,3,4) and (5,6,7,8) should have same slope ranges.
    """
    cells = [(0, 0, 0), (1, 0, 0), (1, 1, 0), (1, 0, 1), (1, 1, 1)]

    upper = [Octant.O1, Octant.O2, Octant.O3, Octant.O4]
    lower = [Octant.O5, Octant.O6, Octant.O7, Octant.O8]

    expected_upper = [(0.0, 0.0), (0.0, 0.0), (0.0, 0.0), (1 / 3, 1.0), (1 / 3, 1.0)]
    expected_lower = [(1.0, 1.0), (1 / 3, 1.0), (1 / 3, 1.0), (1.0, 1.0), (1.0, 1.0)]

    for octant in upper:
        for axis in (Axis.X, Axis.Y):
            actual = [
                dzdp_slopes_floor(dp, dz, 0.5, octant, axis) for (dp, _, dz) in cells
            ]
            assert actual == expected_upper

    for octant in lower:
        for axis in (Axis.X, Axis.Y):
            actual = [
                dzdp_slopes_floor(dp, dz, 0.5, octant, axis) for (dp, _, dz) in cells
            ]
            assert actual == expected_lower


def test_dzdp_slopes_north():
    """Test dzdp slopes to the North wall with all octants and axes.

    Expected: octants (1, 2, 3X, 4X), (5, 6, 7X, 8X), (3Y, 4Y) and (7Y, 8Y) should
    have same slope ranges.
    """
    test_func = dzdp_slopes_north
    cells = [(0, 0, 0), (1, 0, 0), (1, 1, 0), (1, 0, 1), (1, 1, 1)]

    o1aX = [test_func(dp, dz, 1.0, 0.5, Octant.O1, Axis.X) for (dp, _, dz) in cells]
    o1aY = [test_func(dp, dz, 1.0, 0.5, Octant.O1, Axis.Y) for (dp, _, dz) in cells]
    o2aX = [test_func(dp, dz, 1.0, 0.5, Octant.O2, Axis.X) for (dp, _, dz) in cells]
    o2aY = [test_func(dp, dz, 1.0, 0.5, Octant.O2, Axis.Y) for (dp, _, dz) in cells]
    o3aX = [test_func(dp, dz, 1.0, 0.5, Octant.O3, Axis.X) for (dp, _, dz) in cells]
    o3aY = [test_func(dp, dz, 1.0, 0.5, Octant.O3, Axis.Y) for (dp, _, dz) in cells]
    o4aX = [test_func(dp, dz, 1.0, 0.5, Octant.O4, Axis.X) for (dp, _, dz) in cells]
    o4aY = [test_func(dp, dz, 1.0, 0.5, Octant.O4, Axis.Y) for (dp, _, dz) in cells]

    o5aX = [test_func(dp, dz, 1.0, 0.5, Octant.O5, Axis.X) for (dp, _, dz) in cells]
    o5aY = [test_func(dp, dz, 1.0, 0.5, Octant.O5, Axis.Y) for (dp, _, dz) in cells]
    o6aX = [test_func(dp, dz, 1.0, 0.5, Octant.O6, Axis.X) for (dp, _, dz) in cells]
    o6aY = [test_func(dp, dz, 1.0, 0.5, Octant.O6, Axis.Y) for (dp, _, dz) in cells]
    o7aX = [test_func(dp, dz, 1.0, 0.5, Octant.O7, Axis.X) for (dp, _, dz) in cells]
    o7aY = [test_func(dp, dz, 1.0, 0.5, Octant.O7, Axis.Y) for (dp, _, dz) in cells]
    o8aX = [test_func(dp, dz, 1.0, 0.5, Octant.O8, Axis.X) for (dp, _, dz) in cells]
    o8aY = [test_func(dp, dz, 1.0, 0.5, Octant.O8, Axis.Y) for (dp, _, dz) in cells]

    expected_o1aX = [(0.0, 1.0), (0.0, 1.0), (0.0, 1.0), (1.0, 1.0), (1.0, 1.0)]
    expected_o1aY = [(0.0, 1.0), (0.0, 1.0), (0.0, 1.0), (1.0, 1.0), (1.0, 1.0)]
    expected_o2aX = [(0.0, 1.0), (0.0, 1.0), (0.0, 1.0), (1.0, 1.0), (1.0, 1.0)]
    expected_o2aY = [(0.0, 1.0), (0.0, 1.0), (0.0, 1.0), (1.0, 1.0), (1.0, 1.0)]

    expected_o3aX = [(0.0, 1.0), (0.0, 1.0), (0.0, 1.0), (1.0, 1.0), (1.0, 1.0)]
    expected_o3aY = [(0.0, 1.0), (0.0, 1 / 3), (0.0, 1 / 3), (1 / 3, 1.0), (1 / 3, 1.0)]
    expected_o4aX = [(0.0, 1.0), (0.0, 1.0), (0.0, 1.0), (1.0, 1.0), (1.0, 1.0)]
    expected_o4aY = [(0.0, 1.0), (0.0, 1 / 3), (0.0, 1 / 3), (1 / 3, 1.0), (1 / 3, 1.0)]

    expected_o5aX = [(0.0, 1.0), (0.0, 1.0), (0.0, 1.0), (1.0, 1.0), (1.0, 1.0)]
    expected_o5aY = [(0.0, 1.0), (0.0, 1.0), (0.0, 1.0), (1.0, 1.0), (1.0, 1.0)]
    expected_o6aX = [(0.0, 1.0), (0.0, 1.0), (0.0, 1.0), (1.0, 1.0), (1.0, 1.0)]
    expected_o6aY = [(0.0, 1.0), (0.0, 1.0), (0.0, 1.0), (1.0, 1.0), (1.0, 1.0)]

    expected_o7aX = [(0.0, 1.0), (0.0, 1.0), (0.0, 1.0), (1.0, 1.0), (1.0, 1.0)]
    expected_o7aY = [(0.0, 1.0), (0.0, 1 / 3), (0.0, 1 / 3), (1 / 3, 1.0), (1 / 3, 1.0)]
    expected_o8aX = [(0.0, 1.0), (0.0, 1.0), (0.0, 1.0), (1.0, 1.0), (1.0, 1.0)]
    expected_o8aY = [(0.0, 1.0), (0.0, 1 / 3), (0.0, 1 / 3), (1 / 3, 1.0), (1 / 3, 1.0)]

    assert o1aX == expected_o1aX
    assert o1aY == expected_o1aY
    assert o2aX == expected_o2aX
    assert o2aY == expected_o2aY
    assert o3aX == expected_o3aX
    assert o3aY == expected_o3aY
    assert o4aX == expected_o4aX
    assert o4aY == expected_o4aY

    assert o5aX == expected_o5aX
    assert o5aY == expected_o5aY
    assert o6aX == expected_o6aX
    assert o6aY == expected_o6aY
    assert o7aX == expected_o7aX
    assert o7aY == expected_o7aY
    assert o8aX == expected_o8aX
    assert o8aY == expected_o8aY


def test_dzdp_slopes_west():
    """Test dzdp slopes to the West wall with all octants and axes.

    Expected: octants (1, 2Y, 3Y, 4), (5, 6Y, 7Y, 8), (2X, 3X) and (6X, 7X) should
    have same slope ranges."""
    test_func = dzdp_slopes_west
    cells = [(0, 0, 0), (1, 0, 0), (1, 1, 0), (1, 0, 1), (1, 1, 1)]

    o1aX = [test_func(dp, dz, 1.0, 0.5, Octant.O1, Axis.X) for (dp, _, dz) in cells]
    o1aY = [test_func(dp, dz, 1.0, 0.5, Octant.O1, Axis.Y) for (dp, _, dz) in cells]
    o2aX = [test_func(dp, dz, 1.0, 0.5, Octant.O2, Axis.X) for (dp, _, dz) in cells]
    o2aY = [test_func(dp, dz, 1.0, 0.5, Octant.O2, Axis.Y) for (dp, _, dz) in cells]
    o3aX = [test_func(dp, dz, 1.0, 0.5, Octant.O3, Axis.X) for (dp, _, dz) in cells]
    o3aY = [test_func(dp, dz, 1.0, 0.5, Octant.O3, Axis.Y) for (dp, _, dz) in cells]
    o4aX = [test_func(dp, dz, 1.0, 0.5, Octant.O4, Axis.X) for (dp, _, dz) in cells]
    o4aY = [test_func(dp, dz, 1.0, 0.5, Octant.O4, Axis.Y) for (dp, _, dz) in cells]

    o5aX = [test_func(dp, dz, 1.0, 0.5, Octant.O5, Axis.X) for (dp, _, dz) in cells]
    o5aY = [test_func(dp, dz, 1.0, 0.5, Octant.O5, Axis.Y) for (dp, _, dz) in cells]
    o6aX = [test_func(dp, dz, 1.0, 0.5, Octant.O6, Axis.X) for (dp, _, dz) in cells]
    o6aY = [test_func(dp, dz, 1.0, 0.5, Octant.O6, Axis.Y) for (dp, _, dz) in cells]
    o7aX = [test_func(dp, dz, 1.0, 0.5, Octant.O7, Axis.X) for (dp, _, dz) in cells]
    o7aY = [test_func(dp, dz, 1.0, 0.5, Octant.O7, Axis.Y) for (dp, _, dz) in cells]
    o8aX = [test_func(dp, dz, 1.0, 0.5, Octant.O8, Axis.X) for (dp, _, dz) in cells]
    o8aY = [test_func(dp, dz, 1.0, 0.5, Octant.O8, Axis.Y) for (dp, _, dz) in cells]

    expected_o1aX = [(0.0, 1.0), (0.0, 1.0), (0.0, 1.0), (1.0, 1.0), (1.0, 1.0)]
    expected_o1aY = [(0.0, 1.0), (0.0, 1.0), (0.0, 1.0), (1.0, 1.0), (1.0, 1.0)]
    expected_o2aX = [(0.0, 1.0), (0.0, 1 / 3), (0.0, 1 / 3), (1 / 3, 1.0), (1 / 3, 1.0)]
    expected_o2aY = [(0.0, 1.0), (0.0, 1.0), (0.0, 1.0), (1.0, 1.0), (1.0, 1.0)]

    expected_o3aX = [(0.0, 1.0), (0.0, 1 / 3), (0.0, 1 / 3), (1 / 3, 1.0), (1 / 3, 1.0)]
    expected_o3aY = [(0.0, 1.0), (0.0, 1.0), (0.0, 1.0), (1.0, 1.0), (1.0, 1.0)]
    expected_o4aX = [(0.0, 1.0), (0.0, 1.0), (0.0, 1.0), (1.0, 1.0), (1.0, 1.0)]
    expected_o4aY = [(0.0, 1.0), (0.0, 1.0), (0.0, 1.0), (1.0, 1.0), (1.0, 1.0)]

    expected_o5aX = [(0.0, 1.0), (0.0, 1.0), (0.0, 1.0), (1.0, 1.0), (1.0, 1.0)]
    expected_o5aY = [(0.0, 1.0), (0.0, 1.0), (0.0, 1.0), (1.0, 1.0), (1.0, 1.0)]
    expected_o6aX = [(0.0, 1.0), (0.0, 1 / 3), (0.0, 1 / 3), (1 / 3, 1.0), (1 / 3, 1.0)]
    expected_o6aY = [(0.0, 1.0), (0.0, 1.0), (0.0, 1.0), (1.0, 1.0), (1.0, 1.0)]

    expected_o7aX = [(0.0, 1.0), (0.0, 1 / 3), (0.0, 1 / 3), (1 / 3, 1.0), (1 / 3, 1.0)]
    expected_o7aY = [(0.0, 1.0), (0.0, 1.0), (0.0, 1.0), (1.0, 1.0), (1.0, 1.0)]
    expected_o8aX = [(0.0, 1.0), (0.0, 1.0), (0.0, 1.0), (1.0, 1.0), (1.0, 1.0)]
    expected_o8aY = [(0.0, 1.0), (0.0, 1.0), (0.0, 1.0), (1.0, 1.0), (1.0, 1.0)]

    assert o1aX == expected_o1aX
    assert o1aY == expected_o1aY
    assert o2aX == expected_o2aX
    assert o2aY == expected_o2aY
    assert o3aX == expected_o3aX
    assert o3aY == expected_o3aY
    assert o4aX == expected_o4aX
    assert o4aY == expected_o4aY

    assert o5aX == expected_o5aX
    assert o5aY == expected_o5aY
    assert o6aX == expected_o6aX
    assert o6aY == expected_o6aY
    assert o7aX == expected_o7aX
    assert o7aY == expected_o7aY
    assert o8aX == expected_o8aX
    assert o8aY == expected_o8aY


def test_octant_to_relative():
    octants = [
        Octant.O1,
        Octant.O2,
        Octant.O3,
        Octant.O4,
        Octant.O5,
        Octant.O6,
        Octant.O7,
        Octant.O8,
    ]
    axes = [Axis.X, Axis.Y, Axis.Z]
    actual = [
        octant_coords_to_relative(1, 2, 3, o, a).as_tuple()
        for o in octants
        for a in axes
    ]
    expected = [
        (1, 2, 3),
        (2, 1, 3),
        (1, 2, 3),
        (-1, 2, 3),
        (-2, 1, 3),
        (-1, 2, 3),
        (-1, -2, 3),
        (-2, -1, 3),
        (-1, -2, 3),
        (1, -2, 3),
        (2, -1, 3),
        (1, -2, 3),
        (1, 2, -3),
        (2, 1, -3),
        (1, 2, -3),
        (-1, 2, -3),
        (-2, 1, -3),
        (-1, 2, -3),
        (-1, -2, -3),
        (-2, -1, -3),
        (-1, -2, -3),
        (1, -2, -3),
        (2, -1, -3),
        (1, -2, -3),
    ]
    assert actual == expected


if __name__ == "__main__":
    print("\n----- Map Functions 3D -----")
