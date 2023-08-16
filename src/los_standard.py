"""10 AUG 2023 - Simple 2D Line of Sight using Angle Ranges."""
import math
import pygame, pygame.freetype
from pygame import Vector2
from pygame.color import Color
from pygame.freetype import Font
from pygame.surface import Surface
from helpers import Blockers, Coords, Direction, FovLineType, Line, QBits, to_tile_id
from map_drawing import (
    draw_enemy,
    draw_player,
    draw_fov_line,
    draw_tile_at_cursor,
    draw_line_to_cursor,
    draw_floor,
    draw_north_wall,
    draw_west_wall,
    draw_structure,
)
from lines import fire_line
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
        radius: int = 63,
        max_radius: int = 63,
        tile_size: int = 64,
        subtiles_xy: int = 8,
        line_width: int = 1,
        qbits: QBits = QBits.Q64,
        fov_line_type: FovLineType = FovLineType.NORMAL,
        floor_color="steelblue2",
        floor_trim_color="steelblue4",
        fov_line_color="deepskyblue1",
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
        self.xdims, self.ydims = map_dims
        self.tile_size = tile_size
        self.line_width = line_width
        self.subtiles_xy = subtiles_xy
        self.subtile_size = tile_size // subtiles_xy
        self.font = font
        self.font_color = font_color
        self.max_radius = min(max_radius, 127)
        self.radius = min(radius, self.max_radius)
        self.qbits = qbits
        self.fov_line_type = fov_line_type
        self.floor_color = Color(floor_color)
        self.fov_line_color = fov_line_color
        self.floor_trim_color = Color(floor_trim_color)
        self.wall_color = Color(wall_color)
        self.wall_trim_color = Color(wall_trim_color)
        self.structure_color = Color(structure_color)
        self.structure_trim_color = Color(structure_trim_color)
        self.unseen_color = unseen_color
        self.draw_tid = draw_tid


class Tile:
    """2D Tile, where `p1` is the reference point for drawing."""

    def __init__(self, tid: int, coords: Coords, ts: int, blockers: Blockers):
        self.tid = tid
        self.x = coords.x
        self.y = coords.y
        self.p1 = Vector2(coords.x * ts, coords.y * ts)
        self.structure = blockers.structure
        self.wall_n = blockers.wall_n
        self.wall_w = blockers.wall_w

    def __repr__(self) -> str:
        return f"T{self.tid}({self.x},{self.y}) S:{self.structure} N: {self.wall_n} W: {self.wall_w}"

    def to_coords(self) -> Tuple[int, int]:
        return (self.x, self.y)


class TileMap:
    """2D tilemap, taking a dictionary of blocked (x,y) coordinates."""

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
            Tile(
                to_tile_id(x, y, xdims),
                Coords(x, y),
                ts,
                blocked.get((x, y), Blockers()),
            )
            for y in range(ydims)
            for x in range(xdims)
        ]

    def tile_at(self, x: int, y: int) -> Tile:
        """Gets Tile at given location."""
        tid = x + y * self.xdims
        return self.tiles[tid]

    def show(self):
        tile_row = []
        row = 0
        for tile in self.tiles:
            tile_row.append(f"{tile}")
            if tile.y > row:
                row += 1
                print(" ".join(tile_row))
                tile_row.clear()


def get_tile_at_cursor(mx: int, my: int, tile_size: int) -> Coords:
    """Gets the coordinates of the Tile at the mouse cursor position."""
    tx = math.floor(mx / tile_size)
    ty = math.floor(my / tile_size)
    return Coords(tx, ty)


#   ##         ######    ######
#   ##        ##    ##  ##
#   ##        ##    ##   ######
#   ##        ##    ##        ##
#   ########   ######   #######


