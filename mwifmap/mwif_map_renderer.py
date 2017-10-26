"""render map using `svgwrite`"""

## IMPORTS

import os
import svgwrite
# import scipy as sp
from scipy import interp

from mwifmap.mwif_map_reader import MWIFMapReader
from mwifmap.rvr_files import process_rvr_line
from mwifmap.util import *


## CLASSES

class MapDrawing(object):
    """wrapper to render the map to svg/png"""

    def __init__(self, map_reader=None, filename=None, scale=None, region=None, background="default"):
        # map reader
        self.map_reader = map_reader
        if self.map_reader is None:
            raise ValueError("No map was passed to {}".format(self.__class__.__name__))

        # filename
        self.svg_name = filename or "test"
        if not self.svg_name.endswith(".svg"):
            self.svg_name += ".svg"

        # scale
        self.scale = float(scale or 1.0)

        # region
        self.region = [0, 0, self.map_reader.map.cols - 1, self.map_reader.map.rows - 1]
        if region is not None:
            self.region = [
                region[0] or self.region[0],
                region[1] or self.region[1],
                region[2] or self.region[2],
                region[3] or self.region[3]]
        self.region = tuple(self.region)

        # background
        self.background = background
        if self.background == "default":
            self.background = SETTINGS["colour"]["background"]

        # sizes
        w = self.region[2] - self.region[0] + 1
        h = self.region[3] - self.region[1] + 1
        hex_w, hex_h = get_hex_dims(self.scale)
        self.svg_width = (w + .5) * hex_w
        self.svg_height = (h * .75 + .25) * hex_h

        # other members
        self.layers = []

        # build svg
        self.svg = svgwrite.Drawing(
            filename=self.svg_name,
            size=(self.svg_width, self.svg_height),
            profile="full",
            debug=True)

    def add_layer(self, layer_cls, index=None, *args, **kwargs):
        if not index:
            self.layers.append(layer_cls(self, *args, **kwargs))
        else:
            self.layers.insert(index, layer_cls(self, *args, **kwargs))

    def render(self, finalise=True):
        print("Rendering {} ({}x{})".format(self.svg_name, self.svg_width, self.svg_height))
        if self.background is not None:
            bg = self.svg.rect(
                id="background",
                size=("100%", "100%"),
                fill=self.background)
            self.svg.add(bg)
        for renderer in self.layers:
            renderer.render()
        if finalise is True:
            self.finalise()

    def finalise(self):
        print("finalising..", end=' ')
        print()
        self.svg.saveas(self.svg_name)
        print("DONE!")


class BaseLayer(object):
    def __init__(self, parent, *args, **kwargs):
        # set parent
        self.parent = parent
        # set shortcuts
        self.map = self.parent.map_reader.map
        self.svg = self.parent.svg
        self.layer = None
        self.scale = self.parent.scale
        self.region = self.parent.region

    def render(self, *args, **kwargs):
        self.layer = self.svg.g(id=self.__class__.__name__)
        self._render(*args, **kwargs)
        self.svg.add(self.layer)
        print("{} finished!".format(self.__class__.__name__))

    def _render(self, *args, **kwargs):
        raise NotImplementedError

    def hex_points(self, q, r, scale=None):
        left, top = self.hex_origin(q, r, scale)
        return [(x + left, y + top) for x, y in get_hex_proto(scale or self.scale)]

    def hex_origin(self, q, r, scale=None):
        # calc points - alternate the offset of the cells based on row
        hex_w, hex_h = get_hex_dims(scale or self.scale)
        left = (hex_w / 2 if r % 2 else 0) + (q - self.parent.region[0]) * hex_w + 1
        top = .75 * (r - self.parent.region[1]) * hex_h + 1
        return left, top


class TerrainLayer(BaseLayer):
    def __init__(self, parent, *args, **kwargs):
        super(TerrainLayer, self).__init__(parent, *args, **kwargs)
        self.simple = bool(kwargs.pop("simple", False))
        self.TER_CODE = {}
        if self.simple is False:
            self.TER_BMP = {
                0: Image.open(os.path.join(
                    SETTINGS["filesystem"]["basepath"],
                    "Bitmaps", "Terrain Bitmaps",
                    "Sea.bmp")),
                1: Image.open(os.path.join(
                    SETTINGS["filesystem"]["basepath"],
                    "Bitmaps", "Terrain Bitmaps",
                    "Lake.bmp")),
                2: Image.open(os.path.join(
                    SETTINGS["filesystem"]["basepath"],
                    "Bitmaps", "Terrain Bitmaps",
                    "Clear.bmp")),
                3: Image.open(os.path.join(
                    SETTINGS["filesystem"]["basepath"],
                    "Bitmaps", "Terrain Bitmaps",
                    "Forest.bmp")),
                4: Image.open(os.path.join(
                    SETTINGS["filesystem"]["basepath"],
                    "Bitmaps", "Terrain Bitmaps",
                    "Jungle.bmp")),
                5: Image.open(os.path.join(
                    SETTINGS["filesystem"]["basepath"],
                    "Bitmaps", "Terrain Bitmaps",
                    "Mountain.bmp")),
                6: Image.open(os.path.join(
                    SETTINGS["filesystem"]["basepath"],
                    "Bitmaps", "Terrain Bitmaps",
                    "swamp.bmp")),
                7: Image.open(os.path.join(
                    SETTINGS["filesystem"]["basepath"],
                    "Bitmaps", "Terrain Bitmaps",
                    "Desert.bmp")),
                8: Image.open(os.path.join(
                    SETTINGS["filesystem"]["basepath"],
                    "Bitmaps", "Terrain Bitmaps",
                    "Desert Mountain.bmp")),
                9: Image.open(os.path.join(
                    SETTINGS["filesystem"]["basepath"],
                    "Bitmaps", "Terrain Bitmaps",
                    "Tundra.bmp")),
                10: Image.open(os.path.join(
                    SETTINGS["filesystem"]["basepath"],
                    "Bitmaps", "Terrain Bitmaps",
                    "Ice.bmp")),
                11: Image.open(os.path.join(
                    SETTINGS["filesystem"]["basepath"],
                    "Bitmaps", "Terrain Bitmaps",
                    "Qattara Depression.bmp")),
            }
            for i in range(len(self.TER_BMP)):
                if self.scale != 1.0:
                    self.TER_BMP[i] = pil_img_resize(self.TER_BMP[i], self.scale)
                # create pattern
                img_data, img_dims = pil_img_to_b64_png(self.TER_BMP[i])
                img_node = self.svg.image(
                    "data:image/png;base64,{}".format(img_data),
                    size=img_dims,
                    id="TI{:02d}".format(i))
                pat_node = self.svg.pattern(
                    size=(1, 1),
                    id="TP{:02d}".format(i),
                    patternUnits="objectBoundingBox")
                pat_node.add(img_node)
                self.svg.defs.add(pat_node)
        else:
            for i in range(12):
                self.TER_CODE[i] = SETTINGS["colour"]["ter{:02d}".format(i)]

    def _render(self, *args, **kwargs):
        for cell in self.map.values():
            # region check
            if cell.q < (self.parent.region[0] or 0) or cell.q > (self.parent.region[2] or 9999):
                continue
            if cell.r < (self.parent.region[1] or 0) or cell.r > (self.parent.region[3] or 9999):
                continue

            if self.simple is True:
                # draw the polygon onto the surface
                this_hex = self.svg.polygon(
                    points=self.hex_points(cell.q, cell.r),
                    fill=self.TER_CODE[cell["ter_code"]])
                self.layer.add(this_hex)
            else:
                if not "coastal_bitmap" in cell:
                    this_hex = self.svg.polygon(
                        points=self.hex_points(cell.q, cell.r),
                        fill="url(#TP{:02d})".format(cell["ter_code"]))
                    self.layer.add(this_hex)


