"""reader for MWIF map data

MWIF data uses a R-Q format for indexing cells! The map has a pointy hat, odd row offset grid. Rows are
counted top to bottom, columns are counted left to right. Most of the keys and codes are extracted from
the back of the Player's Manual Vol. 2, and have been adjusted to match reality where necessary.
"""


## IMPORTS

import os
from mwifmap.mwif_hexmap import HexMap
from mwifmap.util import *


## CONSTANTS

BASE_PATH = SETTINGS["filesystem"]["basepath"]
MAP_DIR = os.path.join(BASE_PATH, "Data", "Map Data")
MAP_NAME = "Standard Map"
CODEC = "iso8859_15"

# map data
FILE_ADJ = "{map_name} ADJ.CSV"  # adjacency map for sea zones
FILE_ALT = "{map_name} ALT.CSV"  # alternate control record
FILE_COA = "{map_name} COA.CSV"  # coastal data
FILE_HST = "{map_name} HST.CSV"  # hex side data
FILE_NAM = "{map_name} NAM.CSV"  # label data
FILE_RLS = "{map_name} RLS.CSV"  # river/lake special graphic hexes
FILE_SEA = "{map_name} SEA.CSV"  # sea area data
FILE_TER = "{map_name} TER.CSV"  # hex terrain data
# country data
FILE_CMA = "{map_name} CMa.CSV"  # country data - major powers
FILE_CMI = "{map_name} CMi.CSV"  # country data - minor countries
FILE_CSU = "{map_name} CSu.CSV"  # country data - sub countries
FILE_CGA = "{map_name} CGA.CSV"  # country data - governed areas

COLS = 359
ROWS = 194

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
HST_CODE = {
}


## CLASSES