class LosTile:
    """Line of Sight tile holding objects that block sight."""

    # def __init__(self, x: int, y: int, blockers: Blockers) -> None:
    def __init__(self, blockers: Blockers) -> None:
        self.wall_n = blockers.wall_n
        self.wall_w = blockers.wall_w
        self.structure = blockers.structure

    def blocks(self, x: int, y: int, line: Line, facing: int) -> bool:
        """Returns `True` if this LOS tile blocks the incoming LOS line.

        Facing is an NSEW (0th bit = North) bitflag whose facing is that of the
        tile with respect to the source.
        """
        rx, ry = float(x), float(y)

        if self.wall_n:
            wall_line = Line(rx, ry, rx + 1.0, ry)
            print(f" block: LOS line {line} vs wall N {wall_line}")
            if line.intersects(wall_line):
                return True

        if self.wall_w:
            wall_line = Line(rx, ry, rx, ry + 1.0)
            print(f" block: LOS line {line} vs wall W {wall_line}")
            if line.intersects(wall_line):
                return True

        if not self.structure:
            return False

        print(f" Facing at structure: {bin(facing)}")
        # Tile is N (true) or S (false) of source
        if facing & 1 > 0:
            structure_line = Line(rx, ry + 1.0, rx + 1.0, ry + 1.0)
        else:
            structure_line = Line(rx, ry, rx + 1.0, ry)

        print(f" block: LOS line {line} vs structure 1 {structure_line}")
        if line.intersects(structure_line):
            return True

        # Tile is E (true) or W (false) of source
        if facing & 4 > 0:
            structure_line = Line(rx, ry, rx, ry + 1.0)
        else:
            structure_line = Line(rx + 1.0, ry, rx + 1.0, ry + 1.0)

        print(f" block: LOS line {line} vs structure 2 {structure_line}")
        if line.intersects(structure_line):
            return True

        print(f" ...LOS line {line} is unblocked!")
        return False


class LosMap:
    """Line of Sight map, storing LosTiles for tiles that block vision."""

    def __init__(self, blocked: Dict[Tuple[int, int], Blockers]) -> None:
        self.tiles = {(x, y): LosTile(b) for ((x, y), b) in blocked.items()}


def get_los_points(
    sx: float, sy: float, tx: float, ty: float
) -> List[Tuple[float, float]]:
    """Returns LOS points based on LOS facing.

    In a game, Base LOS points would be stored by the unit being observed.
    Here, they're stored in the function for simplicity.

    Base LOS points are stored WRT center of tile.
    """

    dx = tx - sx
    dy = ty - sy

    # Base pts at N/S facing
    pts = [(-0.4, 0.0), (-0.2, 0.0), (0.0, 0.0), (0.2, 0.0), (0.4, 0.0)]

    # N, S facing
    if abs(dy) > 2.0 * abs(dx):
        return pts
    # E, W facing
    elif abs(dx) > 2.0 * abs(dy):
        return [(0.0, -0.4), (0.0, -0.2), (0.0, 0.0), (0.0, 0.2), (0.0, 0.4)]
    # NE, SW facing
    elif dx * dy < 0.0:
        return [(0.707 * x, 0.707 * x) for x, _ in pts]
    # SE, NW facing
    else:
        return [(-0.707 * x, 0.707 * x) for x, _ in pts]


def get_los_lines(sx: float, sy: float, tx: float, ty: float) -> List[Line]:
    """Returns LOS lines to LOS points."""
    los_pts = get_los_points(sx, sy, tx, ty)
    lines = [Line(sx, sy, tx + rx, ty + ry) for rx, ry in los_pts]

    return lines


def unit_is_visible(los_map: LosMap, px: int, py: int, ex: int, ey: int) -> bool:
    """Returns `True` if the unit at `(ex, ey)` is visible.

    LOS facing is broken into NSEW bits as 0b0000, where 0th bit is North.
    This facing is that of the target with respect to the source.

    If a LOS line passes through all tiles without being blocked, the target
    is visible. If all LOS lines are blocked, the target is not visible.
    """
    sx, sy = px + 0.5, py + 0.5
    tx, ty = ex + 0.5, ey + 0.5
    los_lines = get_los_lines(sx, sy, tx, ty)
    los_tiles = [t for t in fire_line(sx, sy, ex, ey) if t in los_map.tiles]

    #          WESN
    facing = 0b0000

    if ey < py:
        facing |= 0b0001
    if ey > py:
        facing |= 0b0010
    if ex > px:
        facing |= 0b0100
    if ex < px:
        facing |= 0b1000

    for los_line in los_lines:
        print(f"[LOS] Line: {los_line}")
        blocked = False
        for tx, ty in los_tiles:
            los_tile = los_map.tiles.get((tx, ty))
            if los_tile and los_tile.blocks(tx, ty, los_line, facing):
                blocked = True
                break
        if not blocked:
            print(f"[LOS] unit is visible")
            return True

    # All lines blocked
    print(f"[LOS] unit is NOT visible")
    return False


#   #######   #######      ##     ##    ##
#   ##    ##  ##    ##   ##  ##   ##    ##
#   ##    ##  #######   ##    ##  ## ## ##
#   ##    ##  ##   ##   ########  ###  ###
#   #######   ##    ##  ##    ##   ##  ##


def draw_map(
    screen: Surface,
    tilemap: TileMap,
    visible_tiles: Dict[int, int],
    settings: Settings,
):
    """Renders the Tilemap, accounting for FOV."""
    for tid, tile in enumerate(tilemap.tiles):
        visible_tile = visible_tiles.get(tid)
        if visible_tile:
            draw_tile(screen, tile, visible_tile, settings)


