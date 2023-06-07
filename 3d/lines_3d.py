"""Line Drawing Algorithms (3D)"""
from typing import List, Tuple


def bresenham(x1: int, y1: int, z1: int, x2: int, y2: int, z2: int):
    """Bresenham's line algorithm - 3D version."""

    result = [(x1, y1, z1)]

    dx = abs(x2 - x1)
    dy = abs(y2 - y1)
    dz = abs(z2 - z1)

    if x2 > x1:
        x_inc = 1
    else:
        x_inc = -1
    if y2 > y1:
        y_inc = 1
    else:
        y_inc = -1
    if z2 > z1:
        z_inc = 1
    else:
        z_inc = -1

    # X-primary
    if dx >= dy and dx >= dz:
        p1 = 2 * dy - dx
        p2 = 2 * dz - dx
        while x1 != x2:
            x1 += x_inc
            if p1 >= 0:
                y1 += y_inc
                p1 -= 2 * dx
            if p2 >= 0:
                z1 += z_inc
                p2 -= 2 * dx
            p1 += 2 * dy
            p2 += 2 * dz
            result.append((x1, y1, z1))

    # Y-primary
    elif dy >= dx and dy >= dz:
        p1 = 2 * dx - dy
        p2 = 2 * dz - dy
        while y1 != y2:
            y1 += y_inc
            if p1 >= 0:
                x1 += x_inc
                p1 -= 2 * dy
            if p2 >= 0:
                z1 += z_inc
                p2 -= 2 * dy
            p1 += 2 * dx
            p2 += 2 * dz
            result.append((x1, y1, z1))

    # Z-primary
    else:
        p1 = 2 * dy - dz
        p2 = 2 * dx - dz
        while z1 != z2:
            z1 += z_inc
            if p1 >= 0:
                y1 += y_inc
                p1 -= 2 * dz
            if p2 >= 0:
                x1 += x_inc
                p2 -= 2 * dz
            p1 += 2 * dy
            p2 += 2 * dx
            result.append((x1, y1, z1))

    return result


def bresenham_full(x1: int, y1: int, z1: int, x2: int, y2: int, z2: int) -> List[Tuple[int, int, int]]:
    """Breshenham's line algorithm - 3D version that gets all tiles touched.
    
    `tx,ty,tz` indicate full tile distance; `hx,hy,hz` indicate half tile distance.
    """
    result = [(x1, y1, z1)]

    dx, dy, dz = abs(x2 - x1), abs(y2 - y1), abs(z2 - z1)       
    x_inc, y_inc, z_inc = 1, 1, 1
    x, y, z  = x1, y1, z1

    if x2 < x1:
        x_inc = -1
    if y2 < y1:
        y_inc = -1
    if z2 < z1:
        z_inc = -1

    # X-primary
    if dx >= dy and dx >= dz:
        ty = 2 * dy - dx
        tz = 2 * dz - dx

        for _ in range(dx):
            x += x_inc
            hy = ty - dy
            hz = tz - dz

            if hy >= 0:
                if hz >= 0:
                    result.append((x - x_inc, y, z + z_inc))
                    result.append((x - x_inc, y + y_inc, z))
                    result.append((x - x_inc, y + y_inc, z + z_inc))
            if hy <= 0:
                if hz <= 0:
                    result.append((x, y, z))
                if tz > 0:
                    result.append((x, y, z + z_inc))
            if ty > 0:
                y += y_inc        
                ty -= 2 * dx
                if hz <= 0:
                    result.append((x, y, z))
                if tz > 0:
                    result.append((x, y, z + z_inc))
            
            # Increment z separately
            if tz > 0:
                z += z_inc
                tz -= 2 * dx

            ty += 2 * dy
            tz += 2 * dz

    # Y-primary
    elif dy >= dx and dy >= dz:
        tx = 2 * dx - dy
        tz = 2 * dz - dy

        for _ in range(dy):
            y += y_inc
            hx = tx - dx
            hz = tz - dz

            if hx >= 0:
                if hz >= 0:
                    result.append((x, y - y_inc, z + z_inc))
                    result.append((x + x_inc, y - y_inc, z))
                    result.append((x + x_inc, y - y_inc, z + z_inc))
            if hx <= 0:
                if hz <= 0:
                    result.append((x, y, z))
                if tz > 0:
                    result.append((x, y, z + z_inc))
            if tx > 0:
                x += x_inc
                tx -= 2 * dy
                if hz <= 0:
                    result.append((x, y, z))
                if tz > 0:
                    result.append((x, y, z + z_inc))
                
            # Increment z separately
            if tz > 0:
                z += z_inc
                tz -= 2 * dy

            tx += 2 * dx
            tz += 2 * dz
    
    # Z-primary
    else:
        tx = 2 * dx - dz
        ty = 2 * dy - dz

        for _ in range(dz):
            z += z_inc
            hx = tx - dx
            hy = ty - dy

            if hx >= 0:
                if hy >= 0:
                    result.append((x, y + y_inc, z - z_inc))
                    result.append((x + x_inc, y, z - z_inc))
                    result.append((x + x_inc, y + y_inc, z - z_inc))
            if hx <= 0:
                if hy <= 0:
                    result.append((x, y, z))
                if ty > 0:
                    result.append((x, y + y_inc, z))
            if tx > 0:
                x += x_inc
                tx -= 2 * dz
                if hy <= 0:
                    result.append((x, y, z))
                if ty > 0:
                    result.append((x, y + y_inc, z))
                
            # Increment y separately
            if ty > 0:
                y += y_inc
                ty -= 2 * dz

            tx += 2 * dx
            ty += 2 * dy

    return result