class CoastalLayer(BaseLayer):
    def __init__(self, parent, *args, **kwargs):
        super(CoastalLayer, self).__init__(parent, *args, **kwargs)
        self.simple = bool(kwargs.pop("simple", False))
        if self.simple is False:
            # load data files
            self.PAGE_DATA = {}
            for page in range(1, 9):
                self.PAGE_DATA[page] = Image.open(
                    os.path.join(
                        SETTINGS["filesystem"]["basepath"],
                        "Bitmaps", "Coastal Bitmaps",
                        "Page{:02d}.bmp".format(page)))

    def _render(self, *args, **kwargs):
        if self.simple is True:
            self.layer.style = \
                "font-size:36;" \
                "font-family:Verdana, Helvetica, Arial, sans-serif;" \
                "font-weight:bold;" \
                "font-style:oblique;" \
                "fill:black"
        for cell in self.map.values():
            # region check
            if cell.q < (self.parent.region[0] or 0) or cell.q > (self.parent.region[2] or 9999):
                continue
            if cell.r < (self.parent.region[1] or 0) or cell.r > (self.parent.region[3] or 9999):
                continue

            if "coastal_bitmap" in cell:
                if self.simple is True:
                    # draw a "C" into the coastal hexes
                    points = self.hex_points(cell.q, cell.r)
                    x = points[0][0]
                    y = points[1][1] + (points[2][1] - points[1][1]) / 2
                    txt = self.svg.text("C", insert=(x, y), text_anchor="middle")
                    self.layer.add(txt)
                else:
                    # get the hex image
                    page, row, idx = cell["coastal_bitmap"]
                    hex_w, hex_h = get_hex_dims(1.0)
                    dx1_pat = int((hex_w / 2 if row % 2 else 0) + idx * hex_w)
                    dx2_pat = int(dx1_pat + hex_w)
                    dy1_pat = int(.75 * row * hex_h)
                    dy2_pat = int(dy1_pat + hex_h)
                    hex_img = self.PAGE_DATA[page].crop(
                        (dx1_pat, dy1_pat, dx2_pat, dy2_pat))
                    if self.scale != 1.0:
                        hex_img = pil_img_resize(hex_img, self.scale)
                    hex_img_data, hex_img_dims = pil_img_to_b64_png(hex_img)
                    del hex_img
                    # create pattern
                    img_node = self.svg.image(
                        "data:image/png;base64,{}".format(hex_img_data),
                        size=hex_img_dims,
                        id="CI{}{:02d}{:02d}".format(page, row, idx))
                    pat_node = self.svg.pattern(
                        size=(1, 1),
                        id="CP{}{:02d}{:02d}".format(page, row, idx),
                        patternUnits="objectBoundingBox")
                    pat_node.add(img_node)
                    self.svg.defs.add(pat_node)
                    # create hex
                    hex = self.svg.polygon(
                        points=self.hex_points(cell.q, cell.r),
                        fill="url(#CP{}{:02d}{:02d})".format(page, row, idx))
                    self.layer.add(hex)


class RVRLayer(BaseLayer):
    def __init__(self, parent, *args, **kwargs):
        super(RVRLayer, self).__init__(parent, *args, **kwargs)
        file_name = os.path.join(
            SETTINGS["filesystem"]["basepath"],
            "Bitmaps",
            "AggregateRiverLake.RVR")
        self.RVR_DATA = {}
        with open(file_name, "r") as fp:
            for line in fp.readlines():
                (q, r), img = process_rvr_line(line)
                self.RVR_DATA[q, r] = img

    def _render(self, *args, **kwargs):
        for cell in self.map.values():
            # region check
            if cell.q < (self.parent.region[0] or 0) or cell.q > (self.parent.region[2] or 99999):
                continue
            if cell.r < (self.parent.region[1] or 0) or cell.r > (self.parent.region[3] or 99999):
                continue

            if (cell.q, cell.r) in self.RVR_DATA:
                # get the hex image
                hex_img = self.RVR_DATA[cell.q, cell.r]
                hex_img = pil_img_resize(hex_img, self.scale)
                hex_img_data, hex_img_dims = pil_img_to_b64_png(hex_img)
                del hex_img
                # create pattern
                img_node = self.svg.image(
                    "data:image/png;base64,{}".format(hex_img_data),
                    size=hex_img_dims,
                    id="RLI{:03d}{:02d}".format(*cell.key()))
                pat_node = self.svg.pattern(
                    size=(1, 1),
                    id="RLP{:03d}{:02d}".format(*cell.key()),
                    patternUnits="objectBoundingBox")
                pat_node.add(img_node)
                self.svg.defs.add(pat_node)
                # create hex
                hex = self.svg.polygon(
                    points=self.hex_points(cell.q, cell.r),
                    fill="url(#RLP{:03d}{:02d})".format(*cell.key()))
                self.layer.add(hex)


