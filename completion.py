# Copyright (C) 2006-2008 Osmo Salomaa
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc., 51
# Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.

"""Complete words with the tab key."""

import gedit
import gobject
import gtk
import pango
import re


class CompletionWindow(gtk.Window):

    """Window for displaying a list of words to complete to."""

    def __init__(self, parent):

        gtk.Window.__init__(self, gtk.WINDOW_POPUP)
        self.store = None
        self.view = None
        self.set_transient_for(parent)
        self.init_view()
        self.init_containers()

    def get_selected(self):
        """Get the selected row."""

        selection = self.view.get_selection()
        return selection.get_selected_rows()[1][0][0]

    def init_containers(self):
        """Initialize the frame and the scrolled window."""

        scroller = gtk.ScrolledWindow()
        scroller.set_policy(*((gtk.POLICY_NEVER,) * 2))
        scroller.add(self.view)
        frame = gtk.Frame()
        frame.set_shadow_type(gtk.SHADOW_OUT)
        frame.add(scroller)
        self.add(frame)

    def init_view(self):
        """Initialize the tree view listing the complete words."""

        self.store = gtk.ListStore(gobject.TYPE_STRING)
        self.view = gtk.TreeView(self.store)
        renderer = gtk.CellRendererText()
        renderer.xpad = renderer.ypad = 6
        column = gtk.TreeViewColumn("", renderer, text=0)
        self.view.append_column(column)
        self.view.set_enable_search(False)
        self.view.set_headers_visible(False)
        self.view.set_rules_hint(True)
        selection = self.view.get_selection()
        selection.set_mode(gtk.SELECTION_SINGLE)

    def select_next(self):
        """Select the next complete word."""

        row = min(self.get_selected() + 1, len(self.store) - 1)
        selection = self.view.get_selection()
        selection.unselect_all()
        selection.select_path(row)
        self.view.scroll_to_cell(row)

    def select_previous(self):
        """Select the previous complete word."""

        row = max(self.get_selected() - 1, 0)
        selection = self.view.get_selection()
        selection.unselect_all()
        selection.select_path(row)
        self.view.scroll_to_cell(row)

    def set_completions(self, completions):
        """Set the completions to display."""

        self.resize(1, 1)
        self.store.clear()
        for word in completions:
            self.store.append((word,))
        self.view.columns_autosize()
        self.view.get_selection().select_path(0)

    def set_font_description(self, font_desc):
        """Set the font description used in the view."""

        self.view.modify_font(font_desc)


