"""render map using cairo"""

## IMPORTS

import os
from cairo import Context, ImageSurface, SVGSurface
from ConfigParser import ConfigParser

import math

from mwif_map_reader import MWIFMapReader

## CONSTANTS

SQRT3 = math.sqrt(3.0)
SQRT3BY2 = SQRT3 / 2.0

## HELPERS

def html2float(html_colour_str):
    """converts HTML colour code to rgb tuple of values in (0.0,1.0]"""
    assert isinstance(html_colour_str, str)
    assert html_colour_str.startswith("#")
    assert len(html_colour_str) == 7

    r = int(html_colour_str[1:3], 16) / 255.0
    g = int(html_colour_str[3:5], 16) / 255.0
    b = int(html_colour_str[5:7], 16) / 255.0

    return r, g, b


## CLASSES

class MapSurface(object):
    """wrapper to render the map to svg/png"""

    def __init__(self, hexmap=None, filename=None, width=None, height=None, size=None):
        self.hexmap = hexmap
        if self.hexmap is None:
            raise ValueError("No map was passed to {}".format(self.__class__.__name__))
        self.surface_name = filename or "test.svg"
        self.size = size or 32.0
        self.surface_width = width
        if self.surface_width is None:
            self.surface_width = (self.hexmap.map.cols + .5) * self.size * SQRT3
        self.surface_height = height
        if self.surface_height is None:
            self.surface_height = (self.hexmap.map.rows * 1.5 + .25) * self.size
        self.layer = []

        # build base map
        self.surface = SVGSurface(self.surface_name + ".svg", self.surface_width, self.surface_height)
        self.context = Context(self.surface)
        # background: magenta
        self.context.save()
        self.context.set_source_rgb(1.0, 0.0, 1.0)
        self.context.paint()
        self.context.restore()

    def add_layer(self, renderer_cls, position=None):
        if not position:
            self.layer.append(renderer_cls(self))
        else:
            self.layer.insert(position, renderer_cls(self))

    def render(self):
        print "Rendering {} ({}x{})".format(self.surface_name, self.surface_width, self.surface_height)
        for renderer in self.layer:
            renderer.render()

    def finalise(self, with_png=False):
        print "finalising:"
        if with_png is True:
            print "PNG"
            self.surface.write_to_png(self.surface_name + ".png")
        print "SVG"
        self.surface.finish()
        print "DONE!"


class BaseRenderer(object):
    def __init__(self, surface, *args, **kwargs):
        self.surface = surface

    def render(self, context=None):
        ctx = context or self.surface.context
        ctx.save()
        self._render(ctx)
        ctx.restore()
        print "{} finished!".format(self.__class__.__name__)

    def _render(self, ctx):
        raise NotImplementedError


