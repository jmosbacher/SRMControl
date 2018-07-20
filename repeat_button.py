from traits.api import *
from traitsui.ui_traits import Image
from traitsui.api import View
from traitsui.ui_traits import AView
from traitsui.qt4.button_editor import CustomEditor
from traitsui.editor_factory import EditorFactory
import cfg
GLOBALS = cfg.Globals()
import os
"""color: grey;
            border-image: url(/home/kamlie/code/button.png) 3 10 3 10;
            border-top: 3px transparent;
            border-bottom: 3px transparent;
            border-right: 10px transparent;
            border-left: 10px transparent;
        }"""
pushbutton = os.path.join(GLOBALS.ICON_DIR, 'pushbutton.png')
class _AutoRepeatButtonEditor(CustomEditor):
    auto_repeat = Bool(True)
    auto_repeat_interval = Int(100)
    auto_repeat_delay = Int(300)

    def init( self, parent):
        super(_AutoRepeatButtonEditor,self).init(parent)
        self.control.setAutoRepeat(self.auto_repeat)
        self.control.setAutoRepeatInterval(self.auto_repeat_interval)
        self.control.setAutoRepeatDelay(self.auto_repeat_delay)

        #self.control.setStyleSheet("border-radius: 10px;\n"
                                   #"border-style: outset;\n"
                                    #"border-width: 2px;\n"
                                    #"border-radius: 15px;\n"
                                    #"border-color: black;\n"
                                    #"padding: 4px;")

class ToolkitEditorFactory(EditorFactory):

    """ Editor factory for buttons.
    """

    # -------------------------------------------------------------------------
    #  Trait definitions:
    # -------------------------------------------------------------------------

    # Value to set when the button is clicked
    value = Property

    # Optional label for the button
    label = Str

    # The name of the external object trait that the button label is synced to
    label_value = Str

    # The name of the trait on the object that contains the list of possible
    # values.  If this is set, then the value, label, and label_value traits
    # are ignored; instead, they will be set from this list.  When this button
    # is clicked, the value set will be the one selected from the drop-down.
    values_trait = Trait(None, None, Str)

    # (Optional) Image to display on the button
    image = Image

    # Extra padding to add to both the left and the right sides
    width_padding = Range(0, 31, 7)

    # Extra padding to add to both the top and the bottom sides
    height_padding = Range(0, 31, 5)

    # Presentation style
    style = Enum('button', 'radio', 'toolbar', 'checkbox')

    # Orientation of the text relative to the image
    orientation = Enum('vertical', 'horizontal')

    # The optional view to display when the button is clicked:
    view = AView

    # -------------------------------------------------------------------------
    #  Traits view definition:
    # -------------------------------------------------------------------------

    traits_view = View(['label', 'value', '|[]'])

    # -------------------------------------------------------------------------
    #  Implementation of the 'value' property:
    # -------------------------------------------------------------------------

    def _get_value(self):
        return self._value

    def _set_value(self, value):
        self._value = value
        if isinstance(value, basestring):
            try:
                self._value = int(value)
            except:
                try:
                    self._value = float(value)
                except:
                    pass

    # -------------------------------------------------------------------------
    #  Initializes the object:
    # -------------------------------------------------------------------------
    def _get_simple_editor_class(self):

        return _AutoRepeatButtonEditor

    def _get_custom_editor_class(self):

        return _AutoRepeatButtonEditor

    def _get_text_editor_class(self):

        return _AutoRepeatButtonEditor

    def _get_readonly_editor_class(self):
        return _AutoRepeatButtonEditor

    def __init__(self, **traits):
        self._value = 0
        super(ToolkitEditorFactory,self).__init__(**traits)


# Define the ButtonEditor class
AutoRepeatButtonEditor = ToolkitEditorFactory