class RailLayer(BaseLayer):
    """layer for rails and roads, features connecting two hexes across their common hexside"""

    def __init__(self, parent, *args, **kwargs):
        super(RailLayer, self).__init__(parent, *args, **kwargs)
        self.rail_style = kwargs.get("base_rail", (("#555555", 6), ("#d7d7d7", 4)))

    def find_rail_rout_for_cell(self, cell, off=None):
        if off is None:
            off = 0.0, 0.0
        x, y = self.hex_origin(cell.q, cell.r)
        clock_pos = -1

        # icon gravity
        if cell["cty"][0] != 0 and clock_pos == -1:
            clock_pos = cell["cty"][1]
        if cell["prt"][0] != 0 and clock_pos == -1:
            clock_pos = cell["prt"][1]
        if cell["res"][0] != 0 and clock_pos == -1:
            clock_pos = cell["res"][1]
        # non-icon gravity
        if cell["cty"][0] == 0 and cell["cty"][1] != 0 and clock_pos == -1:
            clock_pos = cell["cty"][1]

        ## non icon-gravity
        if clock_pos == -1:
            ## check surround of the hex for all-sea hexsides
            surround = [self.map[coord] for coord in self.map.neighbors(cell.key())]
            has_coast = [c["ter_code"] < 2 for c in surround]
            for hs_kind, hs_code in cell["hexsides"]:
                if hs_kind == "Co":
                    for side in range(6):
                        has_coast[side] = has_coast[side] or hs_code & 2 ** side > 0

            # coastal hex without icon gravity
            if any(has_coast):
                if sum(has_coast) == 1:
                    # ONE COASTAL HEXSIDE
                    for side in range(6):
                        if has_coast[side]:
                            # 0, 1, 2, 3, 4, 5 - - > 3, 5, 7, 9, 11, 1
                            clock_pos = (((side * 2) + 3) % 12)
                            clock_pos += 12
                elif sum(has_coast) == 2:
                    # TWO COASTAL HEXSIDES
                    small_s = has_coast.index(True)
                    large_s = has_coast.index(True, small_s + 1)

                    if large_s - small_s == 3:
                        # opposite
                        clock_pos = 0
                    else:
                        # not opposite
                        if large_s - small_s < 3:
                            clock_pos = large_s + small_s + 3
                        else:
                            clock_pos = large_s + small_s - 3
                elif sum(has_coast) == 3:
                    # THREE COASTAL HEXSIDES
                    coast_sides = [i for i, v in enumerate(has_coast) if v is True]
                    if coast_sides[0] % 2 == coast_sides[1] % 2 == coast_sides[2] % 2:
                        # all even or all odd means centered gravity
                        clock_pos = 0
                    else:
                        if sum(coast_sides) % 3 == 0:
                            # all adjacent
                            clock_pos = {
                                0: 3,
                                1: 5,
                                2: 7,
                                3: 9,
                                4: 11,
                                5: 1,
                            }[coast_sides[1]]
                        else:
                            if (coast_sides[2] - coast_sides[1]) == 3:
                                clock_pos = ((coast_sides[0] * 2) + 3) % 12
                            elif (coast_sides[2] - coast_sides[0]) == 3:
                                clock_pos = ((coast_sides[1] * 2) + 3) % 12
                            else:
                                clock_pos = ((coast_sides[2] * 2) + 3) % 12
                elif sum(has_coast) == 4:
                    # FOUR COASTAL HEXSIDES
                    land_sides = [i for i, v in enumerate(has_coast) if v is False]
                    if land_sides[1] - land_sides[0] == 3:
                        # opposite hexsides
                        clock_pos = 0
                    else:
                        if land_sides[1] - land_sides[0] < 3:
                            clock_pos = sum(land_sides) - 3
                        else:
                            clock_pos = sum(land_sides) + 3
                else:
                    # should not happen
                    print("issue routing rail for hex {}".format(cell))

            ## handle landlocked hexes
            else:
                rail_sides = [False] * 6
                for k, s in cell["hexsides"]:
                    if k in ["Ra", "Ro"]:
                        rail_sides = [rail_sides[side] or s & 2 ** side > 0 for side in range(6)]
                # rail_sides = sp.argwhere(sp.asarray(rail_sides) == True).flatten().tolist()
                rail_sides = [i for i, v in enumerate(rail_sides) if v is True]
                if len(rail_sides) == 0:
                    clock_pos = 0
                elif len(rail_sides) == 1:
                    clock_pos = 12 + (rail_sides[0] * 2 + 9) % 12
                elif len(rail_sides) == 2:
                    if rail_sides[1] - rail_sides[0] == 3:
                        # opposite means centered gravity
                        clock_pos = 0
                    elif rail_sides[0] > 1 or (rail_sides[0] == 1 and rail_sides[1] == 3):
                        clock_pos = sum(rail_sides) + 9
                    elif rail_sides[1] < 3:
                        clock_pos = sum(rail_sides) + 21
                    else:
                        clock_pos = sum(rail_sides) + 15
                elif len(rail_sides) == 3:
                    if rail_sides[0] % 2 == rail_sides[1] % 2 == rail_sides[2] % 2:
                        # all even or all odd means centered gravity
                        clock_pos = 0
                    else:
                        if sum(rail_sides) % 3 == 0:
                            # all adjacent
                            clock_pos = {
                                0: 9,
                                1: 11,
                                2: 1,
                                3: 3,
                                4: 5,
                                5: 7,
                            }[rail_sides[1]]
                        else:
                            clock_pos = 0
                elif len(rail_sides) == 4:
                    if rail_sides[0] + 2 == rail_sides[-1] or rail_sides[0] + 4 == rail_sides[-1]:
                        # one isolated hexside
                        if rail_sides[0] - rail_sides[-1] < 3:
                            clock_pos = rail_sides[0] + rail_sides[-1] + 15
                        else:
                            clock_pos = rail_sides[0] + rail_sides[-1] + 9
                    else:
                        clock_pos = 0
                else:
                    # doesnt happen
                    clock_pos = 0

        # return
        dx, dy = get_hex_clock_pos(clock_pos, center=(68, 76), radius=68)
        x += dx + off[0]
        y += dy + off[1]
        return x, y

    def _render(self, *args, **kwargs):
        for cell in self.map.values():
            # region check
            if cell.q < (self.parent.region[0] or 0) or cell.q > (self.parent.region[2] or 99999):
                continue
            if cell.r < (self.parent.region[1] or 0) or cell.r > (self.parent.region[3] or 99999):
                continue

            if "hexsides" in cell:
                for kind, side in cell["hexsides"]:
                    if kind in ("Ra", "Ro"):
                        sections = []
                        orig_x, orig_y = self.find_rail_rout_for_cell(cell)
                        for i, targ in enumerate(self.map.neighbors((cell.q, cell.r))):
                            if side & 2 ** i > 0:
                                if any([k == "Co" and s & 2 ** i > 0 for k, s in cell["hexsides"]]):
                                    continue
                                targ_x, targ_y = self.find_rail_rout_for_cell(self.map[targ])
                                sections.append((orig_x, orig_y, targ_x, targ_y))
                        for s in sections:
                            base_section = self.svg.line(
                                start=(s[0], s[1]),
                                end=(s[2], s[3]),
                                stroke=self.rail_style[0][0],
                                stroke_width=self.rail_style[0][1])
                            self.layer.add(base_section)
                            dash_section = self.svg.line(
                                start=(s[0], s[1]),
                                end=(s[2], s[3]),
                                stroke=self.rail_style[1][0],
                                stroke_width=self.rail_style[1][1])
                            if kind == "Ra":
                                dash_section.dasharray((self.rail_style[0][1],))
                            self.layer.add(dash_section)


