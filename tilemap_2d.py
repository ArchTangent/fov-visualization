# Tilemap and Tiles for 2D FOV

from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional
from structures_2d import Structure
import json

@dataclass
class TileId:
    __slots__ = ["val"]
    val: int

    def to_point(self, xdims: int):
        """Converts a tile ID into a 2D point based on tilemap's X dimensions."""
        y = self.val // xdims
        x = self.val % xdims
    
        return Point2d(x, y)

    def in_bounds(self, num_tiles) -> bool:
        """Returns `True` if Tile ID is a valid index in the tilemap.
        
        Note: this doesn't necessarily mean that the index is within the (x,y)
        bounds of the tilemap.  
        
        Ex: (-1,5) in a 10x10 tilemap would be TileId(49),
        which is a valid index, but *not* within the (x,y) bounds.
        """
        return -1 < self.val < num_tiles


@dataclass
class Point2d:
    __slots__ = ["x", "y"]
    x: int
    y: int

    def to_tile_id(self, xdims: int):
        """Converts a 2D point into a tile ID based on tilemap's X dimensions."""
        return TileId(self.x + self.y * xdims)

    def in_bounds(self, xdims, ydims) -> bool:
        """Returns `True` if point is in bounds based on tilemap's dimensions."""
        return self.x > -1 and self.x < xdims and self.y > -1 and self.y < ydims

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
        self, xdims: int, ydims: int, tiles: Optional[Dict[Tuple, List]]
    ) -> None:
        """Builds map from {(x,y):[struct, n_wall, s_wall, e_wall, w_wall]} data."""
        self.xdims = xdims
        self.ydims = ydims
        self.tiles: List[Tile] = []
        # TODO: error check tiles in bounds

    @staticmethod
    def from_json(data: str):
        """Create a tilemap from (JSON) string of tilemap data.
        
        Keys:
        - "dims": (x,y) dimensions.
        - "tiles": {(x,y): [struct, n_wall, s_wall, e_wall, w_wall]} tile data.
        """
        json_dict = json.loads(data)

        if not map_data_valid(json_dict):
            return Tilemap2d(10, 10, None)

        xdims, ydims = json_dict["dims"]
        tiles = json_dict["tiles"]

        return Tilemap2d(xdims, ydims, tiles)

    @staticmethod
    def empty(xdims: int, ydims: int):
        return Tilemap2d(xdims, ydims, None)


def map_data_valid(json_dict: Dict) -> bool:
    """Returns `True` if map data is in {(int, int): [int, int, int, int] format."""
    valid = True

    dims = json_dict.get("dims", None)
    if not dims:
        print(f"ERROR: Missing JSON dimension data! Expected (int, int)")
        return False
    if not valid_2d_coords(dims):
        print(f"ERROR: Malformed JSON dimension data! Expected (int, int)")
        return False

    tiles = json_dict.get("tiles", {})
    for coords, tile_data in tiles:
        if not valid_2d_coords(coords):
            print(f"ERROR: Malformed JSON coordinate data! Expected (int, int)")
            return False
        if not valid_tile_data(tile_data):
            print(f"ERROR: Malformed JSON tile data! Expected [int, int, int, int int]")
            return False

    return valid

def valid_2d_coords(value: Tuple) -> bool:
    """Returns True if value is an (int, int) 2-tuple.  Does not check bounds."""
    return (
        type(value) == tuple and len(value) == 2 and 
        type(value[0]) == int and type(value[1]) == int
    )

def valid_tile_data(value: List) -> bool:
    """Returns True if value is a [int, int, int, int, int] list."""
    return (
        type(value) == list and len(value) == 5 and 
        type(value[0]) == int and type(value[1]) == int and
        type(value[2]) == int and type(value[3]) == int and
        type(value[4]) == int
    )


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

def test_point_in_bounds():
    xdims, ydims = (10, 10)
    suite = [
        (-1,5), (5,-1), (10,5), (5,10), (20,0), 
        (0,0), (1,0), (0,1), (9,1), (1,9)
    ]
    results = [
        False, False, False, False, False,
        True, True, True, True, True 
    ]
    for xy, expected in zip(suite, results):
        point = Point2d(*xy)
        assert point.in_bounds(xdims, ydims) == expected

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
        
def test_tile_in_bounds():
    xdims, ydims = (10, 10)
    num_tiles = xdims * ydims
    suite = [
        -11, -10, -1, 100, 101,
        0, 5, 50, 75, 99 
    ]
    results = [
        False, False, False, False, False,
        True, True, True, True, True 
    ]
    for tile_ix, expected in zip(suite, results):
        tile_id = TileId(tile_ix)
        assert tile_id.in_bounds(num_tiles) == expected        

if __name__ == "__main__":
    print("-----  Tilemap 2D -----\n")

    point = Point2d(0, 0)
    tile = point.to_tile_id(10)
    expected = TileId(0)
    print(f"tile ({tile}) = expected ({expected})? {tile == expected}")
    
