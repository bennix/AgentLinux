import ctypes
from ctypes import c_uint32, c_void_p

import cairo
from gi.repository import Gdk


class XcursorImage(ctypes.Structure):
    _fields_ = [(key, c_uint32) for key in
                ("version", "size", "width", "height", "xhot", "yhot", "delay")] + [("pixels", c_void_p)]


library = ctypes.CDLL("libXcursor.so.1")
library.XcursorLibraryLoadImage.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int]
library.XcursorLibraryLoadImage.restype = ctypes.POINTER(XcursorImage)
library.XcursorImageDestroy.argtypes = [ctypes.POINTER(XcursorImage)]
library.XcursorImageDestroy.restype = None


def cursor_pixbuf(theme, name, size):
    image = library.XcursorLibraryLoadImage(name.encode(), theme.encode() or None, size)
    if not image:
        return None
    try:
        frame = image.contents
        stride = frame.width * 4
        pixels = bytearray(ctypes.string_at(frame.pixels, stride * frame.height))
        surface = cairo.ImageSurface.create_for_data(pixels, cairo.FORMAT_ARGB32, frame.width, frame.height, stride)
        return Gdk.pixbuf_get_from_surface(surface, 0, 0, frame.width, frame.height)
    finally:
        library.XcursorImageDestroy(image)