def fire_line(
    x1: int, y1: int, z1: int, x2: int, y2: int, z2: int
) -> List[Tuple[int, int, int]]:
    """Fire line - 3D version. Differs slightly from Breshenham.

    All lines should be reciprocal. Uses 1000 for granularity `g`."""
    result = [(x1, y1, z1)]
    
    # Deltas
    dx, dy, dz = x2 - x1, y2 - y1, z2 - z1
    abs_dx, abs_dy, abs_dz = abs(dx), abs(dy), abs(dz)

    # Sign, increment, and cell distance
    x, y, z = x1, y1, z1
    x_inc, y_inc, z_inc = 1, 1, 1
    if dx < 0:
        x_inc = -1
    if dy < 0:
        y_inc = -1
    if dz < 0:
        z_inc = -1

    # Choose primary axis (X, Y, or Z)
    match abs_dy > abs_dx, abs_dz > abs_dy, abs_dz > abs_dx:
        case False, _, False:
            # X Axis dominant
            if dx == 0:
                return result

            dydx = int(dy / abs_dx * 1000)
            dzdx = int(dz / abs_dx * 1000)

            y_dist = 500
            z_dist = 500

            for _ in range(abs_dx):
                x += x_inc
                y_dist += dydx
                z_dist += dzdx

                if y_dist >= 1000:
                    y_dist -= 1000
                    y += 1
                elif y_dist < 0:
                    y_dist += 1000
                    y -= 1

                if z_dist >= 1000:
                    z_dist -= 1000
                    z += 1
                elif z_dist < 0:
                    z_dist += 1000
                    z -= 1

                result.append((x, y, z))

        case True, False, _:
            # Y Axis dominant
            if dy == 0:
                return result

            dxdy = int(dx / abs_dy * 1000)
            dzdy = int(dz / abs_dy * 1000)
            x_dist = 500
            z_dist = 500

            for _ in range(abs_dy):
                y += y_inc
                x_dist += dxdy
                z_dist += dzdy

                if x_dist >= 1000:
                    x_dist -= 1000
                    x += 1
                elif x_dist < 0:
                    x_dist += 1000
                    x -= 1

                if z_dist >= 1000:
                    z_dist -= 1000
                    z += 1
                elif z_dist < 0:
                    z_dist += 1000
                    z -= 1

                result.append((x, y, z))

        case _:
            # Z Axis dominant
            if dz == 0:
                return result

            dxdz = int(dx / abs_dz * 1000)
            dydz = int(dy / abs_dz * 1000)
            x_dist = 500
            y_dist = 500

            for _ in range(abs_dz):
                z += z_inc
                x_dist += dxdz
                y_dist += dydz

                if x_dist >= 1000:
                    x_dist -= 1000
                    x += 1
                elif x_dist < 0:
                    x_dist += 1000
                    x -= 1

                if y_dist >= 1000:
                    y_dist -= 1000
                    y += 1
                elif y_dist < 0:
                    y_dist += 1000
                    y -= 1

                result.append((x, y, z))

    return result


