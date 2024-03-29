"""FOV calculation benchmarks.

Key Ideas:
- Randomly generate map X*Y tilemap with N blockers (only full walls for Simple FOV)
- Each bench tests 10 `fov_calc()`s per `map` value.  If 10 maps, 100 FOV calcs are done.
- For Advanced 2D, the radius is capped to QBits - 1 (e.g. Q32 -> 31 radius)

Operational Complexity:
    where m = number of blocking structures in tile; n = number of FovTiles

Simple 2D:          O(m+n)  number of blocking checks is constant per tile
Standard 2D:        O(m+n)  number of blocking checks is constant per tile
Subtile 2D:         O(m+n)  number of blocking checks is constant per tile
On-the-Fly 2D:      O(m*n)  with list of blocking lines/rects

Results (128x128, 10% blocked, 50 maps, radius 63):
Simple 2D (Q64)       0.541 seconds   923 FPS
Simple 2D (Q128)      0.565 seconds   885 FPS
Standard 2D           1.932 seconds   258 FPS
Subtile 2D            1.435 seconds   348 FPS

Results (128x128, 20% blocked, 50 maps, radius 63):
Simple 2D (Q64)       0.523 seconds   955 FPS
Simple 2D (Q128)      0.537 seconds   930 FPS
Standard 2D           1.849 seconds   270 FPS
Subtile 2D            0.910 seconds   549 FPS

Takeaways:
1.) Use the Standard FOV calculation - best blend of speed and accuracy.
2.) The fewer blocking structures in the map, the longer the calculation takes.
3.) Filters have less impact with lower obstruction density.
4.) Simple FOV does not require filtering: no significant performance gain from it.
5.) On-the-fly methods scale FAR too poorly to work for frequent or far-reaching FOVs!
If they are to be used, it should only be for small FOV radii, in 2D, with few blockers.
6.) Pre-baked circular FovMaps are ~20% faster than calculating circular FOV in fov_calc().
"""
import fov_simple, fov_subtile, fov_standard
from pygame.color import Color
from pygame.freetype import Font
from helpers import Blockers, Coords, QBits
from typing import Callable, Dict, List, Tuple
import random
import time

#    ######   ########  ########  ##    ##  #######
#   ##        ##           ##     ##    ##  ##    ##
#    ######   ######       ##     ##    ##  #######
#         ##  ##           ##     ##    ##  ##
#   #######   ########     ##      ######   ##


class BenchSettings:
    def __init__(
        self,
        seed: int,
        dims: Coords,
        maps: int,
        radius: int,
        pct_blocked: float,
        use_walls: bool,
    ) -> None:
        self.seed = seed
        self.dims = dims
        self.maps = maps
        self.radius = radius
        self.pct_blocked = pct_blocked
        self.blocked_ct = int(dims.x * dims.y * pct_blocked)
        self.use_walls = use_walls


def random_blockers(dims: Coords, count: int, use_walls: bool, simple: bool) -> Dict:
    """Generates random dictionary of `Blockers`.

    Blockers vary with `use_walls`:
    - if `True`:  all non-simple fov calcs are half structure, half wall
    - if `False`: all fov calc blockers are structures

    Essentially, set `use_walls = False` when comparing simple FOV vs other methods.
    """
    from random import randint, sample

    x, y = dims.x - 1, dims.y - 1

    blocked = {(randint(0, x), randint(0, y)): Blockers() for t in range(count)}
    coords = [*blocked.keys()]

    match (simple, use_walls):
        case False, True:
            struct_ct = len(coords) // 2
            n_wall_ct = struct_ct // 2
            w_wall_ct = struct_ct // 2
        case _:
            struct_ct = len(coords)
            n_wall_ct = 0
            w_wall_ct = 0

    # Structures
    for c in sample(coords, struct_ct):
        blocked[c].structure = 2

    # N Walls
    for c in sample(coords, n_wall_ct):
        blocked[c].wall_n = 2

    # W walls
    for c in sample(coords, w_wall_ct):
        blocked[c].wall_w = 2

    return blocked


def bench_timer(module, fov_map, bs, settings, simple: bool):
    """General-use benchmark timer."""
    sx, sy = bs.dims.x // 2, bs.dims.y // 2
    random.seed(bs.seed)
    total = 0.0

    # Time each variation of the map
    origins = [(sx + dx, sy) for dx in range(-4, 6)]
    visible_ct = 0

    for bench_map in range(bs.maps):
        blocked = random_blockers(bs.dims, bs.blocked_ct, bs.use_walls, simple)
        tilemap = module.TileMap(blocked, settings)
        start = time.time()
        for ox, oy in origins:
            visible = module.fov_calc(ox, oy, tilemap, fov_map, settings.max_radius)
            visible_ct += len(visible)
        end = time.time()
        total += end - start

    octant_len = len(fov_map.octant_1.tiles)
    print(f"  {visible_ct} visible tiles with {octant_len} FovTiles per octant")

    return total