class MWIFMapReader(object):
    """map reader for matrix games MWIF"""

    def __init__(self, map_dir=None, map_name=None):
        self.map_dir = map_dir or MAP_DIR
        self.map_name = map_name or MAP_NAME
        self.map = HexMap(COLS, ROWS)

    def load_ter_data(self, map_dir=None, map_name=None, verbose=False):
        """read in TER file"""

        # init
        dir_name = map_dir or self.map_dir
        file_name = FILE_TER.format(map_name=map_name or self.map_name)
        open_path = os.path.join(dir_name, file_name)
        ter_rec_read = set()
        nam_rec_read = set()
        if verbose:
            print("reading ter and nam data")

        NAM = open(
            os.path.join(
                dir_name,
                FILE_NAM.format(map_name=map_name or self.map_name)),
            "r").readlines()

        # read loop
        with open(open_path, "r") as fp:
            for line_no, read_line in enumerate(fp):
                try:
                    # prepare the line and find the cell index
                    items = read_line.strip().split(",")
                    assert len(items) == 15, "ter record does not have exactly 15 entries"
                    r, q = int(items.pop(0)), int(items.pop(0))
                    # XXX: (r,q) in that order!!
                    ter_rec_read.add((q, r))
                    entry = self.map[(q, r)]

                    # process information
                    entry["ter_code"] = int(items.pop(0))
                    entry["wz_id"] = int(items.pop(0))
                    try:
                        sz_id = int(items.pop(0))
                        entry["sz_id"] = sz_id
                        # all sea hex: stop here
                        continue
                    except:
                        # land hex: move on
                        pass

                    # land hex extra
                    entry["country_id"] = int(items.pop(0))
                    try:
                        entry["res"] = - int(items.pop(0)), 0
                        # got an oil here
                    except:
                        pass
                    try:
                        entry["res"] = int(items.pop(0)), 0
                        # got a resource here
                    except:
                        pass
                    entry["obj"] = bool(int(items.pop(0)))
                    entry["cty"] = int(items.pop(0)), 0
                    entry["prt"] = int(items.pop(0)), 0
                    entry["ice"] = bool(int(items.pop(0)))
                    entry["fac"] = int(items.pop(0)), 0
                    try:
                        lbl_idx = int(items.pop(0))
                        if lbl_idx == -1:
                            raise LookupError
                        # prepare the line and find the cell index
                        items_nam = NAM[lbl_idx].strip().split(",", 11)
                        assert len(items_nam) == 12, "nam record does not have exactly 12 items"
                        assert int(items_nam.pop(0)) == lbl_idx, "label id does not match"
                        nam_rec_read.add(lbl_idx)
                        # label hex and offset
                        lbl_q, lbl_r = int(items_nam.pop(0)), int(items_nam.pop(0))
                        # XXX: (q,r) in that order!!
                        lbl_offset = int(items_nam.pop(0)), int(items_nam.pop(0))

                        # feature positions
                        cty_pos = int(items_nam.pop(0))
                        if cty_pos != 0:
                            entry["cty"] = entry["cty"][0], cty_pos
                        prt_pos = int(items_nam.pop(0))
                        if prt_pos != 0:
                            entry["prt"] = entry["prt"][0], prt_pos
                        fac_pos = int(items_nam.pop(0))
                        if fac_pos != 0:
                            entry["fac"] = entry["fac"][0], fac_pos
                        res_pos = int(items_nam.pop(0))
                        if res_pos != 0:
                            entry["res"] = entry["res"][0], res_pos

                        # label details
                        lbl_col_code = int(items_nam.pop(0))
                        lbl_siz_code = int(items_nam.pop(0))
                        lbl_text = items_nam.pop(0).split(",")[0].strip()
                        if lbl_text != "None":
                            lbl_entry = self.map[lbl_q, lbl_r]
                            if "labels" not in lbl_entry:
                                lbl_entry["labels"] = []
                            lbl_entry["labels"].append((lbl_text, lbl_offset, lbl_siz_code, lbl_col_code))
                    except LookupError:
                        pass
                    except Exception as ex:
                        print("NAM.1 issue (#{}): {}\n{}".format(lbl_idx, str(ex), NAM[lbl_idx]))
                    try:
                        entry["region"] = int(items.pop(0))
                    except:
                        pass
                except Exception as ex:
                    if read_line == "\x1a":
                        # ascii 26 == EOF
                        continue
                    if verbose:
                        print("TER issue (#{}): {}\n{}".format(line_no, str(ex), read_line))

        # hit nam records that had not been referenced
        print("processing unreferenced nam records")
        for nam_idx in range(len(NAM)):
            if nam_idx in nam_rec_read:
                continue
            try:
                items_nam = NAM[nam_idx].strip().split(",", 11)
                assert len(items_nam) == 12, "nam record does not have exactly 12 items"
                assert int(items_nam.pop(0)) == nam_idx, "label id does not match"
                nam_rec_read.add(nam_idx)
                # label hex and offset
                q, r = int(items_nam.pop(0)), int(items_nam.pop(0))
                # XXX: (q,r) in that order!!
                entry = self.map[q, r]
                lbl_offset = int(items_nam.pop(0)), int(items_nam.pop(0))
                # feature positions
                # if "sz_id" in entry:
                [items_nam.pop(0) for _ in [0, 1, 2, 3]]
                # else:
                #     cty_pos = int(items_nam.pop(0))
                #     if cty_pos != 0:
                #         entry["cty"] = entry["cty"][0], cty_pos
                #     prt_pos = int(items_nam.pop(0))
                #     if prt_pos != 0:
                #         entry["prt"] = entry["prt"][0], prt_pos
                #     fac_pos = int(items_nam.pop(0))
                #     if fac_pos != 0:
                #         entry["fac"] = entry["fac"][0], fac_pos
                #     res_pos = int(items_nam.pop(0))
                #     if res_pos != 0:
                #         entry["res"] = entry["res"][0], res_pos

                # label details
                lbl_col_code = int(items_nam.pop(0))
                lbl_siz_code = int(items_nam.pop(0))
                lbl_text = items_nam.pop(0).split(",")[0].strip()
                if lbl_text != "None":
                    if "labels" not in entry:
                        entry["labels"] = []
                    entry["labels"].append((lbl_text, lbl_offset, lbl_siz_code, lbl_col_code))
            except Exception as ex:
                if read_line == "\x1a":
                    # ascii 26 == EOF
                    continue
                print("NAM.2 issue (#{}): {}\n{}".format(nam_idx, str(ex), NAM[nam_idx]))

        # finish
        success = len(ter_rec_read) == COLS * ROWS and len(nam_rec_read) == 3754
        if verbose:
            print("read {} ter records".format(len(ter_rec_read)))
            print("read {} nam records".format(len(nam_rec_read)))
        return success

    def load_coa_data(self, coastal_dir=None, verbose=False):
        """read in coastal bitmap info to flag cells when they get a bitmap"""

        dir_name = coastal_dir or os.path.join(BASE_PATH, "Bitmaps", "Coastal Bitmaps")
        cells_read = set()
        success = True
        if verbose:
            print("reading coastal bitmap data")

        try:
            for page in [1, 2, 3, 4, 5, 6, 7, 8]:
                with open(os.path.join(dir_name, "Page{:02d}.txt".format(page)), "r") as fp:
                    if verbose:
                        print("reading file: \"{}\"".format(os.path.basename(fp.name)))
                    for row, line in enumerate(fp):
                        items = line.strip().split(",")[:-1]
                        col = 0
                        while len(items) > 1:
                            r, q = int(items.pop(0)), int(items.pop(0))
                            cells_read.add((q, r))
                            entry = self.map[(q, r)]
                            entry["coastal_bitmap"] = (page, row, col)
                            col += 1
        except Exception as ex:
            print("Error reading coastal files! {}".format(ex))
            success = False

        # finish
        if verbose:
            print("read {} cells:".format(len(cells_read)), end=' ')
        return success

    def load_hst_data(self, map_dir=None, map_name=None, verbose=False):
        """read in HST file"""

        # init
        dir_name = map_dir or self.map_dir
        file_name = FILE_HST.format(map_name=map_name or self.map_name)
        open_path = os.path.join(dir_name, file_name)
        success = True
        if verbose:
            print("reading hexsides from \"{}\"".format(open_path))

        # read loop
        with open(open_path, "r") as fp:
            for i, read_line in enumerate(fp):
                try:
                    # prepare the line and find the cell index
                    items = read_line.strip().split(",")
                    if len(items) < 4:
                        raise ValueError("less than 4 items on line!")
                    r, q = int(items.pop(0)), int(items.pop(0))
                    # XXX: (r,q) in that order!!
                    entry = self.map[(q, r)]
                    if "hexsides" not in entry:
                        entry["hexsides"] = []
                    kind_code = str(items.pop(0))
                    hst_code = int(items.pop(0))
                    entry["hexsides"].append((kind_code, hst_code))
                except Exception as ex:
                    if read_line == "\x1a":
                        # ascii 26 == EOF
                        continue
                    if verbose:
                        print("Error reading line #{}: {}".format(i, str(ex)))
                        print("Line was: {}".format(repr(read_line)))
        return success

    def load_sea_adj_data(self, map_dir=None, map_name=None, verbose=False):
        """read in COA file"""

        # init
        dir_name = map_dir or self.map_dir
        file_name = FILE_COA.format(map_name=map_name or self.map_name)
        open_path = os.path.join(dir_name, file_name)
        success = True
        if verbose:
            print("reading coastal data from \"{}\"".format(open_path))

        # read loop
        with open(open_path, "r") as fp:
            for i, read_line in enumerate(fp):
                try:
                    # prepare the line and find the cell index
                    items = read_line.strip().split(",")
                    if len(items) < 4:
                        raise ValueError("less than 4 items on line!")
                    q, r = int(items.pop(0)), int(items.pop(0))
                    # XXX: (q,r) in that order!!
                    entry = self.map[(q, r)]
                    if "sz_adj" not in entry:
                        entry["sz_adj"] = []
                    n_sz = int(items.pop(0))
                    for i in range(n_sz):
                        entry["sz_adj"].append(int(items.pop(0)))
                except Exception as ex:
                    if read_line == "\x1a":
                        # ascii 26 == EOF
                        continue
                    if verbose:
                        print("Error reading line #{}: {}".format(i, str(ex)))
                        print("Line was: {}".format(repr(read_line)))
        for cell in self.map.values():
            if "sz_id" in cell:
                continue
            for q, r in self.map.neighbors(cell.key()):
                if "sz_id" in self.map[q, r]:
                    if "sz_adj" not in cell:
                        cell["sz_adj"] = []
                    adj_id = self.map[q, r]["sz_id"]
                    if adj_id not in cell["sz_adj"]:
                        cell["sz_adj"].append(adj_id)
        return success

    def gen_border_data(self, verbose=False):
        """generate border data, has to be done after input all files have been read!"""

        # national borderlines
        nat_border = get_border_line(self.map, "country_id")
        for (q, r), sides in nat_border:
            try:
                entry = self.map[(q, r)]
                if "borders" not in entry:
                    entry["borders"] = []
                entry["borders"].append(("nat", sides))
            except Exception as ex:
                if verbose is True:
                    print("problem adding national border: {}".format(ex))

        # weather borderlines
        wea_border = get_border_line(self.map, "wz_id")
        for (q, r), sides in wea_border:
            try:
                entry = self.map[(q, r)]
                if "borders" not in entry:
                    entry["borders"] = []
                entry["borders"].append(("wea", sides))
            except Exception as ex:
                if verbose is True:
                    print("problem adding weather border: {}".format(ex))

        # sea zone borderlines
        sea_border = get_border_line(self.map, "sz_id")
        for (q, r), sides in sea_border:
            try:
                entry = self.map[(q, r)]
                if "borders" not in entry:
                    entry["borders"] = []
                entry["borders"].append(("sea", sides))
            except Exception as ex:
                if verbose is True:
                    print("problem adding sea zone border: {}".format(ex))


