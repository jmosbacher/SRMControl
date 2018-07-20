#!/usr/bin/python
# -*- coding: utf-8 -*-
# Pierre Haessig — March 2014

from pyface.qt import QtGui, QtCore
from traits.etsconfig.api import ETSConfig
ETSConfig.toolkit = 'qt4'

import guiqwt as gqt
import guidata as gdt

from traits.api import Any, Instance
from traitsui.qt4.editor import Editor
from traitsui.qt4.basic_editor_factory import BasicEditorFactory
from traitsui.api import Handler



class _MPLFigureEditor(Editor):

   scrollable  = True
   frame = Instance(QtGui.QWidget)
   canvas = Instance()
   toolbar = Instance()
   vbox = Instance(QtGui.QVBoxLayout)

   def init(self, parent):
       self.control = self._create_canvas(parent)
       self.set_tooltip()

   def update_editor(self):
       pass

   def _create_canvas(self, parent):
       ''' Create the MPL canvas. '''
       # matplotlib commands to create a canvas

       self.frame = frame = QtGui.QWidget()
       self.canvas = mpl_canvas = gqt.frame(self.value)
       mpl_canvas.setParent(frame)
       self.toolbar = mpl_toolbar = NavigationToolbar2QT(mpl_canvas,frame)

       self.vbox = vbox = QtGui.QVBoxLayout()
       vbox.addWidget(mpl_canvas)
       vbox.addWidget(mpl_toolbar)
       frame.setLayout(vbox)

       return frame



class MPLFigureEditor(BasicEditorFactory):

   klass = _MPLFigureEditor

class MPLInitHandler(Handler):
    """Handler calls mpl_setup() to initialize mpl events"""

    def init(self, info):
        """This method gets called after the controls have all been
        created but before they are displayed.
        """
        info.object.mpl_setup()
        return True

if __name__ == "__main__":
    # Create a window to demo the editor
    from traits.api import HasTraits
    from traitsui.api import View, Item
    from numpy import sin, cos, linspace, pi
    from matplotlib.widgets import  RectangleSelector

    class Test(HasTraits):

        figure = Instance(Figure, ())

        view = View(Item('figure', editor=MPLFigureEditor(),
                         show_label=False),
                    handler=MPLInitHandler,
                    resizable=True)

        def __init__(self):
            super(Test, self).__init__()
            self.axes = self.figure.add_subplot(312)
            t = linspace(0, 2*pi, 200)
            self.axes.plot(sin(t)*(1+0.5*cos(11*t)), cos(t)*(1+0.5*cos(11*t)))

        def mpl_setup(self):
            def onselect(eclick, erelease):
                print( "eclick: {}, erelease: {}".format(eclick,erelease))

            self.rs = RectangleSelector(self.axes, onselect,
                                        drawtype='box',useblit=True)

    Test().configure_traits()