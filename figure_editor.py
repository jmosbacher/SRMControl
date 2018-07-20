import matplotlib
matplotlib.use('Qt4Agg')
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from traitsui.qt4.editor import Editor
from traitsui.qt4.basic_editor_factory import BasicEditorFactory


class _MPLFigureEditor(Editor):

   scrollable  = True

   def init(self, parent):
       self.control = self._create_canvas(parent)
       self.set_tooltip()

   def update_editor(self):
       pass

   def _create_canvas(self, parent):
       """ Create the MPL canvas. """
       # matplotlib commands to create a canvas
       mpl_canvas = FigureCanvas(self.value)
       return mpl_canvas

class MPLFigureEditor(BasicEditorFactory):

   klass = _MPLFigureEditor