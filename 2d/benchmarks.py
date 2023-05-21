"""Benchmarks for 2D FOV Visualization."""

import random
import time
from fov_simple_2d import fov_calc, fov_calc_raw

def bench_fov_simple(maps: int, radius: int, density: int, tries: int, seed: int):
    """Benchmarks visible tiles calc with FovTiles. 129x129 map w/64-fov Unit in center."""
    random.seed(seed)
    total_time = 0
    total_vt = 0

    for _ in range(maps):
        blocked = {(random.randint(0, 128), random.randint(0, 128)) for _ in range(density)}
        tm = TileMap(129, 129, blocked)
        fm = FovMap2D(radius)
        for trial in range(tries):
            start = time.time()
            vt = fov_calc(64, 64, tm, fm, radius)
            total_vt += len(vt)
            end = time.time()
            total_time += end - start


    print(f"Time (reg): {total_time} seconds")

def bench_fov_simple_raw(maps: int, radius: int, density: int, tries: int, seed: int):
    """Benchmarks visible tiles calc without FovTiles. 129x129 map w/64-fov Unit in center."""
    random.seed(seed)
    total_time = 0
    total_vt = 0

    for _ in range(maps):
        blocked = {(random.randint(0, 128), random.randint(0, 128)) for _ in range(density)}
        tm = TileMap(129, 129, blocked)
        fm = FovMap2D(radius)
        for trial in range(tries):
            start = time.time()
            vt = fov_calc_raw(64, 64, tm, radius)
            total_vt += len(vt)
            end = time.time()
            total_time += end - start

    print(f"Time (raw): {total_time} seconds")

if __name__ == "__main__":
    print("\n=====  2D FOV Benchmarks  =====\n")
    SEED=13

    print(f"----- FOV Simple -----")
    time_data=[5,64,100,100,SEED]
    bench_fov_simple(*time_data)
    bench_fov_simple_raw(*time_data)