class CompletionPlugin(gedit.Plugin):

    """Complete words with the tab key."""

    re_alpha = re.compile(r"\w+", re.UNICODE | re.MULTILINE)
    re_non_alpha = re.compile(r"\W+", re.UNICODE | re.MULTILINE)

    def __init__(self):

        gedit.Plugin.__init__(self)
        self.all_words = {}
        self.completion_windows = {}
        self.completions = []
        self.favorite_words = {}
        self.font_ascent = 0
        self.remains = []

    def activate(self, window):
        """Activate plugin."""

        callback = self.on_window_tab_added
        id_1 = window.connect("tab-added", callback)
        callback = self.on_window_tab_removed
        id_2 = window.connect("tab-removed", callback)
        window.set_data(self.__class__.__name__, (id_1, id_2))
        for doc in window.get_documents():
            self.connect_document(doc)
            self.scan_document(doc)
        views = window.get_views()
        for view in views:
            self.connect_view(view, window)
        if views: self.update_fonts(views[0])
        self.completion_windows[window] = CompletionWindow(window)
        # Scan the active document in window if it has input focus
        # for new words at constant intervals.
        def scan(self, window):
            if not window.is_active(): return True
            return self.scan_active_document(window)
        priority = gobject.PRIORITY_LOW
        gobject.timeout_add(10000, scan, self, window, priority=priority)

    def complete_current(self):
        """Complete the current word."""

        window = gedit.app_get_default().get_active_window()
        doc = window.get_active_document()
        index = self.completion_windows[window].get_selected()
        doc.insert_at_cursor(self.remains[index])
        if not doc in self.favorite_words:
            self.favorite_words[doc] = set(())
        self.favorite_words[doc].add(self.completions[index])
        self.terminate_completion()

    def connect_document(self, doc):
        """Connect to document's 'loaded' signal."""

        callback = lambda doc, x, self: self.scan_document(doc)
        handler_id = doc.connect("loaded", callback, self)
        doc.set_data(self.__class__.__name__, (handler_id,))

    def connect_view(self, view, window):
        """Connect to view's editing signals."""

        callback = lambda x, y, self: self.terminate_completion()
        id_1 = view.connect("focus-out-event", callback, self)
        callback = self.on_view_key_press_event
        id_2 = view.connect("key-press-event", callback, window)
        view.set_data(self.__class__.__name__, (id_1, id_2))

    def deactivate(self, window):
        """Deactivate plugin."""

        widgets = [window]
        widgets.extend(window.get_views())
        widgets.extend(window.get_documents())
        name = self.__class__.__name__
        for widget in widgets:
            for handler_id in widget.get_data(name):
                widget.disconnect(handler_id)
            widget.set_data(name, None)
        self.terminate_completion()
        self.completion_windows.pop(window)
        for doc in window.get_documents():
            self.all_words.pop(doc, None)
            self.favorite_words.pop(doc, None)

    def display_completions(self, view, event):
        """Find completions and display them in the completion window."""

        doc = view.get_buffer()
        insert = doc.get_iter_at_mark(doc.get_insert())
        start = insert.copy()
        while start.backward_char():
            char = unicode(start.get_char())
            if not self.re_alpha.match(char):
                start.forward_char()
                break
        incomplete = unicode(doc.get_text(start, insert))
        incomplete += unicode(event.string)
        if incomplete.isdigit():
            return self.terminate_completion()
        self.find_completions(doc, incomplete)
        if not self.completions:
            return self.terminate_completion()
        self.show_completion_window(view, insert)

    def find_completions(self, doc, incomplete):
        """Find completions for incomplete word and save them."""

        self.completions = []
        self.remains = []
        favorites = self.favorite_words.get(doc, ())
        all_words = set(())
        for words in self.all_words.values():
            all_words.update(words)
        for sequence in (favorites, all_words):
            for word in sequence:
                if not word.startswith(incomplete): continue
                if word == incomplete: continue
                if word in self.completions: continue
                self.completions.append(word)
                self.remains.append(word[len(incomplete):])
                if len(self.remains) > 5: break

    def on_view_key_press_event(self, view, event, window):
        """Manage actions for completions and the completion window."""

        if event.state & gtk.gdk.CONTROL_MASK:
            return self.terminate_completion()
        if event.state & gtk.gdk.MOD1_MASK:
            return self.terminate_completion()
        if (event.keyval == gtk.keysyms.Tab) and self.remains:
            return not self.complete_current()
        completion_window = self.completion_windows[window]
        if (event.keyval == gtk.keysyms.Up) and self.remains:
            return not completion_window.select_previous()
        if (event.keyval == gtk.keysyms.Down) and self.remains:
            return not completion_window.select_next()
        string = unicode(event.string)
        if len(string) != 1:
            return self.terminate_completion()
        if self.re_alpha.match(string) is None:
            return self.terminate_completion()
        doc = view.get_buffer()
        insert = doc.get_iter_at_mark(doc.get_insert())
        if self.re_alpha.match(unicode(insert.get_char())):
            return self.terminate_completion()
        return self.display_completions(view, event)

    def on_window_tab_added(self, window, tab):
        """Connect to signals of the document and view in tab."""

        self.update_fonts(tab.get_view())
        self.connect_document(tab.get_document())
        self.connect_view(tab.get_view(), window)

    def on_window_tab_removed(self, window, tab):
        """Remove closed document's word and favorite sets."""

        doc = tab.get_document()
        if doc in self.all_words:
            self.all_words.pop(doc)
        if doc in self.favorite_words:
            self.favorite_words.pop(doc)

    def scan_active_document(self, window):
        """Scan all the words in the active document in window."""

        # Return False to not scan again.
        if window is None: return False
        doc = window.get_active_document()
        if doc is not None:
            self.scan_document(doc)
        return True

    def scan_document(self, doc):
        """Scan and save all words in document."""

        text = unicode(doc.get_text(*doc.get_bounds()))
        self.all_words[doc] = frozenset(self.re_non_alpha.split(text))

    def show_completion_window(self, view, itr):
        """Show the completion window below the cursor."""

        text_window = gtk.TEXT_WINDOW_WIDGET
        rect = view.get_iter_location(itr)
        x, y = view.buffer_to_window_coords(text_window, rect.x, rect.y)
        window = gedit.app_get_default().get_active_window()
        x, y = view.translate_coordinates(window, x, y)
        x += window.get_position()[0] + self.font_ascent
        # Use 24 pixels as an estimate height for window title bar.
        y += window.get_position()[1] + 24 + (2 * self.font_ascent)
        completion_window = self.completion_windows[window]
        completion_window.set_completions(self.completions)
        completion_window.move(int(x), int(y))
        completion_window.show_all()

    def terminate_completion(self):
        """Hide the completion window and cancel completions."""

        window = gedit.app_get_default().get_active_window()
        self.completion_windows[window].hide()
        self.completions = []
        self.remains = []

    def update_fonts(self, view):
        """Update font descriptions and ascent metrics."""

        context = view.get_pango_context()
        font_desc = context.get_font_description()
        if self.font_ascent == 0:
            metrics = context.get_metrics(font_desc, None)
            self.font_ascent = metrics.get_ascent() / pango.SCALE
        for completion_window in self.completion_windows.values():
            completion_window.set_font_description(font_desc)
