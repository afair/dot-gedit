# -*- coding: utf8 -*
#
#  Gedit plugin to open a terminal at the location of the current file.
#
#  Copyright (C) 2005, Ramzi Ferchichi <ramzi@gafouri.net>
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
#

import os 
import os.path

import gedit
import gtk
import gconf


OPEN_TERMINAL_HERE_UI = """
<ui>
  <menubar name="MenuBar">
    <menu name="ToolsMenu" action="Tools">
      <placeholder name="ToolsOps_2">
        <menuitem name="Open Terminal Here" action="OpenTerminalHere"/>
      </placeholder>
    </menu>
  </menubar>
  
  <popup name="NotebookPopup" action="NotebookPopupAction">
    <placeholder name="NotebookPupupOps_1">
      <menuitem name="Open Terminal Here" action="OpenTerminalHere"/>
    </placeholder>
  </popup>
</ui>
"""


#
# TODO:
#   - Handle non file:// uri's (check how nautilus-open-terminal does it)
#   - Thorough error checking
#   - I18N
#

class OpenTerminalHerePlugin(gedit.Plugin):

	def __init__(self):
		
		gedit.Plugin.__init__(self)
		self.conf_client = gconf.client_get_default()


	def open_terminal_cb(self, window):
		
		active_doc = window.get_active_document()
		document_dir = os.path.dirname(active_doc.get_uri()).replace("file://", "")

		terminal_exec = self.conf_client.get_string("/desktop/gnome/applications/terminal/exec")
		if not terminal_exec:
			terminal_exec = "gnome-terminal"

		os.chdir(document_dir)
		os.system(terminal_exec + "&")


	def activate(self, window):	
		
		action = ("OpenTerminalHere",
		          None,
		          "Open _Terminal Here",
		          None,
		          "Open Terminal Here",
		          lambda x, y: self.open_terminal_cb(y))
		
		action_group = gtk.ActionGroup("OpenTerminalHerePluginActions")
		action_group.add_actions([action], window)

		ui_manager = window.get_ui_manager()
		ui_manager.insert_action_group(action_group, 0)
		ui_id = ui_manager.add_ui_from_string(OPEN_TERMINAL_HERE_UI)
		
		windowdata = dict()
		windowdata["action_group"] = action_group
		windowdata["ui_id"] = ui_id
		
		window.set_data("OpenTerminalHerePluginInfo", windowdata)


	def deactivate(self, window):

		windowdata = window.get_data("OpenTerminalHerePluginInfo")
		
		ui_manager = window.get_ui_manager()
		ui_manager.remove_ui(windowdata["ui_id"])
		ui_manager.remove_action_group(windowdata["action_group"])
		ui_manager.ensure_update()


	def is_valid_doc(self, doc):
		
		return bool(doc and
				    doc.get_uri() and
					doc.get_uri().startswith("file://"))


	def update_ui(self, window):

		windowdata = window.get_data("OpenTerminalHerePluginInfo")
		active_doc = window.get_active_document()
		windowdata["action_group"].set_sensitive(self.is_valid_doc(active_doc))