class TerrainRenderer(BaseRenderer):
    cp = ConfigParser()
    cp.read(["settings.cfg", "./settings.cfg", "./mwifmap/settings.cfg"])
    TER_CODE = {
        0: html2float(cp.get("colour", "ter00")), # "all sea",
        1: html2float(cp.get("colour", "ter01")), # "lake",
        2: html2float(cp.get("colour", "ter02")), # "clear",
        3: html2float(cp.get("colour", "ter03")), # "forest",
        4: html2float(cp.get("colour", "ter04")), # "jungle",
        5: html2float(cp.get("colour", "ter05")), # "mountain",
        6: html2float(cp.get("colour", "ter06")), # "swamp",
        7: html2float(cp.get("colour", "ter07")), # "desert",
        8: html2float(cp.get("colour", "ter08")), # "desert mountain",
        9: html2float(cp.get("colour", "ter09")), # "tundra",
        10: html2float(cp.get("colour", "ter10")), # "ice",
        11: html2float(cp.get("colour", "ter11")), # "quattara depression"
    }
    GRID_COLOUR = html2float(cp.get("colour", "grid"))
    del cp

    def __init__(self, surface, *args, **kwargs):
        super(TerrainRenderer, self).__init__(surface, *args, **kwargs)
        self.hexmap = self.surface.hexmap.map
        self.size = self.surface.size
        self.cell_proto = [
            (self.size * SQRT3BY2, 0),
            (self.size * SQRT3, self.size * 0.5),
            (self.size * SQRT3, self.size * 1.5),
            (self.size * SQRT3BY2, self.size * 2.0),
            (0, self.size * 1.5),
            (0, self.size * 0.5),
        ]

    def _render(self, ctx):
        for cell in self.hexmap.itervalues():
            # calc points - alternate the offset of the cells based on row
            offset = self.surface.size * SQRT3BY2 if cell.r % 2 else 0
            top = 1.5 * cell.r * self.size
            left = offset + cell.q * self.size * SQRT3
            points = [(x + left, y + top) for x, y in self.cell_proto]

            # draw the polygon onto the surface
            ctx.set_line_width(1.0)
            # ctx.set_source_rgb(*self.GRID_COLOUR)
            ctx.move_to(*points[0])
            ctx.line_to(*points[1])
            ctx.line_to(*points[2])
            ctx.line_to(*points[3])
            ctx.line_to(*points[4])
            ctx.line_to(*points[5])
            ctx.close_path()
            # ctx.stroke_preserve()
            ctx.set_source_rgb(*self.TER_CODE[cell["ter_code"]])
            ctx.fill()
            ctx.save()


class CostalRenderer(BaseRenderer):
    cp = ConfigParser()
    cp.read(["settings.cfg", "./settings.cfg", "./mwifmap/settings.cfg"])
    BASE_PATH = cp.get("filesystem", "basepath")
    del cp

    def __init__(self, surface, *args, **kwargs):
        super(CostalRenderer, self).__init__(surface, *args, **kwargs)
        self.hexmap = self.surface.hexmap.map
        self.size = self.surface.size
        self.cell_proto = [
            (self.size * SQRT3BY2, 0),
            (self.size * SQRT3, self.size * 0.5),
            (self.size * SQRT3, self.size * 1.5),
            (self.size * SQRT3BY2, self.size * 2.0),
            (0, self.size * 1.5),
            (0, self.size * 0.5),
        ]

    def _render(self, ctx):
        base_path = os.path.join(self.BASE_PATH, "Bitmaps", "Coastal Bitmaps")
        try:
            page_bm_file = os.path.join(base_path, "Page01.bmp")
            page_bm_file = ImageSurface.crea
            with open(page_bm_file, "r") as fp:

            page_dt_file = os.path.join(base_path, "Page01.txt")
        except:
            print "Error reading coastal files!"

    # XXX: paste - unfinished!
    def placePng(pCtxt, pFilename, pX, pY, pFac):
        mpng = cairo.ImageSurface.create_from_png(pFilename)
        mw = mpng.get_width() * pFac
        mh = mpng.get_height() * pFac
        mPatt = cairo.SurfacePattern(mpng)
        mMatrix = cairo.Matrix(xx=1 / pFac, yy=1 / pFac,
                               x0=-pX / pFac, y0=-pY / pFac)
        mPatt.set_matrix(mMatrix)
        pCtxt.set_source(mPatt)
        pCtxt.rectangle(pX, pY, mw, mh)
        pCtxt.fill()

## TEST

def test1():
    for html_colour in ["#123456", "#000000", "#FFFFFF"]:
        print html_colour, ":", html2float(html_colour)


def test2():
    m = MWIFMapReader()
    m.load_ter()

    m = MWIFMapReader()
    m.load_ter()

    ms = MapSurface(m, "example2", size=76)
    ms.add_layer(TerrainRenderer)
    ms.render()
    #ms.finalise(True)
    ms.finalise(False)

## MAIN

if __name__ == '__main__':
    test2()

## EOF
