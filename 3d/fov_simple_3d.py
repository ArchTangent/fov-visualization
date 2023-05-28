"""3D FOV Visualization."""

from typing import Tuple


class CellMap:
    """Holds `Cell` instances representing the FOV structure of the game map."""

    def __init__(self, xdims: int, ydims: int, blocked: set[Tuple[int, int]]) -> None:
        pass


class Cell:
    """Strucure data for FOV calculations in a `CellMap`."""

    __slots__ = "x", "y", "z", "floor", "ceiling", "structure", "wall_n", "wall_e"

    def __init__(
        self,
        x: int,
        y: int,
        z: int,
        floor: bool,
        ceiling: bool,
        structure: int,
        wall_n: int,
        wall_e: int,
    ) -> None:
        self.x = x
        self.y = y
        self.z = z
        self.floor = floor
        self.ceiling = ceiling
        self.structure = structure
        self.wall_n = wall_n
        self.wall_e = wall_e

    def __repr__(self) -> str:
        f = "F" if self.floor else None
        c = "C" if self.ceiling else None
        n = "_"
        if self.wall_n > 1:
            n = "N"
        elif self.wall_n > 0:
            n = "n"
        e = "_"
        if self.wall_e > 1:
            e = "E"
        elif self.wall_e > 0:
            e = "e"
        s = "_"
        if self.structure > 1:
            s = "S"
        elif self.structure > 0:
            s = "s"
        return f"{self.x, self.y, self.z}: [{f}{c}{s}{n}{e}]"





if __name__ == "__main__":
    print(f"\n===== 3D FOV TESTING =====\n")
    c1 = Cell(1, 2, 3, True, True, 0, 0, 0)
    c2 = Cell(1, 2, 3, True, True, 2, 1, 1)
    print(c1)
    print(c2)

