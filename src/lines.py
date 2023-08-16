"""Line Drawing Algorithms (2D)"""
import math
from typing import List, Tuple


def bresenham(x1: int, y1: int, x2: int, y2: int) -> List[Tuple[int, int]]:
    """Breshenham's line algorithm - 2D version."""
    result = [(x1, y1)]

    dx, dy = abs(x2 - x1), abs(y2 - y1)
    x_inc, y_inc = 1, 1
    x, y = x1, y1

    if x2 < x1:
        x_inc = -1
    if y2 < y1:
        y_inc = -1

    # Y-primary
    if dy > dx:
        tx = 2 * dx - dy

        for _ in range(dy):
            y += y_inc
            if tx >= 0:
                x += x_inc
                tx -= 2 * dy
            tx += 2 * dx

            result.append((x, y))

    # X-primary
    else:
        ty = 2 * dy - dx

        for _ in range(dx):
            x += x_inc
            if ty >= 0:
                y += y_inc
                ty -= 2 * dx
            ty += 2 * dy

            result.append((x, y))

    return result


def bresenham_full(x1: int, y1: int, x2: int, y2: int) -> List[Tuple[int, int]]:
    """Breshenham's line algorithm - 2D version that gets all tiles touched.

    `tx`, `ty` indicate full tile distance; `hx`, `hy` indicate half tile distance.
    """
    result = [(x1, y1)]

    dx, dy = abs(x2 - x1), abs(y2 - y1)
    x_inc, y_inc = 1, 1
    x, y = x1, y1

    if x2 < x1:
        x_inc = -1
    if y2 < y1:
        y_inc = -1

    # Y-primary
    if dy > dx:
        tx = 2 * dx - dy

        for _ in range(dy):
            y += y_inc
            hx = tx - dx

            if hx >= 0:
                result.append((x + x_inc, y - y_inc))
            if hx <= 0:
                result.append((x, y))
            if tx > 0:
                x += x_inc
                tx -= 2 * dy
                result.append((x, y))
            tx += 2 * dx

    # X-primary
    else:
        ty = 2 * dy - dx

        for _ in range(dx):
            x += x_inc
            hy = ty - dy

            if hy >= 0:
                result.append((x - x_inc, y + y_inc))
            if hy <= 0:
                result.append((x, y))
            if ty > 0:
                y += y_inc
                ty -= 2 * dx
                result.append((x, y))
            ty += 2 * dy

    return result


def fire_line(xi: float, yi: float, x2: int, y2: int) -> List[Tuple[int, int]]:
    """Returns all tiles touched from source tile to slope range of target tile.

    - `x1`, `y1` represent the source tile.
    - `x2`, `y2` represent the target tile.
    - `xi`, `yi` are starting floating point values.
    - `xf`, `yf` are ending floating point values.
    - `xs`, `ys` are x/y floating point shifts within source cell, normally `0.5`.
      If `xs = 0.5` and `ys = 0.5`, the fire line starts from XY center of cell.
      These can represent weapon/tool projections from the body (e.g. a gun barrel).
    - `d(x,y)_start`, `d(x,y)_end` are starting / ending range indexes.

    Fire line spans angle range beween lines `AB` and `AC`:
    ```none
            xi                          xf
    +----+----+                     B----+----+
    |       A |yi                   |         |
    |         |                     |    +    | yf
    |         |                     |         |
    +----+----+                     +----+----C
        src                             tgt
    (x1, y1)                    (x2, y2)
    ```

    Example fire lines:
    ```none

              ++T
             ++++                  S++++T
            S++

    (0.5, 0.5) to (4, 2)    (0.5, 0.5) to (5, 0)
    ```

    Y, X order of calculation is for optimum locality when selecting cells
    from the map, which are arranged in YX order.

    NOTE: assumes all values are positive and in-bounds.
    NOTE: to avoid dividing by zero, xs or ys should never be 0.0 or 1.0.
    """
    x1, y1 = int(xi), int(yi)
    xs, ys = xi - x1, yi - y1
    xf, yf = x2 + 0.5, y2 + 0.5
    cx, cy = abs(x2 - x1), abs(y2 - y1)
    dx, dy = abs(xf - xi), abs(yf - yi)
    dx_max, dy_max = cx + 1, cy + 1
    x_inc = 1 if x2 > x1 else -1
    y_inc = 1 if y2 > y1 else -1
    m = 0.000001

    if xf < xi:
        x_inc = -1
        xs = math.ceil(xi) - xi
    if yf < yi:
        y_inc = -1
        ys = math.ceil(yi) - yi

    result = []

    if cx == 0:
        return [(x1, y1 + y_inc * i) for i in range(dy_max)]
    if cy == 0:
        return [(x1 + x_inc * i, y1) for i in range(dx_max)]

    dxdy_lo = (dx - 0.5) / (dy + 0.5)
    dxdy_hi = (dx + 0.5) / (dy - 0.5)
    dx_lo_ref = xs - (dxdy_lo * ys)
    dx_hi_ref = xs + (dxdy_hi * (1.0 - ys))
    y = y1

    for y_ix in range(dy_max):
        dx_lo = dx_lo_ref + dxdy_lo * y_ix
        dx_hi = dx_hi_ref + dxdy_hi * y_ix
        dx_start = max(math.floor(dx_lo - m), 0)
        dx_end = min(math.ceil(dx_hi + m), dx_max)
        x = x1 + x_inc * dx_start

        for _ in range(dx_start, dx_end):
            result.append((x, y))
            x += x_inc

        dx_lo += dxdy_lo
        dx_hi += dxdy_hi
        y += y_inc

    return result