class HexsideLayer(BaseLayer):
    """layer for hex side features like strait arrows, alpine hexsides, etc."""

    def __init__(self, parent, *args, **kwargs):
        super(HexsideLayer, self).__init__(parent, *args, **kwargs)

        # strait arrows
        feat = self.svg.marker(
            id="arrowhead",
            insert=(2, 2),
            size=(5, 5),
            orient="auto")
        feat.add(self.svg.polygon(points=[(0, 0), (5, 2), (0, 4)], fill="red"))
        self.svg.defs.add(feat)

    def _render(self, *args, **kwargs):
        for cell in self.map.values():
            # region check
            if cell.q < (self.parent.region[0] or 0) or cell.q > (self.parent.region[2] or 99999):
                continue
            if cell.r < (self.parent.region[1] or 0) or cell.r > (self.parent.region[3] or 99999):
                continue

            if "hexsides" in cell:
                points = self.hex_points(cell.q, cell.r)
                for kind, side in cell["hexsides"]:
                    if kind in ["Al", "Ri", "Ca"]:
                        line_points = []
                        if side & 1:
                            line_points.append((points[4], points[5]))
                        if side & 2:
                            line_points.append((points[5], points[0]))
                        if side & 4:
                            line_points.append((points[0], points[1]))
                        if side & 8:
                            line_points.append((points[1], points[2]))
                        if side & 16:
                            line_points.append((points[2], points[3]))
                        if side & 32:
                            line_points.append((points[3], points[4]))
                        try:
                            line_kwargs = {
                                "Al": {"stroke": "white", "stroke_width": 20},
                                # "Ri": {"stroke": "blue", "stroke_width": 5},
                                # "Ca": {"stroke": "blue", "stroke_width": 3},
                            }[kind]
                            for edge in line_points:
                                line = self.svg.line(start=edge[0], end=edge[1], **line_kwargs)
                                self.layer.add(line)
                        except:
                            continue
                    elif kind == "St":
                        # straits
                        lerp = lambda A, B, C: (C * B) + ((1 - C) * A)
                        line_kwargs = {"stroke": "red", "stroke_width": 4, "marker_end": "url(#arrowhead)"}
                        dxx, dx, dy = 28, 14, 24
                        if side & 1:  # W
                            line_start = (
                                lerp(points[4][0], points[5][0], 1.0 / 3.0),
                                lerp(points[4][1], points[5][1], 1.0 / 3.0))
                            line_end = (line_start[0] + dxx, line_start[1])
                            line = self.svg.line(start=line_start, end=line_end, **line_kwargs)
                            self.layer.add(line)
                        if side & 2:  # NW
                            line_start = (
                                lerp(points[5][0], points[0][0], 1.0 / 3.0),
                                lerp(points[5][1], points[0][1], 1.0 / 3.0))
                            line_end = (line_start[0] + dx, line_start[1] + dy)
                            line = self.svg.line(start=line_start, end=line_end, **line_kwargs)
                            self.layer.add(line)
                        if side & 4:  # NE
                            line_start = (
                                lerp(points[1][0], points[0][0], 1.0 / 3.0),
                                lerp(points[1][1], points[0][1], 1.0 / 3.0))
                            line_end = (line_start[0] - dx, line_start[1] + dy)
                            line = self.svg.line(start=line_start, end=line_end, **line_kwargs)
                            self.layer.add(line)
                        if side & 8:  # E
                            line_start = (
                                lerp(points[2][0], points[1][0], 1.0 / 3.0),
                                lerp(points[2][1], points[1][1], 1.0 / 3.0))
                            line_end = (line_start[0] - dxx, line_start[1])
                            line = self.svg.line(start=line_start, end=line_end, **line_kwargs)
                            self.layer.add(line)
                        if side & 16:  # SE
                            line_start = (
                                lerp(points[3][0], points[2][0], 1.0 / 3.0),
                                lerp(points[3][1], points[2][1], 1.0 / 3.0))
                            line_end = (line_start[0] - dx, line_start[1] - dy)
                            line = self.svg.line(start=line_start, end=line_end, **line_kwargs)
                            self.layer.add(line)
                        if side & 32:  # SW
                            line_start = (
                                lerp(points[3][0], points[4][0], 1.0 / 3.0),
                                lerp(points[3][1], points[4][1], 1.0 / 3.0))
                            line_end = (line_start[0] + dx, line_start[1] - dy)
                            line = self.svg.line(start=line_start, end=line_end, **line_kwargs)
                            self.layer.add(line)


