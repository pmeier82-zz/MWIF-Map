"""utility function for recreating the MWiF map"""

## IMPORTS

import math
import base64
from configparser import ConfigParser
from io import BytesIO
from PIL import Image

## CONSTANTS

SQRT3 = math.sqrt(3.0)
SQRT3BY2 = SQRT3 / 2.0

## SETTINGS

cp = ConfigParser()
cp.read(["settings.cfg", "./settings.cfg", "./mwifmap/settings.cfg"])
SETTINGS = cp._sections
del cp


## HELPERS

def pil_img_resize(image, scale):
    if scale == 1.0:
        return image
    dims = tuple(int(ii * scale) for ii in image.size)
    return image.resize(dims, Image.ANTIALIAS if scale < 1.0 else Image.BICUBIC)


def pil_img_to_b64_png(image):
    """
    :param image:
    :parameters:
        PIL.Image : image
            the image to be converted
    :returns:
        str : the image string in base64
        tuple : width, height tuple
    """

    # temporary byte buffer
    buf = BytesIO()
    # save as small as possible
    image.save(buf, format="PNG", optimize=True)
    # get base64 repr and strip null bytes
    image_str = base64.b64encode(buf.getvalue()).decode()
    # image_str = base64.b64encode(image.tobytes()).decode()
    buf.close()
    del buf
    # return byte data and image dimensions
    return image_str, image.size


def html2f(html_colour_str):
    """converts HTML colour code to rgb tuple of values in (0.0, 1.0]"""

    assert isinstance(html_colour_str, str)
    assert html_colour_str.startswith("#")
    assert len(html_colour_str) == 7

    r = int(html_colour_str[1:3], 16) / 255.0
    g = int(html_colour_str[3:5], 16) / 255.0
    b = int(html_colour_str[5:7], 16) / 255.0

    return r, g, b


def get_hex_proto(scale=1.0):
    """return the list of points that from a hex shape"""

    try:
        rval = []
        point_str = SETTINGS["hex"]["prototype"]
        point_str = point_str.split("#")[0]
        points = point_str.strip().split(",")
        assert len(points) == 12, "invalid length of {}".format(len(points))
        for ii in range(6):
            rval.append((
                float(points.pop(0)) * float(scale),
                float(points.pop(0)) * float(scale),
            ))
        return tuple(rval)
    except:
        return (68., 0.), (136., 38.), (136., 114.), (68., 152.), (0., 114.), (0., 38.)


def get_hex_bb(scale=1.0):
    proto = get_hex_proto(scale)
    rval = [0, 0, 0, 0]
    for entry in proto:
        rval[0] = min(rval[0], entry[0])
        rval[1] = min(rval[1], entry[1])
        rval[2] = max(rval[2], entry[0])
        rval[3] = max(rval[3], entry[1])
    return tuple(rval)


def get_hex_clock_pos(clock_pos, center=None, radius=None, dist=None, integer=True):
    if center is None:
        center = (0, 0)
    if radius is None:
        radius = 1.0
    if dist is None:
        dist = 0.0
    proto = {
        1: (0.5, -SQRT3BY2),
        2: (SQRT3BY2, -0.5),
        3: (1.0, 0.0),
        4: (SQRT3BY2, 0.5),
        5: (0.5, SQRT3BY2),
        6: (0.0, 1.0),
        7: (-0.5, SQRT3BY2),
        8: (-SQRT3BY2, 0.5),
        9: (-1.0, 0.0),
        10: (-SQRT3BY2, -0.5),
        11: (-0.5, -SQRT3BY2),
        12: (-0.0, -1.0),
    }.get(clock_pos - 12 if clock_pos > 12 else clock_pos, (0.0, 0.0))
    dist_base = {
        True: 0.5,
        False: 2. / 3.
    }.get(clock_pos > 12, 0.0)
    rval = [center[0] + proto[0] * radius * (dist_base + dist), center[1] + proto[1] * radius * (dist_base + dist)]
    if integer is True:
        rval = map(round, rval)
    return tuple(rval)


def get_hex_dims(scale=1.0):
    bb = get_hex_bb(scale)
    return bb[2] - bb[0], bb[3] - bb[1]


## MAIN

if __name__ == "__main__":
    print(get_hex_proto())
    print(get_hex_proto(2))
    print(get_hex_proto(.5))

    print("#" * 50)

## EOF
