# Objects and helpers for 2D FOV
# See:  map_functions.py

from tilemap_2d import Point2d

def chessboard_distance(p1: Point2d, p2: Point2d) -> int:
    """Return the chessboard (king's move) distance between two 2D points."""
    dx = p2.x - p1.x
    dy = p2.y - p1.y

    return max(abs(dx), abs(dy))

def orthogonal_distance(p1: Point2d, p2: Point2d) -> int:
    """Return the orthogonal (NSEW) distance between two 2D points."""
    dx = p2.x - p1.x
    dy = p2.y - p1.y

    return abs(dx) + abs(dy)

def test_chessboard_distance():
    suite = [
        ((0, 0), (0, 0), 0),
        ((0, 0), (0, 1), 1),
        ((0, 0), (1, 0), 1),
        ((0, 0), (0, -1), 1),
        ((0, 0), (-1, 0), 1),
        ((0, 1), (0, 0), 1),
        ((1, 0), (0, 0), 1),
        ((0, -1), (0, 0), 1),
        ((-1, 0), (0, 0), 1),
        ((-1, 0), (0, -1), 1),
        ((0, -1), (-1, 0), 1),
        ((0, 0), (1, 1), 1),
        ((0, 0), (-1, -1), 1),
        ((-1, -1), (1, 1), 2),
        ((1, 1), (-1, -1), 2),
        ((0, 1), (0, -1), 2),
        ((1, 0), (-1, 0), 2),
    ]
    for c1, c2, expected in suite:
        p1 = Point2d(c1[0], c1[1])
        p2 = Point2d(c2[0], c2[1])
        assert chessboard_distance(p1, p2) == expected

def test_orthogonal_distance():
    suite = [
        ((0, 0), (0, 0), 0),
        ((0, 0), (0, 1), 1),
        ((0, 0), (1, 0), 1),
        ((0, 1), (0, 0), 1),
        ((1, 0), (0, 0), 1),
        ((0, -1), (0, 0), 1),
        ((0, 0), (0, -1), 1),
        ((-1, 0), (0, 0), 1),
        ((0, 0), (-1, 0), 1),
        ((-1, 0), (0, -1), 2),
        ((0, -1), (-1, 0), 2),
        ((0, 0), (1, 1), 2),
        ((0, 0), (-1, -1), 2),
        ((-1, -1), (1, 1), 4),
        ((1, 1), (-1, -1), 4),
        ((0, 1), (0, -1), 2),
        ((1, 0), (-1, 0), 2),
    ]
    for c1, c2, expected in suite:
        p1 = Point2d(c1[0], c1[1])
        p2 = Point2d(c2[0], c2[1])
        assert orthogonal_distance(p1, p2) == expected
