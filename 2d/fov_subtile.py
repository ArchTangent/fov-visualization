"""2D FOV Visualization - Subtile Method. 

Key Ideas:
- Tiles are broken up into subgrids of (x*x) subtiles, e.g. 4x4 = 16 subtiles.
- As # of subtiles go up, FOV granularity and generation time go up. 4 is a good value.
- FOV is divided into 8 parts called octants (not to be confused with geometric term).
- Uses bresenham lines comprised of subtiles to determine which tile are visible.
- There are 64FOV angle ranges are quantized into 64, 128, or 256 subdivisions.
"""
import math
import pygame, pygame.freetype
from pygame import Vector2
from pygame.color import Color
from pygame.freetype import Font
from pygame.surface import Surface
from helpers import (
    Coords,
    FovLineType,
    Octant,
    boundary_radii,
    max_fovtile_index,
    octant_transform,
    pri_sec_to_relative,
    to_tile_id,
)
from lines import bresenham, bresenham_full
from typing import List, Dict, Set, Tuple


class Settings:
    """Settings for Pygame."""

    def __init__(
        self,
        width: int,
        height: int,
        map_dims: Coords,
        tile_size: int,
        line_width: int,
        subtiles_xy: int,
        font: Font,
        font_color: Color,
        fov_radius: int=63,
        fov_line_type: FovLineType=FovLineType.NORMAL,
        floor_color="steelblue2",
        floor_trim_color="steelblue4",
        fov_line_color="slateblue1",
        fov_line_trim_color="slateblue3",
        wall_color="seagreen3",
        wall_trim_color="seagreen4",
        structure_color="seagreen3",
        structure_trim_color="seagreen4",
        unseen_color="gray15",
        draw_tid: bool = False,
    ) -> None:
        self.width = width
        self.height = height
        self.map_dims = map_dims
        self.tile_size = tile_size
        self.line_width = line_width
        self.subtiles_xy = subtiles_xy
        self.subtile_size = tile_size // subtiles_xy
        self.font = font
        self.font_color = font_color
        self.fov_radius = fov_radius
        self.fov_line_type = fov_line_type
        self.floor_color = Color(floor_color)
        self.fov_line_color = fov_line_color
        self.fov_line_trim_color = fov_line_trim_color
        self.floor_trim_color = Color(floor_trim_color)
        self.wall_color = Color(wall_color)
        self.wall_trim_color = Color(wall_trim_color)
        self.structure_color = Color(structure_color)
        self.structure_trim_color = Color(structure_trim_color)
        self.unseen_color = Color(unseen_color)
        self.draw_tid = draw_tid
        self.xdims, self.ydims = map_dims.x, map_dims.y


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


