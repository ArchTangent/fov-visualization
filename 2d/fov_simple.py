"""2D FOV Visualization - Simple Method.

Key Ideas:
- Tiles either `block_sight` completely (over their entire span), or do not.
- FOV is divided into 8 parts called octants (not to be confused with geometric term).
- FOV angle ranges are quantized into 64, 128, or 256 subdivisions.
- It is ~10x faster to use pre-calculated values (in `FovTile`s). See `benchmarks` for more.
- An observer's FOV radius cannot exceed `QBits.value - 1` (e.g. Q32 -> radius 31)
"""
import math
import pygame, pygame.freetype
from pygame import Vector2
from pygame.color import Color
from pygame.freetype import Font
from pygame.surface import Surface
from helpers import (
    Blockers,
    Coords,
    FovLineType,
    Octant,
    QBits,
    boundary_radii,
    pri_sec_to_relative,
    to_tile_id,
)
from map_drawing_2d import (
    draw_player,
    draw_fov_line, 
    draw_tile_at_cursor,
    draw_line_to_cursor,
    draw_floor,
    draw_structure,
)
from typing import Dict, List, Tuple


class Settings:
    """Settings for Pygame."""

    def __init__(
        self,
        width: int,
        height: int,
        map_dims: Coords,
        font: Font,
        font_color: Color,
        max_radius: int = 63,
        radius: int = 63,
        tile_size: int = 64,
        subtiles_xy: int = 8,
        line_width: int = 1,
        qbits: QBits = QBits.Q64,
        fov_line_type: FovLineType = FovLineType.NORMAL,
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
        if map_dims.x < 1 or map_dims.y < 1:
            raise ValueError("all map dimensions must be > 0!")

        self.width = width
        self.height = height
        self.map_dims = map_dims
        self.tile_size = tile_size
        self.line_width = line_width
        self.subtiles_xy = subtiles_xy
        self.subtile_size = tile_size // subtiles_xy
        self.font = font
        self.font_color = font_color
        self.qbits = qbits
        self.fov_line_type = fov_line_type
        self.floor_color = Color(floor_color)
        self.fov_line_color = fov_line_color
        self.fov_line_trim_color = fov_line_trim_color
        self.floor_trim_color = Color(floor_trim_color)
        self.structure_color = Color(structure_color)
        self.structure_trim_color = Color(structure_trim_color)
        self.wall_color = wall_color
        self.wall_trim_color = wall_trim_color
        self.unseen_color = Color(unseen_color)
        self.draw_tid = draw_tid
        # For simple, max radius can't exceed Qbits!
        self.max_radius = min(max_radius, qbits.value - 1)
        self.radius = min(radius, max_radius)


class TileMap:
    """2D tilemap, taking a dictionary of blocked (x,y) coordinates.

    NOTE: direct access to Tilemap.tiles uses [y][x] order. Use `tile_at(x,y)` instead.
    """

    def __init__(self, blocked: Dict[Tuple[int, int], Blockers], settings: Settings):
        self.xdims, self.ydims = settings.map_dims
        ts = settings.tile_size

        self.tiles = [
            [
                Tile(
                    to_tile_id(x, y, self.xdims),
                    x,
                    y,
                    ts,
                    (x, y) in blocked,
                )
                for x in range(self.xdims)
            ]
            for y in range(self.ydims)
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

    def __init__(self, tid: int, x: int, y: int, ts: int, blocked: bool):
        self.tid = tid
        self.x = x
        self.y = y
        self.blocks_path = blocked
        self.blocks_sight = blocked
        # Reference point on the map for drawing
        self.p1 = Vector2(x * ts, y * ts)

    def __repr__(self) -> str:
        return f"C{self.tid}({self.x},{self.y})"

    def to_coords(self) -> Tuple[int, int]:
        return (self.x, self.y)


class FovMaps:
    """Holds `FovMap` instances for each value of FOV radius."""
    def __init__(self, qbits: QBits) -> None:
        self.by_radius = [
            FovMap(r, qbits) for r in range(qbits.value)
        ]


class FovMap:
    """2D FOV map of FovTiles used with TileMap to determine visible tiles.

    ### Parameters

    `radius`: int
        Maximum in-game FOV radius.
    `qbits`: QBits
        Defines the granularity (read: accuracy) of the FOV calculation.
    """

    def __init__(self, radius: int, qbits: QBits) -> None:
        self.octant_1 = FovOctant.new(radius, Octant.O1, qbits)
        self.octant_2 = FovOctant.new(radius, Octant.O2, qbits)
        self.octant_3 = FovOctant.new(radius, Octant.O3, qbits)
        self.octant_4 = FovOctant.new(radius, Octant.O4, qbits)
        self.octant_5 = FovOctant.new(radius, Octant.O5, qbits)
        self.octant_6 = FovOctant.new(radius, Octant.O6, qbits)
        self.octant_7 = FovOctant.new(radius, Octant.O7, qbits)
        self.octant_8 = FovOctant.new(radius, Octant.O8, qbits)


class FovTile:
    """2D FOV Tile used in an FovOctant.

    An FOV tile is visible if at least one of its `visible_bits` is not blocked
    by `blocked` bits in the FOV calculation.

    ### Fields

    `tix`: int
        Tile index within the Octant and list of FOV tiles.
    `dpri, dsec`: int
        Relative (pri,sec) coordinates of the FOV tile compared to FOV origin.
    `visible_bits`: u64
        Bitflags spanning the visible Δsec/Δpri slope range for the tile.
    `blocking_bits`: u64
        Bitflags spanning the Δsec/Δpri slope range blocked by the tile (if wall present).
    `buffer_ix`: int
        dsec index used to set buffer bits.
    `buffer_bits`: int
        bits required to be set in previous column for this tile to be unseen.
    """

    __slots__ = "tix", "rx", "ry", "dpri", "dsec", "abs_radius", "blocking_bits", "visible_bits", "buffer_ix", "buffer_bits",

    def __init__(self, tix: int, dpri: int, dsec: int, octant: Octant, qbits: QBits):
        # Blocking and visible bit ranges are all based on Octant 1
        slope_lo, slope_hi = slopes_by_relative_coords(dpri, dsec)

        self.blocking_bits = quantized_slopes(slope_lo, slope_hi, qbits)
        self.visible_bits = quantized_slopes(slope_lo, slope_hi, qbits)

        # Octant-adjusted relative x/y used to select tile in TileMap
        # dsec is needed for slice filter and bounds checks in FOV calc
        rx, ry = pri_sec_to_relative(dpri, dsec, octant)
        self.rx, self.ry = int(rx), int(ry)
        self.dsec = dsec
        self.dpri = dpri
        self.tix = tix

        # Absolute radius and margin `m`: used to filter tiles within circular radius
        m = 0.5
        if dpri == 0:
            self.abs_radius = (dpri - m) * (dpri - m) + (dsec * dsec)
        else:
            self.abs_radius = (dpri - m) * (dpri - m) + (dsec - m) * (dsec - m)

        # Blocking buffer bits
        buffer_ix = 2**dsec
        self.buffer_ix = buffer_ix
        self.buffer_bits: int

        # Cardinal Alignment
        if dsec == 0:
            self.buffer_bits = buffer_ix

        # Diagonal Alignment
        elif dsec == dpri:
            self.buffer_bits = buffer_ix | buffer_ix >> 1

        # All other tiles
        else:
            self.buffer_bits = buffer_ix | buffer_ix >> 1

    def __repr__(self) -> str:
        return f"FovTile {self.tix} rel: ({self.rx},{self.ry})"


class FovOctant:
    """2D FOV Octant with TileMap coordinate translations and blocking bits.

    ### Parameters

    `radius`: int
        Maximum in-game FOV radius.
    `octant`: Octant
        One of 8 Octants represented by this instance.
    `qbits`: QBits
        Defines the granularity (read: accuracy) of the FOV calculation.

    ### Fields

    `max_fov_ix`: List[int]
        Maximum FovCell index of x or y for a given radius. For example,
        max_fov_ix[22] gives the index of the farthest FovTile in FovOctant.tiles
        for a radius of 22.
    """

    def __init__(self, tiles: List[FovTile], max_fov_ix: List[int]):
        self.tiles = tiles
        self.max_fov_ix = max_fov_ix

    @staticmethod
    def new(radius: int, octant: Octant, qbits: QBits):
        tiles: List[FovTile] = []
        max_fov_ix: List[int] = [0]
        fov_ix = 0
        tix = 1
        limit = radius * radius
        m = 0.5
       
        for dpri in range(1, radius + 1):
            for dsec in range(dpri + 1):
                if dpri == 0:
                    r = (dpri - m) * (dpri - m) + (dsec * dsec)
                else:
                    r = (dpri - m) * (dpri - m) + (dsec - m) * (dsec - m)

                if r < limit:
                    tile = FovTile(tix, dpri, dsec, octant, qbits)
                    tiles.append(tile)
                    fov_ix += 1
                    tix += 1

            max_fov_ix.append(fov_ix)

        return FovOctant(tiles, max_fov_ix)


def get_tile_at_cursor(mx: int, my: int, tile_size: int) -> Coords:
    """Gets the coordinates of the Tile at the mouse cursor position."""
    tx = math.floor(mx / tile_size)
    ty = math.floor(my / tile_size)
    return Coords(tx, ty)


#   ########    ####    ##    ##
#   ##        ##    ##  ##    ##
#   ######    ##    ##  ##    ##
#   ##        ##    ##   ##  ##
#   ##         ######      ##


def fov_calc(
    ox: int, oy: int, tilemap: TileMap, fov_map: FovMap, radius: int
) -> set[Tuple[int, int]]:
    """Returns visible tiles for the 2D FOV calculation using `FovTile`s.

    Notes:
    - check if tile is visible before applying blocking bits.
    - tiles can only add to blocked bits if they are visible.
    - the player's own tile is always visible.

    ### Parameters

    `ox`, `oy`: int
        Origin coordinates of the current Unit.
    `radius`: int
        Current unit's FOV radius.
    """
    xdims, ydims = tilemap.xdims, tilemap.ydims
    visible_tiles = {(ox, oy)}
    abs_radius = radius * radius
    tm = tilemap

    # --- Octants 1-2 --- #
    max_x, max_y = boundary_radii(ox, oy, xdims, ydims, Octant.O1, radius)

    visible_tiles.update(get_visible_tiles(ox, oy, max_x, max_y, abs_radius, tm, fov_map.octant_1))
    visible_tiles.update(get_visible_tiles(ox, oy, max_y, max_x, abs_radius, tm, fov_map.octant_2))

    # --- Octants 3-4 --- #
    max_x, max_y = boundary_radii(ox, oy, xdims, ydims, Octant.O4, radius)

    visible_tiles.update(get_visible_tiles(ox, oy, max_y, max_x, abs_radius, tm, fov_map.octant_3))
    visible_tiles.update(get_visible_tiles(ox, oy, max_x, max_y, abs_radius, tm, fov_map.octant_4))

    # --- Octants 5-6 --- #
    max_x, max_y = boundary_radii(ox, oy, xdims, ydims, Octant.O5, radius)

    visible_tiles.update(get_visible_tiles(ox, oy, max_x, max_y, abs_radius, tm, fov_map.octant_5))
    visible_tiles.update(get_visible_tiles(ox, oy, max_y, max_x, abs_radius, tm, fov_map.octant_6))

    # --- Octants 7-8 --- #
    max_x, max_y = boundary_radii(ox, oy, xdims, ydims, Octant.O8, radius)

    visible_tiles.update(get_visible_tiles(ox, oy, max_y, max_x, abs_radius, tm, fov_map.octant_7))
    visible_tiles.update(get_visible_tiles(ox, oy, max_x, max_y, abs_radius, tm, fov_map.octant_8))

    return visible_tiles


def get_visible_tiles(
    ox: int,
    oy: int,
    max_dpri: int,
    max_dsec: int,
    abs_radius: int,
    tilemap: TileMap,
    fov_octant: FovOctant,
) -> List[Tuple[int, int]]:
    """Returns list of visible tiles in a given Octant using `FovTile`s.

    `ox`, `oy`: int
        Origin coordinates of the Unit for whom FOV is calculated.
    `abs_radius`: int
        Absolute radius (radius * radius) for circular FOV approximation.
    """
    fov_tiles = fov_octant.tiles

    blocked_bits: int = 0
    visible_tiles = []

    pri_ix_max = fov_octant.max_fov_ix[max_dpri]

    # Blocking buffer bits for previous and current (primary) columns
    prev_buffer: int = 0b0
    curr_buffer: int = 0b0
    prev_pri: int = 0

    for fov_tile in fov_tiles[:pri_ix_max]:
        # Filters
        if fov_tile.dsec > max_dsec or fov_tile.abs_radius > abs_radius:
            continue

        if fov_tile.dpri > prev_pri:
            prev_buffer = curr_buffer
            curr_buffer = 0
            prev_pri += 1

        buffer_bits = fov_tile.buffer_bits
        if buffer_bits & prev_buffer == buffer_bits:
            curr_buffer |= fov_tile.buffer_ix
            continue

        if tile_is_visible(fov_tile.visible_bits, blocked_bits):
            tx, ty = ox + fov_tile.rx, oy + fov_tile.ry
            tile = tilemap.tile_at(tx, ty)
            visible_tiles.append((tx, ty))

            if tile.blocks_sight:
                blocked_bits |= fov_tile.blocking_bits
        else:
            curr_buffer |= fov_tile.buffer_ix

        prev_pri = fov_tile.dpri

    return visible_tiles


def quantized_slopes(slope_lo: float, slope_hi: float, qbits: QBits) -> int:
    """Returns dpri/dsec slope in a 32-to-128-bit integer bitfield.

    Used for blocking_bits and visible_bits, these slope ranges round the
    low slope up and the high slope down (narrow).
    """
    slopes: int = 0

    bits = qbits.value

    bit_lo = max(math.ceil(slope_lo * bits), 0)
    bit_hi = min(math.floor(slope_hi * bits), bits)

    for b in range(bit_lo, bit_hi + 1):
        slopes |= 2**b

    return slopes


def slopes_by_relative_coords(dpri: int, dsec: int) -> Tuple[float, float]:
    """Returns low/high dsec/dpri slope for a 2D tile based on relative coords and Octant"""
    if dpri == dsec == 0:
        return 0.0, 1.0

    slope_lo = max((dsec - 0.5) / (dpri + 0.5), 0.0)
    slope_hi = min((dsec + 0.5) / (dpri - 0.5), 1.0)

    return slope_lo, slope_hi


def tile_is_visible(visible_bits: int, blocked_bits: int) -> bool:
    """Returns `True` if the tile has at least one visible bit not in FOV's blocked bits."""
    return visible_bits - (visible_bits & blocked_bits) > 0


#   #######   #######      ##     ##    ##
#   ##    ##  ##    ##   ##  ##   ##    ##
#   ##    ##  #######   ##    ##  ## ## ##
#   ##    ##  ##   ##   ########  ###  ###
#   #######   ##    ##  ##    ##   ##  ##

def draw_map(
    tilemap: TileMap,
    visible_tiles: set,
    screen: Surface,
    settings: Settings,
):
    """Renders the Tilemap, accounting for FOV."""
    # Row is y; col is x
    for ty, row_data in enumerate(tilemap.tiles):
        for tx, tile in enumerate(row_data):
            if (tx, ty) in visible_tiles:
                draw_tile(screen, tile, settings)


def draw_tile(screen: Surface, tile: Tile, settings: Settings):
    """Renders a visible 3D Tile on the map."""
    p1 = tile.p1
    p1x, p1y = tile.p1
    s = settings
    w = s.line_width
    ts = s.tile_size
    sts = s.subtile_size
    trim_color = settings.floor_trim_color

    # Draw grid if no structure present
    if not tile.blocks_sight:
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
    else:
        draw_structure(screen, p1, ts, w, s.structure_color, s.structure_trim_color)


#    ######      ##     ##    ##  ########
#   ##         ##  ##   ###  ###  ##
#   ##   ###  ##    ##  ## ## ##  ######
#   ##    ##  ########  ##    ##  ##
#    ######   ##    ##  ##    ##  ########


def run_game(blocked: Dict[Tuple[int, int], Blockers], settings: Settings):
    """Renders the FOV display using Pygame."""
    # --- Pygame setup --- #
    pygame.init()
    pygame.display.set_caption("2D Simple FOV")
    screen = pygame.display.set_mode((settings.width, settings.height))
    pygame.key.set_repeat(0)
    clock = pygame.time.Clock()
    running = True

    # --- Player Setup --- #
    px, py = (0, 0)
    player_img = pygame.image.load("assets/paperdoll.png").convert_alpha()
    radius = settings.radius
    max_radius = settings.max_radius

    # --- Map Setup --- #
    tilemap = TileMap(blocked, settings)
    tile_size = settings.tile_size

    fov_map = FovMap(max_radius, settings.qbits)
    visible_tiles = fov_calc(px, py, tilemap, fov_map, radius)

    # --- HUD Setup --- #
    show_player_line = False
    show_fov_line = False
    show_cursor = True


    # --- Initial Draw --- #
    draw_map(tilemap, visible_tiles, screen, settings)
    draw_player(screen, player_img, px, py, tile_size)

    # --- Game Loop --- #
    while running:
        # Track user input for redrawing map
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
                if event.dict["key"] == pygame.K_c:
                    show_cursor = not show_cursor
                    redraw = True
                if event.dict["key"] == pygame.K_f:
                    show_fov_line = not show_fov_line
                    redraw = True
                if event.dict["key"] == pygame.K_r:
                    show_player_line = not show_player_line
                    redraw = True
                if event.dict["key"] == pygame.K_MINUS and radius > 0:
                    redraw = True
                    radius -= 1
                if event.dict["key"] == pygame.K_EQUALS and radius < max_radius:
                    redraw = True
                    radius += 1

        # --- Rendering --- #
        if redraw:
            # fill the screen with a color to wipe away anything from last frame
            screen.fill("black")
            mx, my = pygame.mouse.get_pos()
            visible_tiles = fov_calc(px, py, tilemap, fov_map, radius)
            draw_map(tilemap, visible_tiles, screen, settings)
            draw_player(screen, player_img, px, py, tile_size)

            tx, ty = get_tile_at_cursor(mx, my, tile_size)

            if show_fov_line:
                draw_fov_line(screen, px, py, tx, ty, settings)
            if show_cursor:
                draw_tile_at_cursor(screen, tx, ty, settings, line=False)
            if show_player_line:
                draw_line_to_cursor(screen, px, py, mx, my, settings)

        pygame.display.flip()

        clock.tick(60)  # FPS limit

    pygame.quit()


#   ##    ##     ##     ########  ##    ##
#   ###  ###   ##  ##      ##     ####  ##
#   ## ## ##  ##    ##     ##     ## ## ##
#   ##    ##  ########     ##     ##  ####
#   ##    ##  ##    ##  ########  ##    ##

if __name__ == "__main__":
    print("\n=====  2D Simple FOV Testing  =====\n")

    pygame.freetype.init()

    blocked: Dict[Tuple[int, int], Blockers] = {
        (4, 4): Blockers(structure=2),
        (5, 4): Blockers(structure=2),
        (8, 4): Blockers(structure=2),
        (10, 4): Blockers(structure=2),
        (13, 7): Blockers(structure=2),
        (14, 6): Blockers(structure=2),
        (15, 0): Blockers(structure=2),
        (15, 1): Blockers(structure=2),
    }

    settings = Settings(
        1920,
        1080,
        Coords(128, 128),
        Font(None, size=16),
        Color("snow"),
        radius=5,
        qbits=QBits.Q32,
    )

    fovmaps = FovMaps(settings.qbits)

    run_game(blocked, settings)