## FUNCTIONS

def border_indicator(c, hm, field_name, field_ids):
    if field_name in hm[c]:
        if hm[c][field_name] in field_ids:
            return False
        else:
            return True
    else:
        # sea hex
        return False


def encode_hexsides(l):
    rval = 0
    for ex, co in enumerate(l):
        rval += co * 2 ** ex
    return rval


def get_border_line(hm, field_name, field_ids=None):
    border = []
    for cell in hm.values():
        if field_name not in cell:
            continue
        if field_ids:
            if cell[field_name] not in field_ids:
                continue

        neighbors = hm.neighbors((cell.q, cell.r))
        # order:  W,  NW, NE, E,  SE, SW - dir
        check_ids = field_ids or [cell[field_name]]
        hsc = encode_hexsides([border_indicator(n, hm, field_name, check_ids) for n in neighbors])
        if hsc != 0:
            border.append((cell.key(), hsc))
    return border


## MAIN

if __name__ == "__main__":
    VERBOSE = True
    m = MWIFMapReader()
    m.load_ter_data(verbose=VERBOSE)
    m.load_coa_data(verbose=VERBOSE)
    m.load_hst_data(verbose=VERBOSE)
    m.load_sea_adj_data(verbose=VERBOSE)
    m.gen_border_data(verbose=VERBOSE)
    print(m.map[10, 0])
    print(m.map[10, 0]._data)
    print(dir(m.map[10, 0]))

## EOF
