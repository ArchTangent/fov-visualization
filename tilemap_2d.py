# Tilemap and Tiles for 2D FOV

# from __future__ import annotations
from dataclasses import dataclass
from collections import namedtuple
from typing import List, Dict, Tuple, Optional

@dataclass
class TileId:
    __slots__ = ["val"]
    val: int

    def to_point(self, xdims: int):
        """Converts a tile ID into a 2D point based on tilemap's X dimensions."""
        y = self.val // xdims
        x = self.val % xdims
    
        return Point2d(x, y)

@dataclass
class Point2d:
    __slots__ = ["x", "y"]
    x: int
    y: int

    def to_tile_id(self, xdims: int):
        """Converts a 2D point into a tile ID based on tilemap's X dimensions."""
        return TileId(self.x + self.y * xdims)

@dataclass
class Tile:
    __slots__ = ["structure", "n_wall", "s_wall", "e_wall", "w_wall"]
    structure: int
    n_wall: int
    s_wall: int
    e_wall: int
    w_wall: int


class Tilemap2d:
    def __init__(
        self, xdims: int, ydims: int, structures: Optional[Dict[Tuple[int, int], int]]
    ) -> None:
        self.xdims = xdims
        self.ydims = ydims
        self.tiles: List[Tile] = []


class TilemapBuilder2d:
    @staticmethod
    def empty(xdims, ydims) -> Tilemap2d:
        return Tilemap2d(xdims, ydims, None)


def test_point_to_tile():
    """Note: conversion does *not* check for out-of-bounds points."""
    suite = [
        (10, (0, 0), 0),
        (10, (5, 0), 5),
        (10, (9, 0), 9),
        (10, (0, 1), 10),
        (10, (5, 1), 15),
        (10, (9, 1), 19),
        (10, (0, 2), 20),
    ]
    for xdims, coords, expected in suite:
        point = Point2d(*coords)
        tile_id = point.to_tile_id(xdims)

        assert tile_id == TileId(expected)

def test_tile_to_point():
    """Note: conversion does *not* check for out-of-bounds tiles."""
    suite = [
        (10, (0, 0), 0),
        (10, (5, 0), 5),
        (10, (9, 0), 9),
        (10, (0, 1), 10),
        (10, (5, 1), 15),
        (10, (9, 1), 19),
        (10, (0, 2), 20),
    ]
    for xdims, expected, tid in suite:
        tile_id = TileId(tid)
        point = tile_id.to_point(xdims)

        assert point == Point2d(*expected)

if __name__ == "__main__":
    print("-----  Tilemap 2D -----\n")

    point = Point2d(0, 0)
    tile = point.to_tile_id(10)
    expected = TileId(0)
    print(f"tile ({tile}) = expected ({expected})? {tile == expected}")
    
