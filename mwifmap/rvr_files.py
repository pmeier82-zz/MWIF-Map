# -*- coding: utf-8 -*-

"""river and rail (Delphi) code from Steve"""

import os
from mwifmap.util import *

__author__ = "pmeier82"

BASE_PATH = SETTINGS["filesystem"]["basepath"]
RVR_FILE = os.path.join(BASE_PATH, "Bitmaps", "AggregateRiverLake.RVR")
HEX_HEIGHT = 152
HEX_WIDTH = 136


def get_px_data(inp, background=None):
    if background is None:
        background = (0, 0, 0, 0)
    inp = int(inp)
    mask = [
        (inp & 0xc000) >> 14,
        (inp & 0x3000) >> 12,
        (inp & 0x0c00) >> 10,
        (inp & 0x0300) >> 8,
        (inp & 0x00c0) >> 6,
        (inp & 0x0030) >> 4,
        (inp & 0x000c) >> 2,
        (inp & 0x0003)]
    COL = {
        0: background,
        1: (170, 203, 244, 255),  # lake #aacbe0
        2: (61, 120, 188, 255),  # lake bank #3d78bc
        3: (61, 120, 188, 255),  # river #3d78bc
    }
    return tuple(COL[m] for m in mask)


def process_rvr_line(line, background=None):
    """process a line from the RVR file

    based on Steve's forum post at http://www.matrixgames.com/forums/tm.asp?m=3711575&mpage=1&key=&#3734625
    """

    ## init
    if background is None:
        background = (0, 0, 0, 0)
    else:
        if not isinstance(background, (list, tuple)):
            raise ValueError("background has to be None or RGBA-tuple")
        if not len(background) == 4:
            raise ValueError("background has to be None or RGBA-tuple")
        background = tuple(background)
    rval = Image.new("RGBA", (HEX_WIDTH, HEX_HEIGHT), background)
    px_data = rval.load()

    ## reconstruct
    ROWS = line.strip().split(";")
    hex_r, hex_q = [int(item) for item in ROWS.pop(0).split(",")]
    # XXX: (r,q) in that order!!
    for row_num, row in enumerate(ROWS):
        # we should find 152 row entries here, checking in case
        if not row:
            continue
        assert 0 <= row_num < 152, "more than 153 entries for river/lake hex"
        ITEMS = row.split(",")

        row_pixel_count = 0
        for item in ITEMS:
            if not item:
                continue
            if "A" <= item <= "Q":
                # letters are blank pixels strips of length 8 *(ord(letter)-ord("A")+1)
                row_pixel_count += (ord(item) - 64) * 8
            else:
                # numbers coloured pixel strips (of length 8)
                px_data_seq = get_px_data(item)
                for i, px in enumerate(px_data_seq):
                    try:
                        px_data[row_pixel_count + i, row_num] = px
                    except Exception as ex:
                        print(ex)
                        print("problem @ rc({}),rpc({})+i({})".format(row_num, row_pixel_count, i))
                row_pixel_count += 8
        assert row_pixel_count == 136, "pixel count is: {}".format(row_pixel_count)

    ## return
    return (hex_q, hex_r), rval


if __name__ == "__main__":
    ## open file and read in as string
    LINES = None
    with open(RVR_FILE, "r") as fp:
        LINES = fp.readlines()

    entry = 4000
    print(LINES[entry])
    (q, r), pic = process_rvr_line(LINES[entry])
    pic.show()