def fire_line_full(
    x1: int, y1: int, z1: int, x2: int, y2: int, z2: int
) -> List[Tuple[int, int, int]]:
    """Fire line full - 3D version that gets all tiles touched.

    Secondary distance is th secondary axis distance from the next tile edge.
    Indicates a crossing of a tile boundary.

    `g` is the granularity of cell distance. A higher value detects corners better.
    """

    result = [(x1, y1, z1)]

    # Deltas
    dx, dy, dz = x2 - x1, y2 - y1, z2 - z1   
    abs_dx, abs_dy, abs_dz = abs(dx), abs(dy), abs(dz)

    # Sign, increment, and tile distance
    x, y, z = x1, y1, z1
    x_inc, y_inc, z_inc = 1, 1, 1
    if dx < 0:
        x_inc = -1
    if dy < 0:
        y_inc = -1
    if dz < 0:
        z_inc = -1

    x_dist, y_dist, z_dist = 500, 500, 500

    # Choose primary axis (Z, Y, or X)
    match abs_dy > abs_dx, abs_dz > abs_dy, abs_dz > abs_dx:
        case False, _, False:
            # X Axis dominant
            if dx == 0:
                return result

            dydx = int(abs_dy / abs_dx * 1000)
            dzdx = int(abs_dz / abs_dx * 1000)
            dydx_edge = dydx // 2
            dzdx_edge = dzdx // 2

            for _ in range(abs_dx):
                x += x_inc
                y_dist += dydx
                y_dist_edge = y_dist - dydx_edge
                z_dist += dzdx
                z_dist_edge = z_dist - dzdx_edge

                # Get each valid z for given y distance
                if y_dist_edge >= 1000:
                    if z_dist_edge >= 1000:
                        result.append((x - x_inc, y, z + z_inc))
                        result.append((x - x_inc, y + y_inc, z))
                        result.append((x - x_inc, y + y_inc, z + z_inc))

                if y_dist_edge <= 1000:
                    if z_dist_edge <= 1000:
                        result.append((x, y, z))
                    if z_dist > 1000:
                        result.append((x, y, z + z_inc))

                if y_dist > 1000:
                    y_dist -= 1000
                    y += y_inc
                    if z_dist_edge <= 1000:
                        result.append((x, y, z))
                    if z_dist > 1000:
                        result.append((x, y, z + z_inc))

                # Increment z separately
                if z_dist > 1000:
                    z_dist -= 1000
                    z += z_inc

        case True, False, _:
            # Y Axis dominant
            if dy == 0:
                return result

            dxdy = int(abs_dx / abs_dy * 1000)
            dzdy = int(abs_dz / abs_dy * 1000)
            dxdy_edge = dxdy // 2
            dzdy_edge = dzdy // 2

            for _ in range(abs_dy):
                y += y_inc
                x_dist += dxdy
                x_dist_edge = x_dist - dxdy_edge
                z_dist += dzdy
                z_dist_edge = z_dist - dzdy_edge

                # Get each valid z for given x distance
                if x_dist_edge >= 1000:
                    if z_dist_edge >= 1000:
                        result.append((x, y - y_inc, z + z_inc))
                        result.append((x + x_inc, y - y_inc, z))
                        result.append((x + x_inc, y - y_inc, z + z_inc))

                if x_dist_edge <= 1000:
                    if z_dist_edge <= 1000:
                        result.append((x, y, z))
                    if z_dist > 1000:
                        result.append((x, y, z + z_inc))

                if x_dist > 1000:
                    x_dist -= 1000
                    x += x_inc
                    if z_dist_edge <= 1000:
                        result.append((x, y, z))
                    if z_dist > 1000:
                        result.append((x, y, z + z_inc))

                # Increment z separately
                if z_dist > 1000:
                    z_dist -= 1000
                    z += z_inc

        case _:
            # Z Axis dominant
            if dz == 0:
                return result

            dxdz = int(abs_dx / abs_dz * 1000)
            dydz = int(abs_dy / abs_dz * 1000)
            dxdz_edge = dxdz // 2
            dydz_edge = dydz // 2

            for _ in range(abs_dz):
                z += z_inc
                x_dist += dxdz
                x_dist_edge = x_dist - dxdz_edge
                y_dist += dydz
                y_dist_edge = y_dist - dydz_edge

                # Get each valid y for given x distance
                if x_dist_edge >= 1000:
                    if y_dist_edge >= 1000:
                        result.append((x, y + y_inc, z - z_inc))
                        result.append((x + x_inc, y, z - z_inc))
                        result.append((x + x_inc, y + y_inc, z - z_inc))

                if x_dist_edge <= 1000:
                    if y_dist_edge <= 1000:
                        result.append((x, y, z))
                    if y_dist > 1000:
                        result.append((x, y + y_inc, z))

                if x_dist > 1000:
                    x_dist -= 1000
                    x += x_inc
                    if y_dist_edge <= 1000:
                        result.append((x, y, z))
                    if y_dist > 1000:
                        result.append((x, y + y_inc, z))

                # Increment y separately
                if y_dist > 1000:
                    y_dist -= 1000
                    y += y_inc

    return result


