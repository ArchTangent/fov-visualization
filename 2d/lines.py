"""Line Drawing Algorithms (2D)"""
from typing import List, Tuple


def bresenham(x1: int, y1: int, x2: int, y2: int) -> List[Tuple[int, int]]:
    """Bresenham's Line Algorithm - 2D version.

    All lines should be reciprocal. Uses 1000 for granularity `g`."""
    # Deltas
    dx, dy = x2 - x1, y2 - y1
    abs_dx, abs_dy = abs(dx), abs(dy)

    if abs_dx == 0 and abs_dy == 0:
        return [(x1, y1)]

    # Sign, increment, and tile distance
    x_inc, y_inc = 1, 1
    if dx < 0:
        x_inc = -1
    if dy < 0:
        y_inc = -1
    dist = 500

    # Choose primary axis (Y or X)
    if abs_dy > abs_dx:
        dsdp = int(abs_dx / abs_dy * 1000) * x_inc
        pri, sec = y1, x1
        result = [(sec, pri)]

        for _ in range(abs_dy):
            pri += y_inc
            dist += dsdp

            if dist >= 1000:
                dist -= 1000
                sec += 1
            elif dist < 0:
                dist += 1000
                sec -= 1

            result.append((sec, pri))
    else:
        dsdp = int(abs_dy / abs_dx * 1000) * y_inc
        pri_inc = x_inc
        pri, sec = x1, y1
        result = [(pri, sec)]

        for _ in range(abs_dx):
            pri += pri_inc
            dist += dsdp

            if dist >= 1000:
                dist -= 1000
                sec += 1
            elif dist < 0:
                dist += 1000
                sec -= 1

            result.append((pri, sec))

    return result


def bresenham_full(
    x1: int, y1: int, x2: int, y2: int, g: int = 1000
) -> List[Tuple[int, int]]:
    """Bresenham's Line Algorithm - 2D version that gets all tiles touched.

    Secondary distance is th secondary axis distance from the next tile edge.
    Indicates a crossing of a tile boundary.

    `g` is the granularity of cell distance. A higher value detects corners better.
    """
    # Deltas
    dx, dy = (x2 - x1, y2 - y1)
    abs_dx, abs_dy = abs(dx), abs(dy)
    abs_dist = max(abs_dx, abs_dy)

    if abs_dist == 0:
        return [(x1, y1)]

    # Sign and increment
    x_inc, y_inc = 1, 1
    if dx < 0:
        x_inc = -1
    if dy < 0:
        y_inc = -1

    result = [(x1, y1)]
    x, y = x1, y1

    # Choose primary axis
    if abs_dy > abs_dx:
        dxdy = int(abs_dx / abs_dy * g)
        dxdy_edge = dxdy // 2
        dist = g // 2

        for _ in range(abs_dist):
            y += y_inc
            dist += dxdy
            dist_edge = dist - dxdy_edge

            if dist_edge >= g:
                result.append((x + x_inc, y - y_inc))

            if dist_edge <= g:
                result.append((x, y))

            if dist > g:
                dist -= g
                x += x_inc
                result.append((x, y))
    else:
        dydx = int(abs_dy / abs_dx * g)
        dydx_edge = dydx // 2
        dist = g // 2

        for _ in range(abs_dist):
            x += x_inc
            dist += dydx
            dist_edge = dist - dydx_edge

            if dist_edge >= g:
                result.append((x - x_inc, y + y_inc))

            if dist_edge <= g:
                result.append((x, y))

            if dist > g:
                dist -= g
                y += y_inc
                result.append((x, y))

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