def draw_tile(screen: Surface, tile: Tile, visible_parts: int, settings: Settings):
    """Renders a visible 3D Tile on the map using `visible_parts` data.

    ```
                      CWNT
    visible_parts = 0b0000
    ```
    Where:
    - `C` = Corner (if a wall present)
    - `W` = West wall
    - `N` = North wall
    - `T` = Tile (and structure, if present)
    """
    p1 = tile.p1
    p1x, p1y = tile.p1
    s = settings
    w = s.line_width
    ts = s.tile_size
    sts = s.subtile_size
    trim_color = settings.floor_trim_color

    # Draw Tile (if not blocked by walls), and structure (if present)
    if visible_parts & 0b0001:
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

        draw_floor(screen, p1, ts, s.floor_color)

        if tile.structure:
            draw_structure(screen, p1, ts, w, s.structure_color, s.structure_trim_color)

        if tile.wall_n:
            draw_north_wall(screen, p1, ts, sts, w, s.wall_color, s.wall_trim_color)

        if tile.wall_w:
            draw_west_wall(screen, p1, ts, sts, w, s.wall_color, s.wall_trim_color)
    else:
        if visible_parts & 0b0010:
            draw_north_wall(screen, p1, ts, sts, w, s.wall_color, s.wall_trim_color)

        if visible_parts & 0b0100:
            draw_west_wall(screen, p1, ts, sts, w, s.wall_color, s.wall_trim_color)


def draw_los_lines(
    screen: Surface, los_map: LosMap, px: int, py: int, ex: int, ey: int, settings
):
    """Draws all LOS lines to a target, with color coding."""
    seen_color = Color(115, 191, 17)
    unseen_color = Color(215, 30, 120)
    ts = settings.tile_size

    sx, sy = px + 0.5, py + 0.5
    tx, ty = ex + 0.5, ey + 0.5
    los_lines = get_los_lines(sx, sy, tx, ty)
    los_tiles = [t for t in fire_line(sx, sy, ex, ey) if t in los_map.tiles]

    x1 = sx * ts
    y1 = sy * ts

    #          WESN
    facing = 0b0000

    if ey < py:
        facing |= 0b0001
    if ey > py:
        facing |= 0b0010
    if ex > px:
        facing |= 0b0100
    if ex < px:
        facing |= 0b1000

    for los in los_lines:
        blocked = False
        color = seen_color
        for tx, ty in los_tiles:
            los_tile = los_map.tiles.get((tx, ty))

            if los_tile and los_tile.blocks(tx, ty, los, facing):
                blocked = True
                color = unseen_color
                break

        if blocked:
            color = unseen_color

        x2 = los.x2 * ts
        y2 = los.y2 * ts

        # print(f"[DRAW] drawing line from {(los.x1, los.y1)} to {(los.x2, los.y2)}")
        pygame.draw.line(screen, color, (x1, y1), (x2, y2))


#    ######      ##     ##    ##  ########
#   ##         ##  ##   ###  ###  ##
#   ##   ###  ##    ##  ## ## ##  ######
#   ##    ##  ########  ##    ##  ##
#    ######   ##    ##  ##    ##  ########


