# System library imports
from pyface.qt import QtCore, QtGui
# ETS imports
from traitsui.qt4.table_editor import TableDelegate


class ProgressRenderer(TableDelegate):
    """ A renderer which displays a progress bar.
    """

    #-------------------------------------------------------------------------
    #  QAbstractItemDelegate interface
    #-------------------------------------------------------------------------

    def paint(self, painter, option, index):
        """ Paint the progressbar. """
        # Get the column and object
        column = index.model()._editor.columns[index.column()]
        obj = index.data(QtCore.Qt.UserRole)

        # set up progress bar options
        progress_bar_option = QtGui.QStyleOptionProgressBar()
        progress_bar_option.rect = option.rect
        progress_bar_option.minimum = column.get_minimum(obj)
        progress_bar_option.maximum = column.get_maximum(obj)
        progress_bar_option.progress = int(column.get_raw_value(obj))
        progress_bar_option.textVisible = column.get_text_visible()
        progress_bar_option.text = column.get_value(obj)

        # Draw it
        style = QtGui.QApplication.instance().style()
        style.drawControl(QtGui.QStyle.CE_ProgressBar, progress_bar_option,
                          painter)

#------------------------------------------------------------------------------
#
#  Copyright (c) 2016, Enthought, Inc.
#  All rights reserved.
#
#  This software is provided without warranty under the terms of the BSD
#  license included in enthought/LICENSE.txt and may be redistributed only
#  under the conditions described in the aforementioned license.  The license
#  is also available online at http://www.enthought.com/licenses/BSD.txt
#
#  Thanks for using Enthought open source!
#
#  Author: Corran Webster
#
#------------------------------------------------------------------------------

""" A column class for for the TableEditor that displays progress bars. """

from traits.etsconfig.api import ETSConfig
from traits.api import Bool, Int, Str

from traitsui.table_column import ObjectColumn


if ETSConfig.toolkit == 'qt4':
    pass
    #from traitsui.qt4.extra.progress_renderer import ProgressRenderer
else:
    raise NotImplementedError("No pregress column renderer for backend")


class ProgressColumn(ObjectColumn):
    """ A column which displays trait values as a progress bar

    Progress values must be an integer value between the maximum and minimum
    values.  By default it is assumed to be a percentage.
    """

    #: Format string to apply to column values.
    format = Str('%s%%')

    #: The minimum value for a progress bar.
    minimum = Int(0)

    #: The maximum value for a progress bar.
    maximum = Int(100)

    #: Whether or not to display the text with the progress bar.
    #: This may not display with some progress bar styles, eg. on OS X.
    text_visible = Bool(True)

    def __init__(self, **traits):
        super(ProgressColumn, self).__init__(**traits)
        # force the renderer to be a progress bar renderer
        self.renderer = ProgressRenderer()

    def is_editable(self, object):
        """ Returns whether the column is editable for a specified object.
        """
        # Progress columns are always read-only
        return False

    def get_minimum(self, object):
        return self.minimum

    def get_maximum(self, object):
        return self.maximum

    def get_text_visible(self):
        """ Whether or not to display text in column.

        Note, may not render on some platforms (eg. OS X) due to
        the rendering style.
        """
        return self.text_visible

from traits.api import *
from traitsui.api import *
import sys


def progress_bar( nmin=0.0, nmax=100.0, nsymb=10, show_perc=True,
                  left_symb=u'\u2592', done_symb=u'\u2593'):
    def render_prog_str(n):
        if not isinstance(n, (int,float)):
            return u''

        frac = (n-nmin)/(nmax-nmin)
        perc = int(frac * 100)
        if n>=nmax:
            ndone = nsymb
            perc = 100
        else:
            ndone = int(frac * nsymb)
        if n<=nmin:
            nleft = nsymb
            perc = 0
        else:
            nleft = nsymb - ndone
        parts = [done_symb for i in range(ndone)]
        parts += [left_symb for i in range(nleft)]
        if show_perc:
            parts.append(u' {}%'.format(int(perc)))
        return u''.join(parts)
    return render_prog_str
render_done = progress_bar(nsymb=30)

class HasProg(HasTraits):
    done = Int(0)

class ProgressTable(TableEditor):
    columns = [
        ObjectColumn(name='done', label='Done', format_func=progress_bar(nsymb=5),width=0.20),
        #ProgressColumn(name='perc_done', label='Percent', width=0.20),
    ]


class Tester(HasTraits):

    progresses = List([HasProg() for n in range(3)])
    inc = Button('UP')
    dec = Button('DOWN')
    done = Int(0)
    done_str = Str()

    view = View(
        Item(name='inc',show_label=False),
        Item(name='dec', show_label=False),
        Item(name='done',format_func=progress_bar(nsymb=20),style='simple', show_label=False),
        #Item(name='tu', editor=TupleEditor(),show_label=False),
        Item(name='progresses',editor=ProgressTable(),show_label=False),
        #Item(name='prog', editor=ProgressEditor(), show_label=False),
        statusbar=[StatusItem(name='done_str')],
    resizable=True)

    def _done_str_default(self):
        return render_done(self.done)

    @on_trait_change('done')
    def update(self):
        self.done_str = render_done(self.done)

    def _inc_fired(self):
        self.done += 5
        for prog in self.progresses:
            prog.done +=5


    def _dec_fired(self):
        self.done -= 5
        for prog in self.progresses:
            prog.done -= 5


if __name__=='__main__':
    t = Tester()
    t.configure_traits()