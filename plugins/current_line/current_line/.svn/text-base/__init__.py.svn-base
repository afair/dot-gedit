import gedit
import gtk
import gconf
import os
import os.path

GCONF_KEY_BASE = '/apps/gedit-2/plugins/currentline'
GCONF_KEY_FOREGROUND = '/apps/gedit-2/plugins/currentline/foreground'
GCONF_KEY_BACKGROUND = '/apps/gedit-2/plugins/currentline/background'
GCONF_KEY_APPLY = '/apps/gedit-2/plugins/currentline/apply'
GLADE_FILE = os.path.join(os.path.dirname(__file__), "current-line.glade")

class CurrentLine(gedit.Plugin):
    def __init__(self):
        gedit.Plugin.__init__(self)
        gconf.client_get_default().notify_add(GCONF_KEY_BASE, self.on_gconf_notify)
    
    def activate(self, window):
        self.window = window
        self.window.connect('tab-added', self.on_tab_added)
    
    def on_tab_added(self, window, tab):
        view = tab.get_view()
        self.set_colors(view)
    
    def on_gconf_notify(self, client, id, entry, data):
        for view in self.window.get_views():
            self.set_colors(view)
    
    def set_colors(self, view):
        if gconf_get_bool(GCONF_KEY_APPLY):
            fgcolor = gconf_get_str(GCONF_KEY_FOREGROUND, '#000')
            bgcolor = gconf_get_str(GCONF_KEY_BACKGROUND, '#EEE')
            
            view.modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse(bgcolor))
            view.modify_fg(gtk.STATE_NORMAL, gtk.gdk.color_parse(fgcolor))
        else:
            pass
    
    def create_configure_dialog(self):
        glade_xml = gtk.glade.XML(GLADE_FILE)
        
        self.config_dialog = glade_xml.get_widget('window1')
        self.config_dialog.connect('delete_event', self.on_config_close)
        
        fg_button = glade_xml.get_widget('foreground_button')
        fg_button.connect('color-set', self.on_color_set)
        fg_color = gtk.gdk.color_parse(gconf_get_str(GCONF_KEY_FOREGROUND, '#000'))

        bg_button = glade_xml.get_widget('background_button')
        bg_button.connect('color-set', self.on_color_set)
        bg_color = gtk.gdk.color_parse(gconf_get_str(GCONF_KEY_BACKGROUND, '#eee'))

        close_button = glade_xml.get_widget('close_button')
        close_button.connect('clicked', self.on_close)

        apply_colors = glade_xml.get_widget('apply_colors')
        apply_colors.connect('toggled', self.on_apply)
        do_apply = gconf_get_bool(GCONF_KEY_APPLY)

        bg_button.set_color(bg_color)
        fg_button.set_color(fg_color)
        apply_colors.set_active(do_apply)
        
        return self.config_dialog
    
    def on_config_close(self, *args):
        self.config_dialog.destroy()
    
    def on_close(self, *args):
        self.on_config_close(self)
    
    def on_color_set(self, widget):
        color = widget.get_color()
        value = "#%04x%04x%04x" % (color.red, color.green, color.blue)
        
        if widget.get_name() == 'background_button':
            path = GCONF_KEY_BACKGROUND
        else:
            path = GCONF_KEY_FOREGROUND
        
        gconf_set_str(path, value)
    
    def on_apply(self, widget):
        gconf_set_bool(GCONF_KEY_APPLY, widget.get_active())

def gconf_get_bool(key, default = False):
    val = gconf.client_get_default().get(key)
    if val is not None and val.type == gconf.VALUE_BOOL:
        return val.get_bool()
    else:
        return default

def gconf_set_bool(key, value):
    v = gconf.Value(gconf.VALUE_BOOL)
    v.set_bool(value)
    gconf.client_get_default().set(key, v)

def gconf_get_str(key, default = ''):
    val = gconf.client_get_default().get(key)
    if val is not None and val.type == gconf.VALUE_STRING:
        return val.get_string()
    else:
        return default

def gconf_set_str(key, value):
    v = gconf.Value(gconf.VALUE_STRING)
    v.set_string(value)
    gconf.client_get_default().set(key, v)
