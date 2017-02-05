__kupfer_name__ = _("Quick Image Viewer")
__kupfer_actions__ = ("View", )
__description__ = ""
__version__ = ""
__author__ = ""

import shutil

from gi.repository import Gio
import gio
import glib
import gtk
from gi.repository import GdkPixbuf

from kupfer.objects import Action, FileLeaf
from kupfer.objects import OperationError
from kupfer import utils


def is_content_type(fileleaf, ctype):
    predicate = Gio.content_type_is_a
    ctype_guess, uncertain = Gio.content_type_guess(fileleaf.object, None)
    ret = predicate(ctype_guess, ctype)
    if ret or not uncertain:
        return ret
    content_attr = Gio.FILE_ATTRIBUTE_STANDARD_CONTENT_TYPE
    gfile = Gio.File.new_for_path(fileleaf.object)
    if not gfile.query_exists(None):
        return
    info = gfile.query_info(content_attr, Gio.FileQueryInfoFlags.NONE, None)
    content_type = info.get_attribute_string(content_attr)
    return predicate(content_type, ctype)

def _set_size(loader, width, height, max_w, max_h):
    if width <= max_w and height <= max_h:
        return
    w_scale = max_w*1.0/width
    h_scale = max_h*1.0/height
    scale = min(w_scale, h_scale)
    loader.set_size(int(width*scale), int(height*scale))

def load_image_max_size(filename, w, h):
    pl = GdkPixbuf.PixbufLoader()
    pl.connect("size-prepared", _set_size, w, h)
    try:
        with open(filename, "rb") as f:
            shutil.copyfileobj(f, pl)
        pl.close()
    except (glib.GError, EnvironmentError) as exc:
        raise OperationError(exc)
    return pl.get_pixbuf()

class View (Action):
    def __init__(self):
        Action.__init__(self, _("View Image"))
        self.open_windows = {}

    def item_types(self):
        yield FileLeaf

    def valid_for_item(self, obj):
        return is_content_type(obj, "image/*")

    def wants_context(self):
        return True

    def activate(self, obj, ctx):
        ## If the same file @obj is already open,
        ## then close its window.
        if obj.object in self.open_windows:
            open_window = self.open_windows.pop(obj.object)
            open_window.destroy()
            return
        image_widget = gtk.Image()
        h = gtk.gdk.screen_height()
        w = gtk.gdk.screen_width()
        image_widget.set_from_pixbuf(load_image_max_size(obj.object, w, h))
        image_widget.show()
        window = gtk.Window() 
        window.set_title(str(obj))
        window.set_position(gtk.WIN_POS_CENTER)
        window.add(image_widget)
        ctx.environment.present_window(window)
        window.connect("key-press-event", self.window_key_press, obj.object)
        window.connect("delete-event", self.window_deleted, obj.object)
        self.open_windows[obj.object] = window

    def window_deleted(self, window, event, filename):
        self.open_windows.pop(filename, None)
        return False

    def window_key_press(self, window, event, filepath):
        if gtk.gdk.keyval_name(event.keyval) == "Escape":
            self.window_deleted(window, event, filepath)
            window.destroy()
            return True
        if gtk.gdk.keyval_name(event.keyval) == "Return":
            self.window_deleted(window, event, filepath)
            utils.show_path(filepath)
            window.destroy()
            return True

    def get_description(self):
        return None

