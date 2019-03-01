from __future__ import print_function
from traits.api import HasTraits, Str, Bool, Trait, Int, Instance, Button, Property, List, Any
from traitsui.api import View, UItem, TextEditor, TabularEditor, ListStrEditor, Item, Handler,HGroup
from traitsui.tabular_adapter import TabularAdapter
from pyface.api import GUI
from traits.etsconfig.api import ETSConfig
from collections import deque
from time import sleep
import textwrap
import logging
from threading import Thread
from timeit import default_timer as timer

DEFAULT_BUFFER_SIZE = 100000
DEFAULT_VIEW_SIZE = 10000
DEFAULT_MAX_MESSAGE_LENGTH = 60



class StringListAdapter(TabularAdapter):

    columns = [ ('Log', 'myvalue') ]
    myvalue_text = Property

    def _get_myvalue_text(self):
        return self.item

log_editor = TabularEditor(
    show_titles=True,
    operations=[],
    editable=False,
    selectable=False,
    horizontal_lines=False,
    adapter=StringListAdapter())

class _LogStreamHandler(Handler):

    def object_scroll_changed(self, uiinfo):
        if uiinfo.ui is None:
            return

        if ETSConfig.toolkit == 'qt4':
            for ed in uiinfo.ui._editors:
                if ed.name=='log':
                    break
        else:
            return
        ed.scroll_to_row = len(uiinfo.object.log)-2

class LogStream(HasTraits):
    # The text that has been written with the 'write' method.
    log = List([])
    log_handler = Any
    # The maximum allowed messages in self._paused_buffer.
    buff_size = Trait(DEFAULT_BUFFER_SIZE, None, Int)

    # The maximum allowed length of each message.
    max_len = Trait(DEFAULT_MAX_MESSAGE_LENGTH, None, Int)

    # The maximum allowed messages in self.log
    max_view_len = Trait(DEFAULT_VIEW_SIZE, None, Int)

    # String that holds text written.
    buffer = Instance(deque)
    paused = Bool(False)
    scroll = Bool(False)
    reading = Bool(False)

    def _buffer_default(self):
        return deque(maxlen=self.buff_size)

    def _buff_size_changed(self,new):
        self.buffer = deque(self.buffer, maxlen=new)

    def _paused_changed(self):
        if self.paused:
            # Copy the current_samp text to _paused_buffer.  While the OutputStream
            # is paused, the write() method will append its argument to _paused_buffer.
            #self._paused_buffer.clear()
            #self._paused_buffer.extend(self.text)
            pass
        else:
            # No longer paused, so copy the _paused_buffer to the displayed text, and
            # reset _paused_buffer.

            pass
            #self._paused_buffer.clear()

    def config_logger(self,name=None,level='INFO',fmt=None):
        logger = logging.getLogger(name)
        if self.log_handler is None:
            self.log_handler = logging.StreamHandler(stream=self)
        if fmt is None:
            formatter = logging.Formatter('[%(levelname)s] (%(threadName)-10s) : %(message)s')
        else:
            formatter = logging.Formatter(fmt=fmt)
        self.log_handler.setFormatter(formatter)
        self.log_handler.setLevel(getattr(logging,level))
        logger.addHandler(self.log_handler)
        logger.setLevel(getattr(logging,level))

    def read_buffer(self):
        while self.buffer:
            self.log.append(self.buffer.popleft())
            if len(self.log) > self.max_view_len:
                self.log = self.log[-self.max_view_len:]

            self.scroll = not self.scroll
            sleep(0.001)
        self.reading = False

    def write(self, s):
        if ':' in s:
            first, rest = s.split(':', 1)
        else:
            first = 'Message'
            rest = s
        lines = [first + ':'] + textwrap.wrap(rest, self.max_len, break_long_words=True)

        self.buffer.extend(lines)
        if not self.reading:
            self.reading = True
            t = Thread(target=self.read_buffer)
            t.setDaemon(True)
            t.start()



    def flush(self):
        GUI.process_events()
        #self.scroll = not self.scroll

    def close(self):
        pass

    def reset(self):
        self.buffer.clear()
        self.paused = False
        self.log = []

    def traits_view(self):
        view = \
            View(
                UItem('log', editor=log_editor(),),

                handler = _LogStreamHandler(),
                height=650,
                width=500,
            resizable=True,
            scrollable = True)
        return view

if __name__ == '__main__':
    import logging
    import numpy as np
    from threading import Thread

    def log_printer(stream):
        logger = logging.getLogger(__name__)
        sleep(2)
        for i in range(20):
            #print(' printed message %d'%i, file=stream)
            logger.info('info message number %d' %i+str(np.random.random(np.random.randint(1,10,1))))
            logger.debug('debug message number %d' %i)
            sleep(np.random.random())

    logger = logging.getLogger(__name__)
    log_stream = LogStream()
    log_handler = logging.StreamHandler(stream=log_stream)
    formatter = logging.Formatter('[%(levelname)s] (%(threadName)-10s) : %(message)s')
    log_handler.setFormatter(formatter)
    log_handler.setLevel(logging.DEBUG)

    logger.addHandler(log_handler)
    logger.setLevel(logging.DEBUG)


    for n in range(2):
        t = Thread(name='Worker %d'%n , target=log_printer,args=(log_stream,))
        t.setDaemon(True)
        t.start()
        #sleep(0.02)

    log_stream.configure_traits()