# Tilemap and Tiles for 2D FOV

from dataclasses import dataclass
from collections import namedtuple
from typing import List, Dict, Tuple, Optional

# NOTE: can have NSEW walls in any tile
# TODO: tilemaps need: xdims, ydims, structures (dict of {coords2d:structure_id} )
# TODO: add_structure(), remove_structure()

@dataclass
class Point2d:
    __slots__ = ["x", "y"]
    x: int
    y: int

@dataclass
class Tile2d:
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
        self.tiles: List[Tile2d] = []


class TilemapBuilder2d:
    @staticmethod
    def empty(xdims, ydims) -> Tilemap2d:
        return Tilemap2d(xdims, ydims, None)


if __name__ == "__main__":
    print("-----  Tilemap 2D -----\n")
    
