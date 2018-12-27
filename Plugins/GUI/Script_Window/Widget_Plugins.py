
from collections import defaultdict

from PyQt5.QtWidgets import QTreeWidgetItem, QTreeWidget

from ... import Analyses
from ... import Transforms
from ... import Utilities


class Widget_Plugins(QTreeWidget):
    '''
    Tree view of all available plugins.
    Clicking a plugin will signal a separate documentation
    window to change text.
    '''
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Set up dragging.
        #tree.setAcceptDrops(True)
        self.setDragEnabled(True)

        # Clear the treeWidget_Plugins list and redraw it, according to
        #  the type filter.
        # TODO: is this needed?  forget why it was put here.
        self.clear()
                
        # Loop over the plugin subpackages.
        for subpackage in [Analyses, Transforms, Utilities]:
            plugin_type = subpackage.__name__.split('.')[-1]

            # Make a new leaf item.
            package_item = QTreeWidgetItem()

            # Set the name in column 0.
            package_item.setText(0, plugin_type)

            # Attach the widget item to the parent tree.
            self.addTopLevelItem(package_item)

            # Loop over defined plugins in it.
            category_plugin_dict = defaultdict(list)
            for item_name in dir(subpackage):
                item = getattr(subpackage, item_name)

                # Can check for the _plugin_type attribute, attached
                #  by the decorator.
                if not getattr(item, '_plugin_type', None):
                    continue
        
                # Skip if the file name starts with an underscore, indicating
                #  an experimental function.
                if item.__name__[0] == '_':
                    continue

                # Record this function for the category.
                category_plugin_dict[item._category].append(item)


            # TODO: nested categories.
            # For now, just a flat list.
            for category, plugin_list in category_plugin_dict.items():
                for plugin in plugin_list:

                    # Create a nested tree node.
                    subitem = QTreeWidgetItem()
                    # Assign the name as text to column 0.
                    subitem.setText(0, plugin.__name__)
                    # Attach the widget item to the parent tree.
                    package_item.addChild(subitem)
                    # Annotate the item with the plugin, for easy
                    # referencing.
                    subitem.plugin = plugin

        self.expandAll()

        self.currentItemChanged.connect(self.Handle_currentItemChanged)
        return


    def Handle_currentItemChanged(self, new_item = None):
        '''
        A different item was clicked on.
        '''
        if hasattr(new_item, 'plugin'):
            # Get the doc text.
            # Add shared documenation at the end.
            text = '\n'.join([new_item.plugin.__doc__] + new_item.plugin._shared_docs)

            # Send to the text viewer.
            self.window.widget_documentation.setPlainText(text)
        return

    
    # Somewhat funky, but just name this function mimeData to customize
    # what is sent during a drag event.
    # Goal is to drag out plain text, since the text edit window
    # can handle that naturally.
    # Idea taken from:
    # https://stackoverflow.com/questions/49951628/drag-and-drop-item-text-from-qtreeview-to-qlineedit
    def mimeData(self, selections):
        '''
        Customize the dragged item to have a text field.
        This includes the name of the plugin, and some automated formatting.
        '''
        mimedata = super().mimeData(selections)
        if selections:
            item = selections[0]
            
            if hasattr(item, 'plugin'):
                # Add empty args and a newline for now.
                # TODO: maybe add named args and defaults; that would
                # take some inspection. Alternatively, could create
                # custom defaults for each transform.
                text = item.plugin.__name__ + '()\n'
            else:
                # Don't copy over anything for non-plugins.
                text = ''
            mimedata.setText(text)

        return mimedata