class FeatureLayer(BaseLayer):
    """layer for hex features like cities, ports, resource, factories, etc."""

    def __init__(self, parent, *args, **kwargs):
        super(FeatureLayer, self).__init__(parent, *args, **kwargs)

        # city dot 22x22
        feat = self.svg.g(id="city")
        feat.add(self.svg.circle(center=(0, 0), r=10, fill="yellow", stroke="black", stroke_width=4))
        self.svg.defs.add(feat)

        # minor capital dot 34x34
        feat = self.svg.g(id="capital-minor")
        feat.add(self.svg.circle(center=(0, 0), r=15, fill="yellow", stroke="black", stroke_width=4))
        feat.add(self.svg.circle(center=(0, 0), r=5, fill="gray"))
        self.svg.defs.add(feat)

        # major capital dot 34x34
        feat = self.svg.g(id="capital-major")
        feat.add(self.svg.circle(center=(0, 0), r=15, fill="yellow", stroke="black", stroke_width=4))
        feat.add(self.svg.circle(center=(0, 0), r=5, fill="red"))
        self.svg.defs.add(feat)

        # minor port dot 30x30
        feat = self.svg.g(id="minor-port")
        feat.add(self.svg.circle(center=(0, 0), r=15, fill="royalblue", stroke="gray"))
        feat.add(self.svg.circle(center=(0, 0), r=12, fill="white"))
        feat.add(self.svg.rect(insert=(-1, -7), size=(2, 16), fill="royalblue"))
        feat.add(self.svg.rect(insert=(-4, -3), size=(8, 2), fill="royalblue"))
        feat.add(self.svg.ellipse(center=(0, -7), r=(3, 2), fill="white", stroke="royalblue", stroke_width=2))
        feat.add(self.svg.path(
            fill="royalblue",
            stroke="royalblue",
            d="M 0,10 c 5.37695,0 8.92477,-6.81264 8.92477,-6.81264 1.69798,-0.82138 1.69798,-0.45555"
              " 1.69798,-0.82138 0,-1.18721 0.13114,-2.9128 0.13114,-3.27863 0,-0.36582 -2.6436,1.82223"
              " -3.83081,1.91196 0,0 1.09057,1.00084 0.91111,1.7325 -0.17946,0.72474 -1.81532,3.47879"
              " -3.36835,4.18973 -2.19496,1.00085 -4.46584,0.91112 -4.46584,0.91112 l 0,2.16734 m 0,0"
              " c -5.37695,0 -8.92477,-6.81264 -8.92477,-6.81264 -1.69798,-0.82138 -1.69798,-0.45555"
              " -1.69798,-0.82138 0,-1.18721 -0.13114,-2.9128 -0.13114,-3.27863 0,-0.36582 2.6436,1.82223"
              " 3.83081,1.91196 0,0 -1.09057,1.00084 -0.91111,1.7325 0.17946,0.72474 1.81532,3.47879"
              " 3.36835,4.18973 2.19496,1.00085 4.46584,0.91112 4.46584,0.91112 l 0,2.16734"))
        self.svg.defs.add(feat)

        # major port dot 30x30
        feat = self.svg.g(id="major-port")
        feat.add(self.svg.circle(center=(0, 0), r=15, fill="goldenrod", stroke="gray"))
        feat.add(self.svg.circle(center=(0, 0), r=12, fill="navy"))
        feat.add(self.svg.rect(insert=(-1, -7), size=(2, 16), fill="white"))
        feat.add(self.svg.rect(insert=(-4, -3), size=(8, 2), fill="white"))
        feat.add(self.svg.ellipse(center=(0, -7), r=(3, 2), fill="navy", stroke="white", stroke_width=2))
        feat.add(self.svg.path(
            fill="white",
            stroke="white",
            d="M 0,10 c 5.37695,0 8.92477,-6.81264 8.92477,-6.81264 1.69798,-0.82138 1.69798,-0.45555"
              " 1.69798,-0.82138 0,-1.18721 0.13114,-2.9128 0.13114,-3.27863 0,-0.36582 -2.6436,1.82223"
              " -3.83081,1.91196 0,0 1.09057,1.00084 0.91111,1.7325 -0.17946,0.72474 -1.81532,3.47879"
              " -3.36835,4.18973 -2.19496,1.00085 -4.46584,0.91112 -4.46584,0.91112 l 0,2.16734 m 0,0"
              " c -5.37695,0 -8.92477,-6.81264 -8.92477,-6.81264 -1.69798,-0.82138 -1.69798,-0.45555"
              " -1.69798,-0.82138 0,-1.18721 -0.13114,-2.9128 -0.13114,-3.27863 0,-0.36582 2.6436,1.82223"
              " 3.83081,1.91196 0,0 -1.09057,1.00084 -0.91111,1.7325 0.17946,0.72474 1.81532,3.47879"
              " 3.36835,4.18973 2.19496,1.00085 4.46584,0.91112 4.46584,0.91112 l 0,2.16734"))
        self.svg.defs.add(feat)

        # iced in port background 30x30
        feat = self.svg.g(id="port-ice")
        r1 = self.svg.rect(insert=(-14, -14), size=(28, 28), fill="white", stroke="gray")
        r1.rotate(45, (0, 0))
        feat.add(r1)
        r2 = self.svg.rect(insert=(-13, -13), size=(26, 26), fill="white", stroke="gray")
        r2.rotate(15, (0, 0))
        feat.add(r2)
        r3 = self.svg.rect(insert=(-13, -13), size=(26, 26), fill="white", stroke="gray")
        r3.rotate(-15, (0, 0))
        feat.add(r3)
        self.svg.defs.add(feat)

        # factory icons
        img_data = Image.open(os.path.join(
            SETTINGS["filesystem"]["basepath"],
            "Bitmaps", "Icon Bitmaps",
            "FACTORYSTACKRED.bmp"))
        img_data, img_dims = pil_img_to_b64_png(img_data)
        img_node = self.svg.image(
            "data:image/png;base64,{}".format(img_data),
            size=img_dims,
            id="png-fac-red")
        self.svg.defs.add(img_node)
        img_data = Image.open(os.path.join(
            SETTINGS["filesystem"]["basepath"],
            "Bitmaps", "Icon Bitmaps",
            "FACTORYSTACKBLUE.bmp"))
        img_data, img_dims = pil_img_to_b64_png(img_data)
        img_node = self.svg.image(
            "data:image/png;base64,{}".format(img_data),
            size=img_dims,
            id="png-fac-blu")
        self.svg.defs.add(img_node)
        img_data = Image.open(os.path.join(
            SETTINGS["filesystem"]["basepath"],
            "Bitmaps", "Icon Bitmaps",
            "FACTORYSMOKE.bmp"))
        img_data, img_dims = pil_img_to_b64_png(img_data)
        img_node = self.svg.image(
            "data:image/png;base64,{}".format(img_data),
            size=img_dims,
            id="png-fac-smk")
        self.svg.defs.add(img_node)

        # factory: r
        feat = self.svg.g(id="factory-r")
        frame = self.svg.rect(insert=(-7, -16), size=(14, 32), fill="red")
        feat.add(frame)
        stack1 = self.svg.use("#png-fac-red", insert=(-5, -4))
        feat.add(stack1)
        smoke1 = self.svg.use("#png-fac-smk", insert=(-5, -14))
        feat.add(smoke1)
        self.svg.defs.add(feat)
        # factory: b
        feat = self.svg.g(id="factory-b")
        frame = self.svg.rect(insert=(-7, -16), size=(14, 32), fill="blue")
        feat.add(frame)
        stack1 = self.svg.use("#png-fac-red", insert=(-5, -4))
        feat.add(stack1)
        smoke1 = self.svg.use("#png-fac-smk", insert=(-5, -14))
        feat.add(smoke1)
        self.svg.defs.add(feat)
        # factory: rb
        feat = self.svg.g(id="factory-rb")
        frame = self.svg.rect(insert=(-12, -16), size=(24, 32), fill="red")
        feat.add(frame)
        stack1 = self.svg.use("#png-fac-red", insert=(-10, -4))
        feat.add(stack1)
        smoke1 = self.svg.use("#png-fac-smk", insert=(-10, -14))
        feat.add(smoke1)
        stack2 = self.svg.use("#png-fac-blu", insert=(0, -4))
        feat.add(stack2)
        smoke2 = self.svg.use("#png-fac-smk", insert=(0, -14))
        feat.add(smoke2)
        self.svg.defs.add(feat)
        # factory: rbb
        feat = self.svg.g(id="factory-rbb")
        frame = self.svg.rect(insert=(-17, -16), size=(34, 32), fill="red")
        feat.add(frame)
        stack1 = self.svg.use("#png-fac-red", insert=(-15, -4))
        feat.add(stack1)
        smoke1 = self.svg.use("#png-fac-smk", insert=(-15, -14))
        feat.add(smoke1)
        stack2 = self.svg.use("#png-fac-blu", insert=(-5, -4))
        feat.add(stack2)
        smoke2 = self.svg.use("#png-fac-smk", insert=(-5, -14))
        feat.add(smoke2)
        stack3 = self.svg.use("#png-fac-blu", insert=(5, -4))
        feat.add(stack3)
        smoke3 = self.svg.use("#png-fac-smk", insert=(5, -14))
        feat.add(smoke3)
        self.svg.defs.add(feat)

        # resource icons
        img_data = Image.open(os.path.join(
            SETTINGS["filesystem"]["basepath"],
            "Bitmaps", "Icon Bitmaps",
            "RESOURCE1.bmp"))
        img_data, img_dims = pil_img_to_b64_png(img_data)
        img_node = self.svg.image(
            "data:image/png;base64,{}".format(img_data),
            insert=(-17, -17),
            size=img_dims,
            id="png-res")
        self.svg.defs.add(img_node)
        img_data = Image.open(os.path.join(
            SETTINGS["filesystem"]["basepath"],
            "Bitmaps", "Icon Bitmaps",
            "OIL1.bmp"))
        img_data, img_dims = pil_img_to_b64_png(img_data)
        img_node = self.svg.image(
            "data:image/png;base64,{}".format(img_data),
            insert=(-17, -17),
            size=img_dims,
            id="png-oil")
        self.svg.defs.add(img_node)

    def _render(self, *args, **kwargs):
        for cell in self.map.values():
            if cell.q < (self.parent.region[0] or 0) or cell.q > (self.parent.region[2] or 99999):
                continue
            if cell.r < (self.parent.region[1] or 0) or cell.r > (self.parent.region[3] or 99999):
                continue
            if "sz_id" in cell:
                continue

            # cell origin
            cell_x, cell_y = self.hex_origin(cell.q, cell.r)

            # city features
            try:
                kind, clock_pos = cell["cty"]
                if kind > 0:
                    dx, dy = get_hex_clock_pos(clock_pos, center=(68, 76), radius=68)
                    if kind == 1:
                        feature = self.svg.use("#city", insert=(cell_x + dx, cell_y + dy))
                    elif kind == 2:
                        feature = self.svg.use("#capital-minor", insert=(cell_x + dx, cell_y + dy))
                    elif kind == 3:
                        feature = self.svg.use("#capital-major", insert=(cell_x + dx, cell_y + dy))
                    else:
                        raise ValueError("unknown city code: {}".format(kind))
                    self.layer.add(feature)
            except Exception as ex:
                print("feature.city issue: [{}] {}".format(cell.key(), ex))

            # port features
            try:
                kind, clock_pos = cell["prt"]
                if kind > 0:
                    dx, dy = get_hex_clock_pos(clock_pos, center=(68, 76), radius=68)
                    if cell["ice"] is True:
                        self.layer.add(self.svg.use("#port-ice", insert=(cell_x + dx, cell_y + dy)))
                    if kind == 1:
                        feature = self.svg.use("#minor-port", insert=(cell_x + dx, cell_y + dy))
                    elif kind == 2:
                        feature = self.svg.use("#major-port", insert=(cell_x + dx, cell_y + dy))
                    else:
                        raise ValueError("unknown port code: {}".format(kind))
                    self.layer.add(feature)
            except Exception as ex:
                print("feature.city issue: [{}] {}".format(cell.key(), ex))

            # factory features
            try:
                kind, clock_pos = cell["fac"]
                if kind > 0:
                    dx, dy = get_hex_clock_pos(clock_pos, center=(68, 76), radius=68)
                    if kind == 1:
                        feature = self.svg.use("#factory-r", insert=(cell_x + dx, cell_y + dy))
                    elif kind == 2:
                        feature = self.svg.use("#factory-b", insert=(cell_x + dx, cell_y + dy))
                    elif kind == 4:
                        feature = self.svg.use("#factory-rb", insert=(cell_x + dx, cell_y + dy))
                    elif kind == 9:
                        feature = self.svg.use("#factory-rbb", insert=(cell_x + dx, cell_y + dy))
                    elif kind == 15:
                        feature = self.svg.use("#factory-rbb", insert=(cell_x + dx, cell_y + dy))
                    else:
                        raise ValueError("unknown factory code: {}".format(kind))
                    self.layer.add(feature)
            except Exception as ex:
                print("feature.factory issue: [{}] {}".format(cell.key(), ex))

            # resource features
            try:
                kind, clock_pos = cell["res"]
                if kind != 0:
                    dx, dy = get_hex_clock_pos(clock_pos, center=(68, 76), radius=68)
                    if kind > 0:
                        feature = self.svg.use("#png-res", insert=(cell_x + dx, cell_y + dy))
                    if kind < 0:
                        feature = self.svg.use("#png-oil", insert=(cell_x + dx, cell_y + dy))
                    self.layer.add(feature)
                    if (abs(kind)) > 1:
                        # handle multiplicity
                        feature = self.svg.rect(insert=(cell_x + dx + 2, cell_y + dy + 2), size=(12, 12), fill="white")
                        self.layer.add(feature)
                        feature = self.svg.text(
                            abs(kind) * "I",
                            insert=(cell_x + dx + 8, cell_y + dy + 12),
                            stroke="black",
                            stroke_width=2,
                            font_size="11px",
                            text_anchor="middle")
                        self.layer.add(feature)

            except Exception as ex:
                print("feature.factory issue: [{}] {}".format(cell.key(), ex))