def run_game(tilemap: TileMap, losmap: LosMap, settings: Settings):
    """Renders the FOV display using Pygame."""
    # --- Pygame setup --- #
    pygame.init()
    pygame.display.set_caption("2D standard FOV")
    screen = pygame.display.set_mode((settings.width, settings.height))
    pygame.key.set_repeat(0)
    clock = pygame.time.Clock()
    running = True

    # --- Unit Setup --- #
    px, py = settings.xdims // 2, settings.ydims // 2
    ex, ey = settings.xdims * 3 // 4, settings.ydims * 3 // 4

    # --- Map Setup --- #
    # All tiles visible for now, with no FOV map radius
    visible_tiles = {tid: 0b0001 for tid, _ in enumerate(tilemap.tiles)}
    tile_size = settings.tile_size
    radius = 32
    max_radius = settings.max_radius

    # --- HUD Setup --- #
    show_player_line = False
    show_los_lines = False
    show_fov_line = False
    show_cursor = True

    # --- Initial Draw --- #
    draw_map(screen, tilemap, visible_tiles, settings)
    draw_player(screen, px, py, tile_size)

    enemy_seen = unit_is_visible(losmap, px, py, ex, ex)

    draw_enemy(screen, ex, ey, tile_size)

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
                redraw = True
                # Player
                if event.dict["key"] == pygame.K_w and py > 0:
                    py -= 1
                if event.dict["key"] == pygame.K_s and py < tilemap.ydims - 1:
                    py += 1
                if event.dict["key"] == pygame.K_a and px > 0:
                    px -= 1
                if event.dict["key"] == pygame.K_d and px < tilemap.xdims - 1:
                    px += 1
                # Enemy
                if event.dict["key"] == pygame.K_i and ey > 0:
                    ey -= 1
                if event.dict["key"] == pygame.K_k and ey < tilemap.ydims - 1:
                    ey += 1
                if event.dict["key"] == pygame.K_j and ex > 0:
                    ex -= 1
                if event.dict["key"] == pygame.K_l and ex < tilemap.xdims - 1:
                    ex += 1
                # Line of Sight / Field of View
                if event.dict["key"] == pygame.K_c:
                    show_cursor = not show_cursor
                if event.dict["key"] == pygame.K_v:
                    show_los_lines = not show_los_lines
                if event.dict["key"] == pygame.K_f:
                    show_fov_line = not show_fov_line
                if event.dict["key"] == pygame.K_r:
                    show_player_line = not show_player_line
                if event.dict["key"] == pygame.K_MINUS and radius > 0:
                    radius -= 1
                if event.dict["key"] == pygame.K_EQUALS and radius < max_radius:
                    radius += 1

        # Check for mouse movement
        mdx, mdy = pygame.mouse.get_rel()
        if mdx != 0 or mdy != 0:
            redraw = True

        # --- Rendering --- #
        if redraw:
            # Fill the screen to clear previous frame
            screen.fill("black")
            mx, my = pygame.mouse.get_pos()
            draw_map(screen, tilemap, visible_tiles, settings)
            draw_player(screen, px, py, tile_size)

            enemy_seen = unit_is_visible(losmap, px, py, ex, ey)

            draw_enemy(screen, ex, ey, tile_size)

            tx, ty = get_tile_at_cursor(mx, my, tile_size)

            if show_fov_line:
                draw_fov_line(screen, px, py, tx, ty, settings)
            if show_los_lines:
                draw_los_lines(screen, losmap, px, py, ex, ey, settings)
            if show_cursor:
                draw_tile_at_cursor(screen, tx, ty, settings, line=False)
            if show_player_line:
                draw_line_to_cursor(screen, px, py, mx, my, settings)

        pygame.display.flip()

        clock.tick(30)  # FPS limit

    pygame.quit()


#   ##    ##     ##     ########  ##    ##
#   ###  ###   ##  ##      ##     ####  ##
#   ## ## ##  ##    ##     ##     ## ## ##
#   ##    ##  ########     ##     ##  ####
#   ##    ##  ##    ##  ########  ##    ##

if __name__ == "__main__":
    print("\n=====  2D Simple LOF Testing  =====\n")

    pygame.freetype.init()

    blocked: Dict[Tuple[int, int], Blockers] = {
        (4, 4): Blockers(wall_n=2),
        (5, 4): Blockers(wall_w=2),
        (8, 4): Blockers(wall_n=2, wall_w=2),
        (10, 4): Blockers(wall_n=2),
        (11, 4): Blockers(wall_n=2),
        (13, 7): Blockers(structure=True),
        (14, 6): Blockers(structure=True),
        (15, 0): Blockers(wall_w=2),
        (15, 1): Blockers(wall_n=2),
        (19, 4): Blockers(wall_n=2),
        (20, 3): Blockers(wall_w=2),
        (20, 4): Blockers(wall_n=2, wall_w=2),
    }

    settings = Settings(
        1280,
        720,
        Coords(16, 9),
        Font(None, size=16),
        Color("snow"),
        radius=5,
    )

    losmap = LosMap(blocked)
    tilemap = TileMap(blocked, settings)
    run_game(tilemap, losmap, settings)

    # TODO: finish map_drawing_2d draw_unit()
    # TODO: finish map_drawing_2d draw_unit_los_plane()
    # TODO: finish map_drawing_2d draw_unit_los_cone() with range to circular hitbox plane

    # TODO: add Unit class with faction and hitbox dimensions (circular)
    # TODO: add Unit class with faction and hitbox dimensions
    # TODO: add unit_list to game, as List[Unit]

    # TODO: draw_fire_line() with hotkey F (replace old)
    # TODO: draw_los_tile()

    # TODO: peeking by moving into entry (~0.1 tile units in) of valid neighboring tile
    # TODO: hug the wall by making LOS facing fixed according to wall being hugged
    # TODO: filter out fire_line() at creation by filtering out tiles not in LOSmap