class TileMap:
    """2D tilemap, taking a dictionary of blocked (x,y) coordinates.

    NOTE: direct access to Tilemap.tiles uses [y][x] order. Use `tile_at(x,y)` instead.
    """

    def __init__(
        self,
        blocked: Dict[Tuple[int, int], Blockers],
        settings: Settings,
    ):
        ts = settings.tile_size
        xdims, ydims = settings.xdims, settings.ydims
        self.xdims = xdims
        self.ydims = ydims
        self.tiles = [
            [
                Tile(
                    to_tile_id(x, y, xdims),
                    Coords(x, y),
                    ts,
                    blocked.get((x, y), Blockers()),
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

    def show(self):
        for row in self.tiles:
            tile_row = [f"{t}" for t in row]
            print(" ".join(tile_row))


class Tile:
    """2D Tile."""

    def __init__(self, tid: int, coords: Coords, ts: int, blockers: Blockers):
        self.tid = tid
        self.x = coords.x
        self.y = coords.y
        # Reference point on the map for drawing
        self.p1 = Vector2(coords.x * ts, coords.y * ts)
        self.structure = blockers.structure
        self.wall_n = blockers.wall_n
        self.wall_w = blockers.wall_w

    def __repr__(self) -> str:
        return f"C{self.tid}({self.x},{self.y})"

    def to_coords(self) -> Tuple[int, int]:
        return (self.x, self.y)


def get_tile_at_cursor(mx: int, my: int, dims: Coords, tile_size: int) -> Coords:
    """Gets the coordinates of the Tile at the mouse cursor position."""
    xdims, ydims = dims
    tx = math.floor(mx / tile_size)
    ty = math.floor(my / tile_size)
    return Coords(tx, ty)


class FovMap:
    """2D FOV map of FovTiles used with TileMap to determine visible tiles.
    
    `radius`: int
        Maximum in-game FOV radius. 63 is a good choice.
    `subtiles`: int
        Number of subtilesMaximum in-game FOV radius.
    `fov_line_type`: FovLineType
        Determines whether bresenham() or bresenham_full() lines are used.
    """

    def __init__(self, radius: int, subtiles: int, fov_line_type: FovLineType) -> None:
        if radius < 2:
            raise ValueError("Use max FOV radius of 2 or higher!")
        self.octant_1 = FovOctant(radius, subtiles, Octant.O1, fov_line_type)
        self.octant_2 = FovOctant(radius, subtiles, Octant.O2, fov_line_type)
        self.octant_3 = FovOctant(radius, subtiles, Octant.O3, fov_line_type)
        self.octant_4 = FovOctant(radius, subtiles, Octant.O4, fov_line_type)
        self.octant_5 = FovOctant(radius, subtiles, Octant.O5, fov_line_type)
        self.octant_6 = FovOctant(radius, subtiles, Octant.O6, fov_line_type)
        self.octant_7 = FovOctant(radius, subtiles, Octant.O7, fov_line_type)
        self.octant_8 = FovOctant(radius, subtiles, Octant.O8, fov_line_type)


class FovOctant:
    """2D FOV Octant with TileMap coordinate translations and blocking bits.

    This version includes the observer's own tile (radius 0) due to walls.

    `radius`: int
        Maximum in-game FOV radius, also granularity. 63 is a good choice.
    `subtiles`: int
        Number of subtilesMaximum in-game FOV radius.
    `octant`: Octant
        One of 8 Octants represented by this instance.
    """

    def __init__(self, radius: int, subtiles: int, octant: Octant, fov_line_type: FovLineType):
        self.tiles: List[FovTile] = []
        slice_threshold = 1
        tix = 0

        fov_lines = FovLines(radius, subtiles, octant, fov_line_type)

        for dpri in range(radius + 1):
            for dsec in range(slice_threshold):
                tile = FovTile(tix, dpri, dsec, subtiles, octant, fov_lines)
                self.tiles.append(tile)
                tix += 1
            slice_threshold += 1


class FovLines:
    """Sets of coordinates for each FOV line in range [0, radius].
    
    There is one FOV bit / FOV index for each FOV line (radius + 1). If the
    radius is 63, there are 64 FOV bits, one bit for each FOV line.
    """

    def __init__(self, radius: int, subtiles_xy: int, octant: Octant, fov_line_type: FovLineType) -> None:
        line_func = bresenham if fov_line_type == FovLineType.NORMAL else bresenham_full
        start = subtiles_xy // 2
        pri = start + subtiles_xy * radius
        src = octant_transform(start, start, Octant.O1, octant)
        self.lines: List[Set[Tuple[int, int]]] = []

        for r in range(radius + 1):
            sec = start + r * subtiles_xy
            tgt = octant_transform(pri, sec, Octant.O1, octant)
            line_list = {c for c in  line_func(*src, *tgt)}
            self.lines.append(line_list)
            

class FovTile:
    """2D FOV Tile used in an `FovOctant`.

    An FOV tile is visible if at least one of its `visible_bits` is not blocked
    by `blocked` bits in the FOV calculation.

    `tix`: int
        Tile index within the Octant and list of FOV tiles.
    `dpri, dsec`: int
        Relative (pri,sec) coordinates of the FOV tile compared to FOV origin.
    `subtiles_xy`: int
        Number of subtiles on x and y axes. If 8, there are (8x8 = 64) subtiles per tile.
    `visible_bits`: u64
        Bitflags spanning the visible Δsec/Δpri FIV lines for the tile.
    `blocking_bits`: u64
        Bitflags spanning the Δsec/Δpri FOV lines blocked by the tile (if wall present).
    `ref_x`, `ref_y`: int 
        Reference subtiles (upper left) used for wall and structure placement within a tile.
    `fov_lines`: FovLines
        Grouping of FOV lines for the given octant, used to get blocking and visible bits.
    """
    __slots__ = "wall_n_bits", "wall_w_bits", "structure_bits", "visible_bits", "ref_x", "ref_y", "rx", "ry", "dsec", "tix"

    def __init__(self, tix: int, dpri: int, dsec: int, subtiles_xy: int, octant: Octant, fov_lines: FovLines):
        # Octant-adjusted relative x/y used to select tile in TileMap
        # dsec is needed for slice filter and bounds checks in FOV calc
        rx, ry = pri_sec_to_relative(dpri, dsec, octant)
        self.rx, self.ry = int(rx), int(ry)
        self.dsec = dsec
        self.tix = tix

        ref_x, ref_y = self.reference_coords(rx, ry, subtiles_xy, octant)
    
        wall_tiles_n = self.wall_n_subtiles(subtiles_xy, ref_x, ref_y)
        wall_tiles_w = self.wall_w_subtiles(subtiles_xy, ref_x, ref_y)
        structure_tiles = self.structure_subtiles(subtiles_xy, ref_x, ref_y)

        self.wall_n_bits: int = 0
        self.wall_w_bits: int = 0
        self.structure_bits: int = 0
        self.visible_bits: int = 0

        # Set blocking and visible bits from walls and structures
        # Structure subtiles are used for structures and tile visibility
        for ix, fov_line in enumerate(fov_lines.lines):
            bit_ix = 1 << ix

            if wall_tiles_n.intersection(fov_line):
                self.wall_n_bits |= bit_ix

            if wall_tiles_w.intersection(fov_line):
                self.wall_w_bits |= bit_ix

            if structure_tiles.intersection(fov_line):
                self.structure_bits |= bit_ix
                self.visible_bits |= bit_ix


    def __repr__(self) -> str:
        return f"FovTile {self.tix} rel: ({self.rx},{self.ry}), ref: {self.ref_x, self.ref_y}, wall N/W: {bin(self.wall_n_bits)}/{bin(self.wall_w_bits)}"
       
    def reference_coords(self, rx: int, ry: int, subtiles_xy: int, octant: Octant) -> Tuple[int, int]:
        """Get (x,y) subtile reference coordinates based on octant, relative to origin.
        
        FovLines use real coordinates WRT (0,0) origin. Octant 1 uses (+,+), 
        Octant 5 uses (-,-) values.

        In Octant 2 at pri, sec of (1, 0), reference (x,y) should have (rx, ry) of (0, 1)
        and a (ref_x, ref_y) of
        """
        bx, by = rx * subtiles_xy, ry * subtiles_xy

        match octant:
            case Octant.O1 | Octant.O2:
                ref_x, ref_y = bx, by
            case Octant.O3 | Octant.O4:
                ref_x, ref_y = bx - subtiles_xy + 1, by
            case Octant.O5 | Octant.O6:
                ref_x, ref_y = bx - subtiles_xy + 1, by - subtiles_xy + 1
            case Octant.O7 | Octant.O8:
                ref_x, ref_y = bx, by - subtiles_xy + 1
        
        return ref_x, ref_y

    def wall_n_subtiles(self, subtiles: int, ref_x: int, ref_y: int) -> Set[Tuple[int, int]]:
        """Returns North wall subtiles in the Tile as (x,y) coordinates."""
        result = {*bresenham(ref_x, ref_y, ref_x + subtiles - 1, ref_y)}
        return result

    def wall_w_subtiles(self, subtiles: int, ref_x: int, ref_y: int) -> Set[Tuple[int, int]]:
        """Returns West wall subtiles in the Tile as (x,y) coordinates."""
        result = {*bresenham(ref_x, ref_y, ref_x, ref_y + subtiles - 1)}
        return result

    def structure_subtiles(self, subtiles: int, ref_x: int, ref_y: int) -> Set[Tuple[int, int]]:
        """Returns Structure subtiles in the Tile as (x,y) coordinates."""
        result = set()
        for y in range(ref_y, ref_y + subtiles):
            line = bresenham(ref_x, y, ref_x + subtiles - 1, y)
            result.update(line)
        
        return result

#   #######   #######      ##     ##    ##
#   ##    ##  ##    ##   ##  ##   ##    ##
#   ##    ##  #######   ##    ##  ## ## ##
#   ##    ##  ##   ##   ########  ###  ###
#   #######   ##    ##  ##    ##   ##  ##

def draw_tile(screen: Surface, tile: Tile, visible_bits: int, settings: Settings):
    """Renders a visible 3D Tile on the map.
    
    `draw_bits` indicate which objects to draw (e.g. 0b010):
    - 0th bit is the tile (and structure)
    - 1st bit is the North wall
    - 2nd bit is the West wall
    """
    p1 = tile.p1
    p1x, p1y = tile.p1
    s = settings
    w = s.line_width
    ts = s.tile_size
    sts = s.subtile_size
    trim_color = settings.floor_trim_color

    tile_bit = visible_bits & 0b001
    wall_n_bit = visible_bits & 0b010
    wall_w_bit = visible_bits & 0b100

    # Draw Tile (if not blocked by walls), and structure (if present)
    if tile_bit:
        # Draw subgrid
        for dx in range(1, settings.subtiles_xy):
            x1 = p1x + dx * sts
            y1 = p1y
            x2 = p1x + dx * sts
            y2 = p1y + ts
            pygame.draw.line(screen, trim_color, (x1, y1), (x2, y2))

        for dy in range(1, settings.subtiles_xy):
            x1 = p1x
            y1 = p1y + dy * sts
            x2 = p1x + ts
            y2 = p1y + dy * sts
            pygame.draw.line(screen, trim_color, (x1, y1), (x2, y2))

        draw_floor(screen, p1, ts, w, s.floor_color, s.floor_trim_color)

        if tile.structure:
            draw_structure(
                screen, p1, ts, w, s.structure_color, s.structure_trim_color
            )

    # Draw N wall (if present)
    if wall_n_bit:
        draw_north_wall(screen, p1, ts, sts, w, s.wall_color, s.wall_trim_color)
    # Draw W wall (if present)
    if wall_w_bit:
        draw_west_wall(screen, p1, ts, sts, w, s.wall_color, s.wall_trim_color)


def draw_unseen_tile(screen: Surface, pr: Vector2, settings: Settings):
    """Renders an unseen tile on the map."""
    s = settings
    w = s.line_width
    color = s.unseen_color
    trim = s.unseen_color
    ts = s.tile_size

    p1 = Vector2(pr.x, pr.y)
    p2 = Vector2(pr.x + ts, pr.y)
    p3 = Vector2(pr.x + ts, pr.y + ts)
    p4 = Vector2(pr.x, pr.y + ts)

    pygame.draw.polygon(screen, color, [p1, p2, p3, p4])
    pygame.draw.lines(screen, trim, True, [p1, p2, p3, p4], width=w)


def draw_fov_line(screen: Surface, tx: int, ty: int, settings: Settings):
    """Draws a 2D FOV line from (0,0) to tile at mouse cursor (tx, ty)."""
    tiles = bresenham_full(0, 0, tx, ty)

    ts = settings.tile_size
    color = Color(settings.fov_line_color)
    trim = Color(settings.fov_line_trim_color)
    for fx, fy in tiles:
        draw_fov_tile(screen, Vector2(fx * ts, fy * ts), ts, color, trim)


def draw_fov_line_subpixel(screen: Surface, tx: int, ty: int, settings: Settings):
    """Draws a subpixel 2D FOV line from (0,0) to tile at mouse cursor (tx, ty)."""
    sp = settings.subtiles_xy
    half_sp = sp // 2
    sts = settings.subtile_size
    # Origin / target pixels vary based on FOV height and octant
    ox = half_sp
    oy = half_sp
    fx = tx * sp + half_sp
    fy = ty * sp + half_sp
    
    if settings.fov_line_type == FovLineType.NORMAL:
        tiles = bresenham(ox, oy, fx, fy)
    else:
        tiles = bresenham_full(ox, oy, fx, fy)

    color = Color(settings.fov_line_color)
    trim = Color(settings.fov_line_trim_color)

    for fx, fy in tiles:
        draw_fov_tile(screen, Vector2(fx * sts, fy * sts), sts, color, trim)


def draw_fov_tile(screen: Surface, pr: Vector2, ts: int, color: Color, trim: Color):
    """Draws an FOV tile with reference point `pr` and tile size `ts`."""

    p1 = Vector2(pr.x, pr.y)
    p2 = Vector2(pr.x + ts, pr.y)
    p3 = Vector2(pr.x + ts, pr.y + ts)
    p4 = Vector2(pr.x, pr.y + ts)

    pygame.draw.polygon(screen, color, [p1, p2, p3, p4])
    pygame.draw.lines(screen, trim, True, [p1, p2, p3, p4])


def draw_floor(
    screen: Surface, pr: Vector2, ts: int, width: int, color: Color, trim: Color
):
    """Draws a floor tile with reference point `pr` and tile size `ts`."""
    p1 = Vector2(pr.x, pr.y)
    p2 = Vector2(pr.x + ts, pr.y)
    p3 = Vector2(pr.x + ts, pr.y + ts)
    p4 = Vector2(pr.x, pr.y + ts)

    # pygame.draw.polygon(screen, color, [p1, p2, p3, p4])
    # pygame.draw.lines(screen, trim, True, [p1, p2, p3, p4], width=width)
    pygame.draw.lines(screen, color, True, [p1, p2, p3, p4], width=2)


def draw_north_wall(
    screen: Surface, pr: Vector2, ts: int, sts: int, width: int, color: Color, trim: Color
):
    """Draws a north wall w/reference `pr`, tile size `ts`, and subtile size `sts`."""
    p1 = Vector2(pr.x, pr.y)
    p2 = Vector2(pr.x + ts, pr.y)
    p3 = Vector2(pr.x + ts, pr.y + sts)
    p4 = Vector2(pr.x, pr.y + sts)

    pygame.draw.polygon(screen, color, [p1, p2, p3, p4])
    pygame.draw.lines(screen, trim, True, [p1, p2, p3, p4], width=width)


def draw_west_wall(
    screen: Surface, pr: Vector2, ts: int, sts: int, width: int, color: Color, trim: Color
):
    """Draws a north wall w/reference `pr`, tile size `ts`, and subtile size `sts`."""
    p1 = Vector2(pr.x, pr.y)
    p2 = Vector2(pr.x + sts, pr.y)
    p3 = Vector2(pr.x + sts, pr.y + ts)
    p4 = Vector2(pr.x, pr.y + ts)

    pygame.draw.polygon(screen, color, [p1, p2, p3, p4])
    pygame.draw.lines(screen, trim, True, [p1, p2, p3, p4], width=width)


def draw_structure(
    screen: Surface, pr: Vector2, ts: int, width: int, color: Color, trim: Color
):
    """Draws a structure in a tile with reference point `pr` and tile size `ts`."""
    p1 = Vector2(pr.x, pr.y)
    p2 = Vector2(pr.x + ts, pr.y)
    p3 = Vector2(pr.x + ts, pr.y + ts)
    p4 = Vector2(pr.x, pr.y + ts)

    pygame.draw.polygon(screen, color, [p1, p2, p3, p4])
    pygame.draw.lines(screen, trim, True, [p1, p2, p3, p4], width=width)


def draw_subgrid(screen: Surface, settings: Settings):
    """Draws subtiles on base of tilemap according to dimensions."""
    color = settings.floor_trim_color
    ts = settings.tile_size
    sts = settings.tile_size / settings.subtiles_xy
    xdims, ydims = settings.xdims, settings.ydims

    for dx in range(1, xdims * settings.subtiles_xy):
        x1 = dx * sts
        y1 = 0
        x2 = dx * sts
        y2 = ydims * ts
        pygame.draw.line(screen, color, (x1, y1), (x2, y2))

    for dy in range(1, ydims * settings.subtiles_xy):
        x1 = 0
        y1 = dy * sts
        x2 = xdims * ts
        y2 = dy * sts
        pygame.draw.line(screen, color, (x1, y1), (x2, y2))


def draw_map(
    screen: Surface,
    tilemap: TileMap,
    visible_tiles: Dict[Tuple[int, int], int],
    settings: Settings
):
    """Renders the Tilemap, accounting for FOV."""
    # Row is y; col is x
    for ty, row_data in enumerate(tilemap.tiles):
        for tx, tile in enumerate(row_data):
            visible_bits = visible_tiles.get((tx, ty))
            if visible_bits:
                draw_tile(screen, tile, visible_bits, settings)


def draw_line_to_cursor(
    screen: Surface, mx: int, my: int, tile_mid: float, line_width: int
):
    """Draws a line from origin to mouse cursor.

    `mx, my`: int
        mouse cursor position.
    `tile_mid`: float
       `tile_size / 2`.
    """
    pygame.draw.line(
        screen,
        Color("red"),
        (tile_mid, tile_mid),
        (mx, my),
        line_width,
    )


def draw_tile_at_cursor(
    screen: Surface, tx: int, ty: int, settings: Settings, line=True
):
    """Draws border around Tile at cursor.  Also draws line if `line=True`."""
    ts = settings.tile_size
    tile_mid = ts * 0.5
    w = settings.line_width
    rx, ry = tx * ts, ty * ts

    if line:
        pygame.draw.line(
            screen,
            Color("red"),
            (tile_mid, tile_mid),
            (rx + tile_mid, ry + tile_mid),
            w,
        )

    pygame.draw.lines(
        screen,
        Color("yellow"),
        True,
        [(rx, ry), (rx + ts, ry), (rx + ts, ry + ts), (rx, ry + ts)],
    )


def draw_player(screen: Surface, player_img: Surface, px: int, py: int, tile_size: int):
    """Renders the player (always visible) on the Tilemap."""
    screen.blit(player_img, (px * tile_size, py * tile_size))


#   ########    ####    ##    ##
#   ##        ##    ##  ##    ##
#   ######    ##    ##  ##    ##
#   ##        ##    ##   ##  ##
#   ##         ######      ##  

def fov_calc(ox: int, oy: int, tilemap: TileMap, fov_map: FovMap, radius: int
) -> Dict[Tuple[int, int], int]:
    """Returns visible tiles (and substructures) from given origin (ox, oy).
    
   Notes:
    - check if tile is visible before applying blocking bits.
    - tiles can only add to blocked bits if they are visible.
    - the player's own tile is always visible.

    `ox`, `oy`: int
        Origin coordinates of the current Unit.
    `radius`: int
        Current unit's FOV radius.
    `draw_bits`: int
        Indicate which objects to draw (e.g. 0b010). 1st bit is the tile (and structure),
        2nd bit is the North wall, 3rd bit is the West wall
    """
    tm = tilemap
    origin = tm.tile_at(ox, oy)
    xdims, ydims = tm.xdims, tm.ydims
    visible_bits = 0b001
    if origin.wall_n:
        visible_bits |= 0b010
    if origin.wall_w:
        visible_bits |= 0b100
    visible_tiles = {(ox, oy): visible_bits}   # All tile structures visible in origin

    # --- Octants 1-2 --- #
    max_x, max_y = boundary_radii(ox, oy, xdims, ydims, Octant.O1, radius)

    vis1 = get_visible_tiles_12(ox, oy, max_x, max_y, tm, fov_map.octant_1.tiles)
    update_visible_tiles(visible_tiles, vis1)

    vis2 = get_visible_tiles_12(ox, oy, max_y, max_x, tm, fov_map.octant_2.tiles)
    update_visible_tiles(visible_tiles, vis2)

    # --- Octants 3-4 --- #
    max_x, max_y = boundary_radii(ox, oy, xdims, ydims, Octant.O4, radius)

    vis3 = get_visible_tiles_34(ox, oy, origin, max_y, max_x, tm, fov_map.octant_3.tiles)
    update_visible_tiles(visible_tiles, vis3)

    vis4 = get_visible_tiles_34(ox, oy, origin, max_x, max_y, tm, fov_map.octant_4.tiles)
    update_visible_tiles(visible_tiles, vis4)

    # --- Octants 5-6 --- #
    max_x, max_y = boundary_radii(ox, oy, xdims, ydims, Octant.O5, radius)

    vis5 = get_visible_tiles_56(ox, oy, origin, max_x, max_y, tm, fov_map.octant_5.tiles)
    update_visible_tiles(visible_tiles, vis5)

    vis6 = get_visible_tiles_56(ox, oy, origin, max_y, max_x, tm, fov_map.octant_6.tiles)
    update_visible_tiles(visible_tiles, vis6)

    # --- Octants 7-8 --- #
    max_x, max_y = boundary_radii(ox, oy, xdims, ydims, Octant.O8, radius)

    vis7 = get_visible_tiles_78(ox, oy, origin, max_y, max_x, tm, fov_map.octant_7.tiles)
    update_visible_tiles(visible_tiles, vis7)

    vis8 = get_visible_tiles_78(ox, oy, origin, max_x, max_y, tm, fov_map.octant_8.tiles)
    update_visible_tiles(visible_tiles, vis8)

    return visible_tiles


def get_visible_tiles_12(
    ox: int,
    oy: int,
    max_pri: int,
    max_sec: int,
    tilemap: TileMap,
    fov_tiles: List[FovTile],
) -> List[Tuple[int, int, int]]:
    """Returns list of visible tiles and substructures in Octants 1 and 2.

    `visible_bits` uses three bitflags: 0b000 (West, North, Tile)
    """
    pri_ix, sec_ix = max_fovtile_index(max_pri) + 1, max_sec + 1
    blocked_bits: int = 0
    visible_tiles: List[Tuple[int, int, int]] = []

    for fov_tile in fov_tiles[1:pri_ix]:    
        if fov_tile.dsec < sec_ix and is_visible(fov_tile.visible_bits, blocked_bits):
            # For Octants 1 and 2, a tile may be blocked by its own N/W walls
            tx, ty = ox + fov_tile.rx, oy + fov_tile.ry
            tile = tilemap.tile_at(tx, ty)
            visible_bits = 0b000

            # NOTE: Check North wall before West
            if tile.wall_w and is_visible(fov_tile.wall_w_bits, blocked_bits):
                blocked_bits |= fov_tile.wall_w_bits
                visible_bits |= 0b100
            if tile.wall_n and is_visible(fov_tile.wall_n_bits, blocked_bits):
                blocked_bits |= fov_tile.wall_n_bits
                visible_bits |= 0b010

            # NOTE: 2nd visibility check after adding own walls
            if is_visible(fov_tile.visible_bits, blocked_bits):
                visible_bits |= 0b001
                if tile.structure:
                    blocked_bits |= fov_tile.structure_bits
        
            visible_tiles.append((tx, ty, visible_bits))

    return visible_tiles


def get_visible_tiles_34(
    ox: int,
    oy: int,
    origin: Tile,
    max_pri: int,
    max_sec: int,
    tilemap: TileMap,
    fov_tiles: List[FovTile],
) -> List[Tuple[int, int, int]]:
    """Returns list of visible tiles and substructures in Octants 3 and 4.

    `visible_bits` uses three bitflags: 0b000 (West, North, Tile)
    """
    pri_ix, sec_ix = max_fovtile_index(max_pri) + 1, max_sec + 1
    blocked_bits: int = 0
    visible_tiles: List[Tuple[int, int, int]] = []

    # Add West wall blocking bits for origin tile
    if origin.wall_w:
        blocked_bits |= fov_tiles[0].wall_w_bits

    for fov_tile in fov_tiles[1:pri_ix]:
        if fov_tile.dsec < sec_ix and is_visible(fov_tile.visible_bits, blocked_bits):
            # For Octants 3 and 4, a tile may be blocked by its own N wall
            tx, ty = ox + fov_tile.rx, oy + fov_tile.ry
            tile = tilemap.tile_at(tx, ty)
            visible_bits = 0b000

            if tile.wall_n and is_visible(fov_tile.wall_n_bits, blocked_bits):
                blocked_bits |= fov_tile.wall_n_bits
                visible_bits |= 0b010

            # NOTE: 2nd visibility check after adding own walls
            if is_visible(fov_tile.visible_bits, blocked_bits):
                visible_bits |= 0b001

                if tile.wall_w:
                    blocked_bits |= fov_tile.wall_w_bits
                    visible_bits |= 0b100
                if tile.structure:
                    blocked_bits |= fov_tile.structure_bits

            visible_tiles.append((tx, ty, visible_bits))

    return visible_tiles


def get_visible_tiles_56(
    ox: int,
    oy: int,
    origin: Tile,
    max_pri: int,
    max_sec: int,
    tilemap: TileMap,
    fov_tiles: List[FovTile],
) -> List[Tuple[int, int, int]]:
    """Returns list of visible tiles and substructures in Octants 5 and 6.

    `visible_bits` uses three bitflags: 0b000 (West, North, Tile)
    """
    pri_ix, sec_ix = max_fovtile_index(max_pri) + 1, max_sec + 1
    blocked_bits: int = 0
    visible_tiles: List[Tuple[int, int, int]] = []

    # Add North and West wall blocking bits for origin tile
    if origin.wall_n:
        blocked_bits |= fov_tiles[0].wall_n_bits
    if origin.wall_w:
        blocked_bits |= fov_tiles[0].wall_w_bits

    for fov_tile in fov_tiles[1:pri_ix]:    
        if fov_tile.dsec < sec_ix and is_visible(fov_tile.visible_bits, blocked_bits):
            # For Octants 5 and 6, tiles are not blocked by their own N/W walls
            tx, ty = ox + fov_tile.rx, oy + fov_tile.ry
            tile = tilemap.tile_at(tx, ty)
            visible_bits = 0b001

            if tile.structure:
                blocked_bits |= fov_tile.structure_bits
            if tile.wall_n:
                blocked_bits |= fov_tile.wall_n_bits
                visible_bits |= 0b010
            if tile.wall_w:
                blocked_bits |= fov_tile.wall_w_bits
                visible_bits |= 0b100

            visible_tiles.append((tx, ty, visible_bits))

    return visible_tiles


def get_visible_tiles_78(
    ox: int,
    oy: int,
    origin: Tile,
    max_pri: int,
    max_sec: int,
    tilemap: TileMap,
    fov_tiles: List[FovTile],
) -> List[Tuple[int, int, int]]:
    """Returns list of visible tiles and substructures in Octants 7 and 8.

    `visible_bits` uses three bitflags: 0b000 (West, North, Tile)
    """
    pri_ix, sec_ix = max_fovtile_index(max_pri) + 1, max_sec + 1
    blocked_bits: int = 0
    visible_tiles: List[Tuple[int, int, int]] = []

    # Add North wall blocking bits for origin tile
    if origin.wall_n:
        blocked_bits |= fov_tiles[0].wall_n_bits

    for fov_tile in fov_tiles[1:pri_ix]:
        if fov_tile.dsec < sec_ix and is_visible(fov_tile.visible_bits, blocked_bits):
            # For Octants 7 and 8, a tile may be blocked by its own W wall
            tx, ty = ox + fov_tile.rx, oy + fov_tile.ry
            tile = tilemap.tile_at(tx, ty)
            visible_bits = 0b000

            if tile.wall_w:
                blocked_bits |= fov_tile.wall_w_bits
                visible_bits |= 0b100

            # NOTE: 2nd visibility check after adding own walls
            if is_visible(fov_tile.visible_bits, blocked_bits):
                visible_bits |= 0b001

                if tile.wall_n:
                    blocked_bits |= fov_tile.wall_n_bits
                    visible_bits |= 0b010
                if tile.structure:
                    blocked_bits |= fov_tile.structure_bits
            
            visible_tiles.append((tx, ty, visible_bits))
            
    return visible_tiles


def is_visible(visible_bits: int, blocked_bits: int) -> bool:
    """Returns `True` if the tile has at least one visible bit not in FOV's blocked bits."""
    return visible_bits - (visible_bits & blocked_bits) > 0


def update_visible_tiles(to_dict: Dict[Tuple[int, int], int], from_list: List[Tuple[int, int, int]]):
    """"Updates full dictionary of visible tiles from per-octant list.
    
    Incoming list of tuples is in form (x, y, visible_bits), where 1st, 2nd, and 3rd 
    visible_bits represent the tile/structure, North, and West wall to draw.
    """
    for (x, y, visible_bits) in from_list:
        current_bits = to_dict.get((x,y), 0)
        to_dict[(x,y)] = current_bits | visible_bits


#    ######      ##     ##    ##  ########
#   ##         ##  ##   ###  ###  ##
#   ##   ###  ##    ##  ## ## ##  ######
#   ##    ##  ########  ##    ##  ##
#    ######   ##    ##  ##    ##  ########

def run_game(tilemap: TileMap, settings: Settings):
    """Renders the FOV display using Pygame."""
    # --- Pygame setup --- #
    pygame.init()
    pygame.display.set_caption("2D Subtile Testing")
    screen = pygame.display.set_mode((1280, 720))
    pygame.key.set_repeat(0)
    clock = pygame.time.Clock()
    running = True

    # --- Player Setup --- #
    px, py = 0, 0
    player_img = pygame.image.load("assets/paperdoll.png").convert_alpha()

    # --- Map Setup --- #
    radius = settings.fov_radius
    tile_size = settings.tile_size
    fov_map = FovMap(radius, settings.subtiles_xy, settings.fov_line_type)
    visible_tiles = fov_calc(0, 0, tilemap, fov_map, radius)

    # --- HUD Setup --- #
    show_fov_line = False
    show_cursor = True

    # --- Initial Draw --- #
    draw_map(screen, tilemap, visible_tiles, settings)
    draw_player(screen, player_img, px, py, tile_size)

    # --- Game Loop --- #
    while running:
        # Track user input to see if map needs to be redrawn (on input)
        redraw = False

        # --- Event Polling --- #
        # pygame.QUIT: Alt+F4 or Pressing 'X' in window corner
        # Handling keypresses with KEYDOWN ensures repeat delay works
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.dict["key"] == pygame.K_w and py > 0:
                    redraw = True
                    py -= 1
                if event.dict["key"] == pygame.K_s and py < tilemap.ydims - 1:
                    redraw = True
                    py += 1
                if event.dict["key"] == pygame.K_a and px > 0:
                    redraw = True
                    px -= 1
                if event.dict["key"] == pygame.K_d and px < tilemap.xdims - 1:
                    redraw = True
                    px += 1

        # Check for mouse movement
        mdx, mdy = pygame.mouse.get_rel()
        if mdx != 0 or mdy != 0:
            redraw = True

        # --- Rendering --- #
        if redraw:
            # fill the screen with a color to wipe away anything from last frame
            screen.fill("black")
            mx, my = pygame.mouse.get_pos()
            visible_tiles = fov_calc(px, py, tilemap, fov_map, radius)
            draw_map(screen, tilemap, visible_tiles, settings)
            draw_player(screen, player_img, px, py, tile_size)
            
            tx, ty = get_tile_at_cursor(mx, my, settings.map_dims, tile_size)

            if show_fov_line:
                draw_fov_line_subpixel(screen, tx, ty, settings)
            if show_cursor:
                draw_tile_at_cursor(screen, tx, ty, settings, line=False)

        pygame.display.flip()

        clock.tick(30)  # FPS limit

    pygame.quit()


#   ##    ##     ##     ########  ##    ##
#   ###  ###   ##  ##      ##     ####  ##
#   ## ## ##  ##    ##     ##     ## ## ##
#   ##    ##  ########     ##     ##  ####
#   ##    ##  ##    ##  ########  ##    ##

if __name__ == "__main__":
    print("\n=====  2D Subpixel FOV Testing  =====\n")
    pygame.freetype.init()
    # FOV Blockers: (structure: int, north_wall: int, west_wall: int)
    blocked = {
        (0, 2): Blockers(wall_n=2, wall_w=2),
        (2, 1): Blockers(structure=True),
        (3, 2): Blockers(wall_w=2),
        (3, 3): Blockers(wall_n=2, wall_w=2),
        (4, 0): Blockers(wall_n=2, wall_w=2),
        (4, 6): Blockers(wall_w=2),
        (9, 3): Blockers(structure=True),
        (8, 4): Blockers(structure=True),
    }
    settings = Settings(
        1280, 720, Coords(16, 9), 64, 1, 4, Font(None, size=16), Color("snow"), fov_line_type=FovLineType.NORMAL
    )
    tilemap = TileMap(blocked, settings)
    run_game(tilemap, settings)  
