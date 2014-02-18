"""render map using cairo"""

## IMPORTS

from cairo import SVGSurface, Context
from ConfigParser import ConfigParser

import math

from mwif_map_reader import MWIFMapReader

## CONSTANTS

SQRT3 = math.sqrt(3.0)
SQRT3BY2 = SQRT3 / 2.0

## HELPERS

def html2float(html_colour_str):
    """converts HTML colour code to a rgb tuple of values in (0.0,1.0]"""
    assert isinstance(html_colour_str, str)
    assert html_colour_str.startswith("#")
    assert len(html_colour_str) == 7

    r = int(html_colour_str[1:3], 16) / 255.0
    g = int(html_colour_str[3:5], 16) / 255.0
    b = int(html_colour_str[5:7], 16) / 255.0

    return r, g, b


## CLASSES

class MapSurface(object):
    """wrapper to render to a cairo context to svg"""

    def __init__(self, hexmap=None, filename=None, width=None, height=None, size=None):
        self.hexmap = hexmap
        if self.hexmap is None:
            raise ValueError("No map was passed to {}".format(self.__class__.__name__))
        self.surface_name = filename or "test.svg"
        self.surface_width = width or 640.0
        self.surface_height = height or 480.0
        self.size = size or 32
        self.pipeline = []

        # build base map
        self.surface = SVGSurface(self.surface_name + ".svg", self.surface_width, self.surface_height)
        self.context = Context(self.surface)
        # background: magenta
        self.context.save()
        self.context.set_source_rgb(1.0, 0.0, 1.0)
        self.context.paint()
        self.context.restore()

    def add_renderer(self, renderer_cls, position=None):
        self.pipeline.append(renderer_cls(self))

    def render(self):
        for renderer in self.pipeline:
            renderer.render()

    def finalise(self, with_png=False):
        self.surface.write_to_png(self.surface_name + ".png")
        self.surface.finish()


class BaseRenderer(object):
    def __init__(self, surface, *args, **kwargs):
        self.surface = surface

    def render(self, context=None):
        ctx = context or self.surface.context
        ctx.save()
        self._render(ctx)
        ctx.restore()

    def _render(self, ctx):
        raise NotImplementedError


class TerrainRenderer(BaseRenderer):
    cp = ConfigParser().read(["settings.cfg", "./settings.cfg", "./mwifmap/settings.cfg"])
    TER_CODE = {
        0: "#38848d", # "all sea",
        1: "#a9cad7", # "lake",
        2: "#c8cf46", # "clear",
        3: "#00a73e", # "forest",
        4: "#107032", # "jungle",
        5: "#727070", # "mountain",
        6: "#b7ddc8", # "swamp",
        7: "#ead065", # "desert",
        8: "#b19150", # "desert mountain",
        9: "#dfdfde", # "tundra",
        10: "#ffffff", # "ice",
        11: "#783c3c", # "quattara depression"
    }
    del cp


class GridRenderer(BaseRenderer):
    """pointy head, odd row off set grid renderer"""

    cp = ConfigParser()
    cp.read(["settings.cfg", "./settings.cfg", "./mwifmap/settings.cfg"])
    GRID_COLOUR = cp.get("colour", "grid")
    del cp

    def __init__(self, surface, *args, **kwargs):
        super(GridRenderer, self).__init__(surface, *args, **kwargs)
        self.hexmap = self.surface.hexmap.map
        self.size = self.surface.size
        self.cell = [
            (self.size * SQRT3BY2, 0),
            (self.size * SQRT3, self.size * 0.5),
            (self.size * SQRT3, self.size * 1.5),
            (self.size * SQRT3BY2, self.size * 2.0),
            (0, self.size * 1.5),
            (0, self.size * 0.5),
        ]

    def _render(self, ctx):
        grid_col = html2float(self.GRID_COLOUR)
        for row in range(self.hexmap.rows):
            # alternate the offset of the cells based on row
            offset = self.surface.size * SQRT3BY2 if row % 2 else 0
            for col in range(self.hexmap.cols):
                # calc points
                top = 1.5 * row * self.size
                left = offset + col * self.size * SQRT3
                points = [(x + left, y + top) for x, y in self.cell]

                # draw the polygon onto the surface
                ctx.set_source_rgb(*grid_col)
                ctx.move_to(*points[0])
                ctx.line_to(*points[1])
                ctx.line_to(*points[2])
                ctx.line_to(*points[3])
                ctx.line_to(*points[4])
                ctx.line_to(*points[5])
                ctx.close_path()
                ctx.set_line_width(0.2)
                ctx.stroke()
                ctx.save()

## TEST
def test1():
    for html_colour in ["#123456", "#000000", "#FFFFFF"]:
        print html_colour, ":", html2float(html_colour)


def test2():
    m = MWIFMapReader()
    m.load_ter()

    m = MWIFMapReader()
    m.load_ter()

    ms = MapSurface(m, "example2", 640, 480, 32)
    ms.add_renderer(GridRenderer)
    ms.render()
    ms.finalise()

## MAIN

if __name__ == '__main__':
    test2()

## EOF
