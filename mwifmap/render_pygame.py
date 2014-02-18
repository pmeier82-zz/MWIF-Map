"""render map using pygame"""

## IMPORTS

from abc import abstractmethod
import pygame
import math
from hexmap import HexMap

## CONSTANTS

SQRT3 = math.sqrt(3.0)
SQRT3BY2 = SQRT3 / 2.0

## CLASSES

class Render(pygame.Surface):
    # __metaclass__ = ABCMeta

    def __init__(self, map_, size=16, *args, **kwargs):
        self.map = map_
        self.size = size
        # pointy head cell

        self.cell = [
            (int(round(self.size * SQRT3BY2)), int(0)),
            (int(round(self.size * SQRT3)), int(round(self.size * 0.5))),
            (int(round(self.size * SQRT3)), int(round(self.size * 1.5))),
            (int(round(self.size * SQRT3BY2)), int(round(self.size * 2.0))),
            (int(0), int(round(self.size * 1.5))),
            (int(0), int(round(self.size * 0.5))),
        ]

        # Colors for the map
        self.GRID_COLOR = pygame.Color(50, 50, 50)

        # super
        super(Render, self).__init__((self.width, self.height), *args, **kwargs)

    @property
    def width(self):
        return int(round((self.map.cols + .5) * self.size * SQRT3))

    @property
    def height(self):
        return int(round((self.map.rows - 1) * self.size * 2))

    # Draw methods
    @abstractmethod
    def draw(self):
        """abstract base method. If called via super, it fills the screen with the colorkey (Default: #FF00FF)"""
        colorkey = self.get_colorkey() or pygame.Color(0xff, 0x0, 0xff)
        self.fill(colorkey)

    # Identify cell
    def get_cell(self, (x, y)):
        """identify the cell clicked in terms of row and column, None of offmap"""
        q = (1 / 3 * SQRT3 * x - 1 / 3 * y) / self.size
        r = 2 / 3 * y / self.size

        return (q, r) if self.map.valid_cell((q, r)) else None

    def fit_window(self, window):
        top = int(round(max(window.get_height() - self.height, 0)))
        left = int(round(max(window.get_width() - self.width, 0)))
        return top, left

    def get_surface(self, (q, r)):
        """returns a subsurface corresponding to the surface"""
        height = self.size * 2
        width = self.size * SQRT3

        top = int(round(1.5 * self.size * r))
        left = int(round((q - math.ceil(r / 2.0)) * width + (width / 2 if r % 2 == 1 else 0)))

        return self.subsurface(pygame.Rect(left, top, width, height))


class RenderUnits(Render):
    """render object that will automatically draw the Units from the map"""

    def __init__(self, map_, *args, **keywords):
        super(RenderUnits, self).__init__(map_, *args, **keywords)
        if not hasattr(self.map, 'units'):
            self.map.units = {}

    def draw(self):
        """
        Calls unit.paint for all units on self.map
        """
        super(RenderUnits, self).draw()
        units = self.map.units

        for position, unit in units.items():
            surface = self.get_surface(position)
            unit.paint(surface)


class RenderGrid(Render):
    def draw(self):
        """draws a hex grid, based on the map object, onto this Surface [ph, odd-r]"""
        super(RenderGrid, self).draw()
        # A point list describing a single cell, based on the radius of each hex

        for row in range(self.map.rows):
            # alternate the offset of the cells based on row
            offset = self.size * SQRT3BY2 if row % 2 else 0
            for col in range(self.map.cols):
                # calc offsets
                top = 1.5 * row * self.size
                left = offset + col * self.size * SQRT3
                # Create a point list containing the offset cell
                points = [(x + left, y + top) for x, y in self.cell]
                # Draw the polygon onto the surface
                pygame.draw.polygon(self, self.GRID_COLOR, points, 1)


def trim_cell(surface):
    pass


if __name__ == '__main__':
    from hexmap import HexMap
    import sys

    class Unit(object):
        color = pygame.Color(200, 200, 200)

        def paint(self, surface):
            radius = surface.get_width() / 2
            pygame.draw.circle(surface, self.color, ( radius, int(SQRT3 / 2 * radius) ), int(radius - radius * .3))

    m = HexMap(5, 5)
    grid = RenderGrid(m, size=76)

    try:
        pygame.init()
        fpsClock = pygame.time.Clock()

        window = pygame.display.set_mode(( 640, 480 ), 1)
        from pygame.locals import QUIT, MOUSEBUTTONDOWN

        #Leave it running until exit
        while True:
            for event in pygame.event.get():
                if event.type == QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == MOUSEBUTTONDOWN:
                    print units.get_cell(event.pos)
            window.fill(pygame.Color('white'))
            grid.draw()
            window.blit(grid, (0, 0))
            pygame.display.update()
            fpsClock.tick(10)
    finally:
        pygame.quit()