#   ########  ########   ######   ########
#      ##     ##        ##           ##
#      ##     ######     ######      ##
#      ##     ##              ##     ##
#      ##     ########  #######      ##

def test_bresenham_3D_full():
    """Check expected values for the `bresenham_full()` 3D function."""
    suite = [
        (0, 0, 0, 3, 0, 0),
        (3, 0, 0, 0, 0, 0),
        (0, 0, 0, 0, 3, 0),
        (0, 3, 0, 0, 0, 0),
        (0, 0, 0, 0, 0, 3),
        (0, 0, 3, 0, 0, 0),
        (0, 0, 0, 1, 1, 1),
        (1, 1, 1, 0, 0, 0),
        (0, 0, 0, 3, 1, 1),
        (3, 1, 1, 0, 0, 0),
        (0, 0, 0, 1, 3, 1),
        (1, 3, 1, 0, 0, 0),
        (0, 0, 0, 1, 1, 3),
        (1, 1, 3, 0, 0, 0),
    ]
    expected = [
        [(0, 0, 0), (1, 0, 0), (2, 0, 0), (3, 0, 0)],
        [(3, 0, 0), (2, 0, 0), (1, 0, 0), (0, 0, 0)],
        [(0, 0, 0), (0, 1, 0), (0, 2, 0), (0, 3, 0)],
        [(0, 3, 0), (0, 2, 0), (0, 1, 0), (0, 0, 0)],
        [(0, 0, 0), (0, 0, 1), (0, 0, 2), (0, 0, 3)],
        [(0, 0, 3), (0, 0, 2), (0, 0, 1), (0, 0, 0)],        
        [(0, 0, 0), (0, 0, 1), (0, 1, 0), (0, 1, 1), (1, 0, 0), (1, 0, 1), (1, 1, 0), (1, 1, 1)],
        [(1, 1, 1), (1, 1, 0), (1, 0, 1), (1, 0, 0), (0, 1, 1), (0, 1, 0), (0, 0, 1), (0, 0, 0)],
        [(0, 0, 0), (1, 0, 0), (1, 0, 1), (1, 1, 0), (1, 1, 1), (2, 0, 0), (2, 0, 1), (2, 1, 0), (2, 1, 1), (3, 1, 1)],
        [(3, 1, 1), (2, 1, 1), (2, 1, 0), (2, 0, 1), (2, 0, 0), (1, 1, 1), (1, 1, 0), (1, 0, 1), (1, 0, 0), (0, 0, 0)],
        [(0, 0, 0), (0, 1, 0), (0, 1, 1), (1, 1, 0), (1, 1, 1), (0, 2, 0), (0, 2, 1), (1, 2, 0), (1, 2, 1), (1, 3, 1)],
        [(1, 3, 1), (1, 2, 1), (1, 2, 0), (0, 2, 1), (0, 2, 0), (1, 1, 1), (1, 1, 0), (0, 1, 1), (0, 1, 0), (0, 0, 0)],
        [(0, 0, 0), (0, 0, 1), (0, 1, 1), (1, 0, 1), (1, 1, 1), (0, 0, 2), (0, 1, 2), (1, 0, 2), (1, 1, 2), (1, 1, 3)],
        [(1, 1, 3), (1, 1, 2), (1, 0, 2), (0, 1, 2), (0, 0, 2), (1, 1, 1), (1, 0, 1), (0, 1, 1), (0, 0, 1), (0, 0, 0)]
    ]
    actual = [bresenham_full(*coords) for coords in suite]
    for i, e in enumerate(expected):
        assert actual[i] == e