class GridLayer(BaseLayer):
    def __init__(self, parent, *args, **kwargs):
        super(GridLayer, self).__init__(parent, *args, **kwargs)
        self.colour = SETTINGS["colour"]["grid"]
        self.coords = bool(kwargs.get("coords", False))

    def _render(self, *args, **kwargs):
        self.layer.style = "font-family:Verdana, Helvetica, Arial, sans-serif;font-size:10;font-weight:bold;"
        for cell in self.map.values():
            # region check
            if cell.q < (self.parent.region[0] or 0) or cell.q > (self.parent.region[2] or 99999):
                continue
            if cell.r < (self.parent.region[1] or 0) or cell.r > (self.parent.region[3] or 99999):
                continue

            points = self.hex_points(cell.q, cell.r)
            grid = self.svg.polygon(points=points, fill="none", stroke=self.colour)
            if self.coords is True:
                x, y = self.hex_origin(cell.q, cell.r)
                coord = self.svg.text(
                    "{:03d}-{:03d}".format(cell.q, cell.r),
                    insert=(x + 125, y + 76),
                    writing_mode="tb",
                    text_anchor="middle",
                    fill=self.colour)
                self.layer.add(coord)
            self.layer.add(grid)


class LabelLayer(BaseLayer):
    """layer for hex features like cities, ports, resource, factories, etc."""

    COL_CODE = {
        1: "#000000",  # black
        2: "#8B0000",  # dark red
        3: "#008000",  # green
        4: "#A52A2A",  # brown
        5: "#000080",  # navy blue
        6: "#EE82EE",  # violet
        7: "#3CB371",  # blue-green
        8: "#C0C0C0",  # silver
        9: "#808080",  # gray
        10: "#FF0000",  # red
        11: "#ADFF2F",  # bright green (green-yellow)
        12: "#FFFF00",  # yellow
        13: "#0000FF",  # blue
        14: "#FF00FF",  # fuchsia
        15: "#00FFFF",  # aqua blue
        16: "#FFFFFF",  # white
    }

    def __init__(self, parent, *args, **kwargs):
        super(LabelLayer, self).__init__(parent, *args, **kwargs)
        self.svg.defs.add(self.svg.style(
            "@import url('https://fonts.googleapis.com/css?family=Droid+Sans:700');"))

    def _render(self, *args, **kwargs):
        self.layer.update({
            "style": "font-family:'Droid Sans',sans-serif;"})
        for cell in self.map.values():
            # region check
            if cell.q < (self.parent.region[0] or 0) or cell.q > (self.parent.region[2] or 99999):
                continue
            if cell.r < (self.parent.region[1] or 0) or cell.r > (self.parent.region[3] or 99999):
                continue

            # cell origin
            x, y = self.hex_origin(cell.q, cell.r)

            # render label
            if "labels" in cell:
                for text, (dx, dy), size, colour in cell["labels"]:
                    size *= 3
                    label = self.svg.text(
                        text,
                        insert=(x + 2 * dx + 2, y + 2 * dy + 2 + size),
                        fill=self.COL_CODE[colour + 1],
                        # stroke=self.COL_CODE[colour + 1],
                        font_size=size)
                    self.layer.add(label)


