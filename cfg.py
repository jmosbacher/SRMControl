from com_ports import serial_ports
from traits.api import SingletonHasTraits,Bool, Str, Int, List, Directory, File, Button
from traitsui.api import View, Item, Group, HGroup, VGroup, ListStrEditor, spring, CheckListEditor
import os
local_dir = os.path.dirname(os.path.realpath(__file__))

class Globals(SingletonHasTraits):
    DIRTY = Bool(False)
    MOCK_DAQ = Bool(False)
    MOCK_STAGE = Bool(False)
    DEBUG = Bool(False)


    FILE_DIR = Directory(local_dir)
    ICON_DIR = Directory(os.path.join(local_dir, 'icons'))
    AUTOSAVE_PATH = File(os.path.join(local_dir, 'autosave.cfg'))

    AUTOLOAD_PATH = File(os.path.join(local_dir, 'autosave.cfg'))
    AUTOLOAD_ONSTART = Bool(False)
    TEMPDIR = Directory(local_dir)

    MAX_SIZE = Int(2000)
    STAGE_AXES = List([1,2,3])
    STAGE_DEFAULT_AXIS = Int(1)
    STAGE_DEFAULT = 'Micronix'
    AVAIL_PORTS = List([])
    COM_PORTS = List([])
    DEVICE_NUMBERS = List([0,1,2])
    DAQ_DEFAULT_DEVICE_NUMBER = Int(2)
    DAQ_DEFAULT_COM = Str('COM4')
    STAGE_DEFAULT_COM = Str('COM5')
    STATUS = Str('IDLE')


    scan_ports = Button('Scan')

    view = View(
        VGroup(
            HGroup(
                Item(name='AUTOLOAD_ONSTART',label='Autololad on startup'),
                Item(name='AUTOLOAD_PATH', label='Path'),
            show_border=True, label='Autoload'),
            HGroup(

                Item(name='AUTOSAVE_PATH', label='Autosave Path'),
                show_border=True, label='Autosave'),
            VGroup(

                Item(name='MAX_SIZE', label='Max buffer size (MB per measurement)'),
                Item(name='TEMPDIR', label='Temp files path'),
                show_border=True, label='Measurement Buffer'),

            HGroup(

                Item(name='DIRTY', label='Dirty'),
                #Item(name='MOCK_DAQ', label='Mock DAQ'),
                #Item(name='MOCK_STAGE', label='Mock Stage'),
                Item(name='DEBUG', label='Debug'),
                show_left=False, show_border=True, label='Debugging'),


                HGroup(
                    Item(name='scan_ports', show_label=False, width=15),
                    Item(name='COM_PORTS', editor=CheckListEditor(name='AVAIL_PORTS'),
                         enabled_when='False',show_label=False, style='custom'),
                label='COM ports',show_border=True),

        label='Global settings'),


    )

    def _AVAIL_PORTS_default(self):
        ports = serial_ports()
        #if not ports:
            #ports = ['COM1']
        return ports

    def _COM_PORTS_default(self):
        ports = serial_ports()
        #if not ports:
            #ports = ['COM1']
        return ports

    def _scan_ports_fired(self):
        self.AVAIL_PORTS = serial_ports()