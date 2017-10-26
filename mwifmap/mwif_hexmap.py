"""container and service code for PHOR hexmap"""

## IMPORTS

import collections

## HELPERS

def to_cube(q_r):
    """phor to cube"""

    q, r = q_r
    x = q - (r - (r & 1)) / 2
    y = -x - r
    return x, y, r


def from_cube(x_y_z):
    """cube to phor"""

    x, y, z = x_y_z
    return int(x + (z - (z & 1)) / 2), int(z)

## CLASSES

class HexMapError(Exception):
    pass


class HexMapCell(collections.MutableMapping):
    """hexmap cell"""

    ## ctor

    def __init__(self, q, r):
        self.q = q
        self.r = r
        self._data = {}

    ## MutableMapping abc implementation

    def __getitem__(self, key):
        return self._data[key]

    def __setitem__(self, key, value):
        self._data[key] = value

    def __delitem__(self, key):
        del self._data[key]

    def __len__(self):
        return len(self._data)

    def __iter__(self):
        return iter(self._data)

    ## special

    def __str__(self):
        return "Cell[{},{}]".format(self.q, self.r)

    ## service

    def key(self):
        return self.q, self.r


class HexMap(collections.Mapping):
    """container for `HexMapCell`s on a PHOR hexagonal grid"""

    ## ctor

    def __init__(self, cols, rows, *args, **keywords):
        self.cols = cols
        self.rows = rows
        self._cell = {(q, r): HexMapCell(q, r) for q in range(self.cols) for r in range(self.rows)}

    ## Mapping abc implementation

    def __getitem__(self, q_r):
        return self._cell[q_r]

    def __iter__(self):
        return iter(self._cell)

    def __len__(self):
        return self.cols * self.rows


    def __str__(self):
        return "{}({}, {})".format(self.__class__.__name__, self.cols, self.rows)

    @property
    def size(self):
        return self.rows, self.cols

    def distance(self, orig, dest):
        """distance between two coordinates"""
        # checks
        oq_x, oq_y, oq_z = to_cube(orig)
        dq_x, dq_y, dq_z = to_cube(dest)
        return max(abs(oq_x - dq_x), abs(oq_y - dq_y), abs(oq_z - dq_z))

    def valid_cell(self, q_r):
        q, r = q_r
        if q < 0 or q >= self.cols:
            return False
        if r < 0 or r >= self.rows:
            return False
        return True

    def neighbors(self, cell):
        """valid cells neighboring the provided cell"""
        cell_q = to_cube(cell)
        rval = map(from_cube, [
            (cell_q[0] + x, cell_q[1] + y, cell_q[2] + z)
            for x, y, z in [
                (-1, +1, 0), #W
                (0, +1, -1), #NW
                (+1, 0, -1), #NE
                (+1, -1, 0), #E
                (0, -1, +1), #SE
                (-1, 0, +1), #SW
            ]
        ])
        # TODO: might want to check for negative coordinates and provide a flag for wrapping
        return filter(self.valid_cell, rval)


## MAIN

if __name__ == '__main__':
    m = HexMap(10, 5)
    print("m:", m)
    print("len(m):", len(m))
    print("m[0, 0]:", m[0, 0])

    n = list(m.neighbors((2, 2)))
    print("neighbors((2, 2)):", n)
    print("valid_cell", list(map(m.valid_cell, n)))
    print("distance", list(map(m.distance, n, [(2, 2)] * len(n))))

## EOF