class BorderLayer(BaseLayer):
    def __init__(self, parent, *args, **kwargs):
        super(BorderLayer, self).__init__(parent, *args, **kwargs)
        self.render_attr = kwargs.get("render_attr", {
            "nat": ("#800000", 6),
            "wea": ("#FFFFFF", 3),
            "sea": ("#000080", 6),
        })

    def _render(self, *args, **kwargs):
        for cell in self.map.values():
            # region check
            if cell.q < (self.parent.region[0] or 0) or cell.q > (self.parent.region[2] or 99999):
                continue
            if cell.r < (self.parent.region[1] or 0) or cell.r > (self.parent.region[3] or 99999):
                continue
            if "borders" not in cell:
                continue

            points = self.hex_points(cell.q, cell.r)
            line_points = []
            n_lines = len(cell["borders"])
            if n_lines == 1:
                kind, sides = cell["borders"][0]
                if sides & 1:
                    line_points.append((points[4], points[5]))
                if sides & 2:
                    line_points.append((points[5], points[0]))
                if sides & 4:
                    line_points.append((points[0], points[1]))
                if sides & 8:
                    line_points.append((points[1], points[2]))
                if sides & 16:
                    line_points.append((points[2], points[3]))
                if sides & 32:
                    line_points.append((points[3], points[4]))
                ra = self.render_attr[kind]
                line_kwargs = {"stroke": ra[0], "stroke_width": ra[1]}
                for edge in line_points:
                    line = self.svg.line(start=edge[0], end=edge[1], **line_kwargs)
                    self.layer.add(line)
            else:
                line_points = {
                    1: (points[4], points[5]),
                    2: (points[5], points[0]),
                    4: (points[0], points[1]),
                    8: (points[1], points[2]),
                    16: (points[2], points[3]),
                    32: (points[3], points[4]),
                }
                line_kind = [c[0] for c in cell["borders"]]
                for key_side in line_points.keys():
                    line_mem = []
                    for n in range(n_lines):
                        kind, sides = cell["borders"][n]
                        line_mem.append(sides & key_side > 0)
                    kth_line = 0
                    for n in range(n_lines):
                        if line_mem[n]:
                            kth_line += 1
                            line = self.svg.line(
                                start=line_points[key_side][0],
                                end=line_points[key_side][1],
                                stroke=self.render_attr[line_kind[n]][0],
                                stroke_width=self.render_attr[line_kind[n]][1])
                            if kth_line > 1:
                                line.dasharray([15, 15 * sum(line_mem)])
                            self.layer.add(line)