#   #######   ########  ##    ##   ######   ##    ##
#   ##    ##  ##        ###   ##  ##    ##  ##    ##
#   #######   ######    ## ## ##  ##        ########
#   ##    ##  ##        ##   ###  ##    ##  ##    ##
#   #######   ########  ##    ##   ######   ##    ##


def bench_simple_2d_q32(bs: BenchSettings) -> float:
    """Bench for simple 2D FOV with 32 Qbits."""
    module = fov_simple

    settings = module.Settings(
        1280,
        720,
        bs.dims,
        Font(None, size=16),
        Color("snow"),
        qbits=QBits.Q32,
        max_radius=bs.radius,
    )

    fov_map = module.FovMap(settings.max_radius, settings.qbits)
    total = bench_timer(module, fov_map, bs, settings, simple=True)

    return total


def bench_simple_2d_q64(bs: BenchSettings) -> float:
    """Bench for simple 2D FOV with 64 Qbits."""
    module = fov_simple

    settings = module.Settings(
        1280,
        720,
        bs.dims,
        Font(None, size=16),
        Color("snow"),
        qbits=QBits.Q64,
        max_radius=bs.radius,
    )

    fov_map = module.FovMap(settings.max_radius, settings.qbits)
    total = bench_timer(module, fov_map, bs, settings, simple=True)

    return total


def bench_simple_2d_q128(bs: BenchSettings) -> float:
    """Bench for simple 2D FOV with 128 Qbits."""
    module = fov_simple

    settings = module.Settings(
        1280,
        720,
        bs.dims,
        Font(None, size=16),
        Color("snow"),
        qbits=QBits.Q128,
        max_radius=bs.radius,
    )

    fov_map = module.FovMap(settings.max_radius, settings.qbits)
    total = bench_timer(module, fov_map, bs, settings, simple=True)

    return total


def bench_standard_2d(bs: BenchSettings) -> float:
    """Bench for standard 2D FOV."""
    module = fov_standard

    settings = module.Settings(
        1280,
        720,
        bs.dims,
        Font(None, size=16),
        Color("snow"),
        max_radius=bs.radius,
    )

    fov_map = module.FovMap.new(settings.max_radius)
    total = bench_timer(module, fov_map, bs, settings, simple=False)

    return total


def bench_subtile_2d(bs: BenchSettings) -> float:
    """Bench for subtile 2D FOV."""
    module = fov_subtile

    settings = module.Settings(
        1280,
        720,
        bs.dims,
        Font(None, size=16),
        Color("snow"),
        max_radius=bs.radius,
    )

    fov_map = module.FovMap(
        settings.max_radius, settings.subtiles_xy, settings.fov_line_type
    )
    total = bench_timer(module, fov_map, bs, settings, simple=False)

    return total


def run_benchmark(
    name: str, funcs: List[Tuple[str, Callable]], settings: BenchSettings
):
    """Summarizes collection of benchmarks in (bench_name, bench_func) format.

    Notes:
    - there are 10 tiles explored per map in `maps`
    - results are sorted by lowest time
    """
    s = settings
    print(f"--- {name} benchmarks ---")
    print(
        f"Dims = {s.dims.x}x{s.dims.y}, density = {s.pct_blocked}, maps = {s.maps}, radius = {s.radius}\n"
    )

    frames = settings.maps * 10
    results = []

    for func_name, func in funcs:
        print(f"Benchmarking {func_name}...")
        total_time = func(bench_settings)
        fps = int(frames / total_time)
        results.append((func_name, total_time, fps))

    print("...Done!  The results:\n")

    for bench_name, total_time, fps in results:
        print(f"{bench_name:20} {round(total_time, 3):6} seconds {fps:5} FPS")


#   ##    ##     ##     ########  ##    ##
#   ###  ###   ##  ##      ##     ####  ##
#   ## ## ##  ##    ##     ##     ## ## ##
#   ##    ##  ########     ##     ##  ####
#   ##    ##  ##    ##  ########  ##    ##

if __name__ == "__main__":
    print(f"\n===== FOV Benchmarks =====\n")
    import pygame.freetype

    pygame.freetype.init()

    seed = 13
    dims = Coords(128, 128)
    by_radius = 50
    radius = 63
    density = 0.20
    use_walls = True

    bench_settings = BenchSettings(seed, dims, by_radius, radius, density, use_walls)

    run_benchmark(
        f"Density {int(density * 100)}% Radius {radius}",
        [
            # ("Simple 2D (Q32)", bench_simple_2d_q32),
            ("Simple 2D (Q64)", bench_simple_2d_q64),
            # ("Simple 2D (Q128)", bench_simple_2d_q128),
            # ("Simple 2D (Q128 F1)", bench_simple_2d_q128_f1),
            # ("Simple 2D (Q128 F2)", bench_simple_2d_q128_f2),
            ("Standard 2D", bench_standard_2d),
            ("Subtile 2D", bench_subtile_2d),
        ],
        bench_settings,
    )