#   ########  ########   ######   ########
#      ##     ##        ##           ##
#      ##     ######     ######      ##
#      ##     ##              ##     ##
#      ##     ########  #######      ##


def test_bresenham_2D_reciprocal():
    """Checks if 2D bresenham lines are reciprocal."""
    suite = [(int(0), int(0), x, y) for x in range(0, 5) for y in range(-5, 5)]
    suite.extend([(x, y, 0, 0) for x in range(0, 5) for y in range(-5, 5)])

    for x1, y1, x2, y2 in suite:
        fwd = bresenham(x1, y1, x2, y2)
        rev = bresenham(x2, y2, x1, y1)
        assert sorted(fwd) == sorted(rev)


def test_bresenham_2D_full():
    """Check expected values for the `bresenham_full()` 2D function."""
    suite = [
        (0, 0, 5, 0),
        (0, 0, -5, 0),
        (0, 0, 0, 5),
        (0, 0, 0, -5),
        (5, 0, 0, 0),
        (-5, 0, 0, 0),
        (0, 5, 0, 0),
        (0, -5, 0, 0),
        (0, 0, 2, 2),
        (2, 2, 0, 0),
        (0, 0, 4, 2),
        (4, 2, 0, 0),
    ]
    expected = [
        [(0, 0), (1, 0), (2, 0), (3, 0), (4, 0), (5, 0)],
        [(0, 0), (-1, 0), (-2, 0), (-3, 0), (-4, 0), (-5, 0)],
        [(0, 0), (0, 1), (0, 2), (0, 3), (0, 4), (0, 5)],
        [(0, 0), (0, -1), (0, -2), (0, -3), (0, -4), (0, -5)],
        [(5, 0), (4, 0), (3, 0), (2, 0), (1, 0), (0, 0)],
        [(-5, 0), (-4, 0), (-3, 0), (-2, 0), (-1, 0), (0, 0)],
        [(0, 5), (0, 4), (0, 3), (0, 2), (0, 1), (0, 0)],
        [(0, -5), (0, -4), (0, -3), (0, -2), (0, -1), (0, 0)],
        [(0, 0), (0, 1), (1, 0), (1, 1), (1, 2), (2, 1), (2, 2)],
        [(2, 2), (2, 1), (1, 2), (1, 1), (1, 0), (0, 1), (0, 0)],
        [(0, 0), (1, 0), (1, 1), (2, 1), (3, 1), (3, 2), (4, 2)],
        [(4, 2), (3, 2), (3, 1), (2, 1), (1, 1), (1, 0), (0, 0)],
    ]
    actual = [bresenham_full(*coords) for coords in suite]
    for i, e in enumerate(expected):
        assert actual[i] == e