def test_fire_line_3D_reciprocal():
    """Checks if 3D fire lines are reciprocal."""
    suite = [
        (int(0), int(0), int(0), x, y, z)
        for x in range(0, 5)
        for y in range(-5, 5)
        for z in range(-5, 5)
    ]
    suite.extend(
        [
            (x, y, z, 0, 0, 0)
            for x in range(0, 5)
            for y in range(-5, 5)
            for z in range(-5, 5)
        ]
    )

    for x1, y1, z1, x2, y2, z2 in suite:
        fwd = fire_line(x1, y1, z1, x2, y2, z2)
        rev = fire_line(x2, y2, z2, x1, y1, z1)
        assert sorted(fwd) == sorted(rev)


def test_fire_line_3D_full():
    """Check expected values for the `fire_line_full()` 3D function."""
    suite = [
        (0, 0, 0, 3, 0, 0),
        (3, 0, 0, 0, 0, 0),
        (0, 0, 0, 0, 3, 0),
        (0, 3, 0, 0, 0, 0),
        (0, 0, 0, 0, 0, 3),
        (0, 0, 3, 0, 0, 0),
        (0, 0, 0, 1, 1, 1),
        (1, 1, 1, 0, 0, 0),
        (0, 0, 0, 3, 1, 1),
        (3, 1, 1, 0, 0, 0),
        (0, 0, 0, 1, 3, 1),
        (1, 3, 1, 0, 0, 0),
        (0, 0, 0, 1, 1, 3),
        (1, 1, 3, 0, 0, 0),
    ]
    expected = [
        [(0, 0, 0), (1, 0, 0), (2, 0, 0), (3, 0, 0)],
        [(3, 0, 0), (2, 0, 0), (1, 0, 0), (0, 0, 0)],
        [(0, 0, 0), (0, 1, 0), (0, 2, 0), (0, 3, 0)],
        [(0, 3, 0), (0, 2, 0), (0, 1, 0), (0, 0, 0)],
        [(0, 0, 0), (0, 0, 1), (0, 0, 2), (0, 0, 3)],
        [(0, 0, 3), (0, 0, 2), (0, 0, 1), (0, 0, 0)],        
        [(0, 0, 0), (0, 0, 1), (0, 1, 0), (0, 1, 1), (1, 0, 0), (1, 0, 1), (1, 1, 0), (1, 1, 1)],
        [(1, 1, 1), (1, 1, 0), (1, 0, 1), (1, 0, 0), (0, 1, 1), (0, 1, 0), (0, 0, 1), (0, 0, 0)],
        [(0, 0, 0), (1, 0, 0), (1, 0, 1), (1, 1, 0), (1, 1, 1), (2, 0, 0), (2, 0, 1), (2, 1, 0), (2, 1, 1), (3, 1, 1)],
        [(3, 1, 1), (2, 1, 1), (2, 1, 0), (2, 0, 1), (2, 0, 0), (1, 1, 1), (1, 1, 0), (1, 0, 1), (1, 0, 0), (0, 0, 0)],
        [(0, 0, 0), (0, 1, 0), (0, 1, 1), (1, 1, 0), (1, 1, 1), (0, 2, 0), (0, 2, 1), (1, 2, 0), (1, 2, 1), (1, 3, 1)],
        [(1, 3, 1), (1, 2, 1), (1, 2, 0), (0, 2, 1), (0, 2, 0), (1, 1, 1), (1, 1, 0), (0, 1, 1), (0, 1, 0), (0, 0, 0)],
        [(0, 0, 0), (0, 0, 1), (0, 1, 1), (1, 0, 1), (1, 1, 1), (0, 0, 2), (0, 1, 2), (1, 0, 2), (1, 1, 2), (1, 1, 3)],
        [(1, 1, 3), (1, 1, 2), (1, 0, 2), (0, 1, 2), (0, 0, 2), (1, 1, 1), (1, 0, 1), (0, 1, 1), (0, 0, 1), (0, 0, 0)]
    ]
    actual = [fire_line_full(*coords) for coords in suite]
    for i, e in enumerate(expected):
        assert actual[i] == e

