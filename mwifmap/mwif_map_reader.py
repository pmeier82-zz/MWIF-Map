"""reader for MWIF map data

MWIF data uses a R-Q format for indexing cells! The map has a pointy hat, odd row offset grid. Rows are
counted top to bottom, columns are counted left to right. Most of the keys and codes are extracted from
the back of the Player's Manual Vol. 2, and have been adjusted to match reality where necessary.
"""

## IMPORTS

import os
from hexmap import HexMap
from ConfigParser import ConfigParser

## CONSTANTS

cp = ConfigParser()
cp.read(["settings.cfg", "./settings.cfg", "./mwifmap/settings.cfg"])
BASE_PATH = cp.get("filesystem", "basepath")
del cp

MAP_DIR = os.path.join(BASE_PATH, "Data", "Map Data")
MAP_NAME = "Standard Map"

FILE_ADJ = "{map_name} ADJ.CSV" # adjacency map for sea zones
FILE_ALT = "{map_name} ALT.CSV" # alternate control record
FILE_COA = "{map_name} COA.CSV" # coastal data
FILE_HST = "{map_name} HST.CSV" # hex side data
FILE_NAM = "{map_name} NAM.CSV" # label data
FILE_RLS = "{map_name} RLS.CSV" # river/lake special graphic hexes
FILE_SEA = "{map_name} SEA.CSV" # sea area data
FILE_TER = "{map_name} TER.CSV" # hex terrain data

COLS = 360
ROWS = 195

TER_CODE = {
    0: "all sea",
    1: "lake",
    2: "clear",
    3: "forest",
    4: "jungle",
    5: "mountain",
    6: "swamp",
    7: "desert",
    8: "desert mountain",
    9: "tundra",
    10: "ice",
    11: "quattara depression"
}
WZ_CODE = {
    0: "ARC",
    1: "NTP",
    2: "MED",
    3: "NMS",
    4: "SMS",
    5: "STP",
}
CITY_CODE = {
    0: "no city",
    1: "city",
    2: "capital, minor country",
    3: "capital, major power",
}
PORT_CODE = {
    0: "no port",
    1: "minor port",
    2: "major port",
}
FACTORY_CODE = {
    # red,blue
    0: (0, 0),
    1: (1, 0),
    2: (0, 1),
    4: (1, 1),
    9: (1, 2),
    15: (3, 0),
}

## CLASSES

class MWIFMapReader(object):
    """map reader for matrix games MWIF"""

    def __init__(self, map_dir=None, map_name=None):
        self.map_dir = map_dir or MAP_DIR
        self.map_name = map_name or MAP_NAME
        self.map = HexMap(COLS, ROWS)

        # read flags
        self.read_ter = False

    def load_ter(self, map_dir=None, map_name=None, verbose=False):
        """read in TER file"""

        # init
        dir_name = map_dir or self.map_dir
        file_name = FILE_TER.format(map_name=map_name or self.map_name)
        open_path = os.path.join(dir_name, file_name)
        cells_read = set()
        if verbose:
            print "reading {} cells from \"{}\"".format(COLS * ROWS, open_path)

        # read loop
        with open(open_path, "r") as fp:
            for i, read_line in enumerate(fp.readlines()):
                try:
                    # prepare the line and find the cell index
                    items = read_line.strip().split(",")
                    if len(items) < 15:
                        raise ValueError("less than 15 items on line!")
                    r, q = int(items.pop(0)), int(items.pop(0))
                    # XXX: (r,q) in that order!!
                    cells_read.add((q, r))
                    entry = self.map[(q, r)]

                    # process information
                    entry["ter_code"] = int(items.pop(0))
                    entry["wz_id"] = int(items.pop(0))
                    try:
                        entry["sz_id"] = int(items.pop(0))
                        # all sea hex: stop here
                        continue
                    except:
                        # land hex: move on
                        pass

                    # land hex extra
                    entry["country_id"] = int(items.pop(0))
                    try:
                        entry["oil"] = int(items.pop(0))
                    except:
                        pass
                    try:
                        entry["res"] = int(items.pop(0))
                    except:
                        pass
                    entry["is_objective"] = bool(int(items.pop(0)))
                    entry["city"] = int(items.pop(0))
                    entry["port"] = int(items.pop(0))
                    entry["is_iced_in"] = bool(int(items.pop(0)))
                    entry["factory"] = int(items.pop(0))
                    try:
                        entry["label"] = int(items.pop(0))
                    except:
                        pass
                    try:
                        entry["region"] = int(items.pop(0))
                    except:
                        pass
                except Exception, ex:
                    if verbose:
                        print "Error reading line #{}: {}".format(i, str(ex))
                        print "Lines was: {}".format(repr(read_line))

        # finish
        success = len(cells_read) == COLS * ROWS
        if verbose:
            print "read {} cells:".format(len(cells_read)),
            print {True: "ALL DONE!", False: "ERROR!"}.get(success)
        return success

## MAIN

if __name__ == "__main__":
    mr = MWIFMapReader()
    mr.load_ter(verbose=True)
    print mr.map[0, 0]
    print mr.map[0, 0]._data
    print dir(mr.map[0, 0])