class InfoLayer(BaseLayer):
    def __init__(self, parent, *args, **kwargs):
        super(InfoLayer, self).__init__(parent, *args, **kwargs)
        self.field_names = kwargs.get("field_names", ["country_id"])
        if not isinstance(self.field_names, (list, tuple)):
            self.field_names = [self.field_names]
        self.render_attr = kwargs.get("render_attr", ("#FF0000",))

    def _render(self, *args, **kwargs):
        self.layer.style = "font-family:Verdana, Helvetica, Arial, sans-serif;font-size:30;font-weight:bold;"
        for cell in self.map.values():
            # region check
            if cell.q < (self.parent.region[0] or 0) or cell.q > (self.parent.region[2] or 99999):
                continue
            if cell.r < (self.parent.region[1] or 0) or cell.r > (self.parent.region[3] or 99999):
                continue
            if not any([n in cell for n in self.field_names]):
                continue

            x, y = self.hex_origin(cell.q, cell.r)
            text = "|".join(["{}".format(cell[n]) for n in self.field_names])
            coord = self.svg.text(
                text,
                insert=(x + 76, y + 76),
                text_anchor="middle",
                fill=self.render_attr[0])
            self.layer.add(coord)


## MAIN

def gen_svg(map_reader, file_name, region=None, scale=None):
    ms = MapDrawing(map_reader, file_name, region=region, scale=scale)
    ms.add_layer(TerrainLayer, simple=False)
    ms.add_layer(CoastalLayer, simple=False)
    ms.add_layer(RVRLayer)
    ms.add_layer(HexsideLayer)
    ms.add_layer(GridLayer, coords=True)
    ms.add_layer(RailLayer)
    ms.add_layer(BorderLayer)
    ms.add_layer(FeatureLayer)
    ms.add_layer(LabelLayer)
    # ms.add_layer(InfoLayer, field_names=["sz_adj"])
    ms.render()
    return ms


def gen_svgs():
    VERBOSE = True
    m = MWIFMapReader()
    m.load_ter_data(verbose=VERBOSE)
    m.load_coa_data(verbose=VERBOSE)
    m.load_hst_data(verbose=VERBOSE)
    m.load_sea_adj_data(verbose=VERBOSE)
    m.gen_border_data(verbose=VERBOSE)

    # regionALL = None
    # regionBlackSea = (48, 48, 68, 68)
    # regionE = (0, 0, 190, 98)
    # regionNW = (190, 0, 359, 98)
    # regionSE = (0, 68, 190, 194)
    # regionSW = (190, 68, 359, 194)
    # regionEurope = (15, 30, 70, 80)

    # 6x3 parts @ 10 hex overlap
    # + -- + -- + -- + -- + -- + -- +
    # | 01 | 02 | 03 | 04 | 05 | 06 |
    # + -- + -- + -- + -- + -- + -- +
    # | 07 | 08 | 09 | 10 | 11 | 12 |
    # + -- + -- + -- + -- + -- + -- +
    # | 13 | 14 | 15 | 16 | 17 | 18 |
    # + -- + -- + -- + -- + -- + -- +
    # | 19 | 20 | 21 | 22 | 23 | 24 |
    # + -- + -- + -- + -- + -- + -- +

    MAX_COL = 359
    MAX_ROW = 195
    for row in range(4):
        for col in range(6):
            part_idx = row * 6 + col + 1
            part_reg = (
                max(col * 62 - 3, 0),
                max(row * 50 - 3, 0),
                min((col + 1) * 62 + 3, MAX_COL),
                min((row + 1) * 50 + 3, MAX_ROW)
            )
            part_nam = "part{:02d}".format(part_idx)
            print()
            print("RENDERING: part:", part_idx, part_nam, part_reg)
            print()
            part_drw = gen_svg(m, part_nam, region=part_reg, scale=None)

    #part_drw = gen_svg(m, "layer", region=(0, 0, 65, 53), scale=None)


## MAIN

if __name__ == "__main__":
    gen_svgs()

## EOF
