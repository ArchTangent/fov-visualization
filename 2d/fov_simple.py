"""2D FOV Visualization - Simple Method.

Key Ideas:
- Tiles either `block_sight` completely (over their entire span), or do not.
- FOV is divided into 8 parts called octants (not to be confused with geometric term).
- FOV angle ranges are quantized into 64, 128, or 256 subdivisions.
- It is ~10x faster to use pre-calculated values (in `FovTile`s). See `benchmarks` for more.
"""
import math
import pygame, pygame.freetype
from pygame.display import update
from pygame import Vector2
from pygame.color import Color
from pygame.freetype import Font
from pygame.surface import Surface
from helpers_2d import to_coords, to_tile_id, Octant, QBits, octant_transform, pri_sec_to_relative
from typing import List, Dict, Optional, Tuple

class Unit:
    """Player to be rendered on the FOV map."""

    def __init__(self, x: int, y: int, radius: int) -> None:
        self.pos = Vector2(float(x), float(y))
        self.x = x
        self.y = y
        self.radius = radius


class TileMap:
    """2D tilemap, taking a dictionary of blocked (x,y) coordinates."""

    def __init__(self, xdims: int, ydims: int, blocked: set[Tuple[int, int]]):
        self.xdims = xdims
        self.ydims = ydims
        self.tiles = [
            [
                Tile(
                    to_tile_id(x, y, xdims),
                    x,
                    y,
                    (x, y) in blocked,
                )
                for x in range(xdims)
            ]
            for y in range(ydims)
        ]

    def tile_at(self, x: int, y: int):
        """Gets Tile at given location"""
        return self.tiles[y][x]

    def tile_ix(self, x: int, y: int):
        """Gets Tile ID at given location"""
        return self.tiles[y][x].tid


class Tile:
    """2D Tile."""

    def __init__(self, tid: int, x: int, y: int, blocked: bool):
        self.tid = tid
        self.x = x
        self.y = y
        self.blocks_path = blocked
        self.blocks_sight = blocked

    def __repr__(self) -> str:
        return f"C{self.tid}({self.x},{self.y})"

    def to_coords(self) -> Tuple[int, int]:
        return (self.x, self.y)


class TileSummary:
    """Summarizes key values for a tile at relative (x,y) values to observer."""

    def __init__(self, rx: int, ry: int) -> None:
        self.rx, self.ry = rx, ry
        self.slopes = slopes_by_relative_coords(rx, ry)
        self.q_block = quantized_slopes_wide(self.slopes[0], self.slopes[1], QBits.Q64)
        self.q_vis = quantized_slopes_narrow(self.slopes[0], self.slopes[1], QBits.Q64)

    def __repr__(self) -> str:
        return f"({self.ry},{self.rx}): {self.slopes}, block: {self.q_block}, vis: {self.q_vis}"


class FovMap2D:
    """2D FOV map of FovTiles used with TileMap to determine visible tiles."""

    def __init__(self, radius: int) -> None:
        if radius < 2:
            raise ValueError("Use max FOV radius of 2 or higher!")
        self.octant_1 = FovOctant2D(radius, Octant.O1)
        self.octant_2 = FovOctant2D(radius, Octant.O2)
        self.octant_3 = FovOctant2D(radius, Octant.O3)
        self.octant_4 = FovOctant2D(radius, Octant.O4)
        self.octant_5 = FovOctant2D(radius, Octant.O5)
        self.octant_6 = FovOctant2D(radius, Octant.O6)
        self.octant_7 = FovOctant2D(radius, Octant.O7)
        self.octant_8 = FovOctant2D(radius, Octant.O8)


class FovOctant2D:
    """2D FOV Octant with TileMap coordinate translations and blocking bits.

    `radius`: int
        Maximum in-game FOV radius.
    `octant`: Octant
        One of 8 Octants represented by this instance.
    """

    def __init__(self, radius: int, octant: Octant):
        self.tiles: List[FovTile] = []
        slice_threshold = 2
        tix = 1

        for dpri in range(1, radius):
            for dsec in range(slice_threshold):
                tile = FovTile(tix, dpri, dsec, octant)
                self.tiles.append(tile)
                tix += 1
            slice_threshold += 1

if __name__ == "__main__":
    print("\n=====  2D FOV Simple  =====\n")

