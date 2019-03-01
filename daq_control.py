from __future__ import print_function
#from collections import deque
#from devices import NIDAQ
from auxilary_functions import length_of
import numpy as np
#from devices import NIDAQ
import os
import cfg
GLOBALS = cfg.Globals()
if GLOBALS.MOCK_DAQ:
    import mock_nidaqmx as nidaqmx
else:
    import nidaqmx
#from device_manager import DeviceManager
from nidaqmx.constants import *
from traits.api import *
from traitsui.api import *
from traitsui.extras.checkbox_column import CheckboxColumn
from constants import IOService
from itertools import product
from time import sleep

class BaseDAQControl(HasTraits):
    _task = Instance(nidaqmx.Task, transient=True)

class BaseDAQChannel(BaseDAQControl):
    _kind = 'BaseDAQChannel'
    name = Property()
    user_name = Str('')
    phys_name = Str('')

    provides = Set(set())
    requires = Set({IOService.DAQ})
    nsamp = Int(100)
    shape = Property()

    channel_type = Str('')

    timeout = Float(10.0)
    daq = Instance(HasTraits, transient=True)

    available_channels = Property(List)


    def __repr__(self):
        #return self.name
        return '{} on {}'.format(self._kind, self.phys_name)

    def __str__(self):
        return self.name
        #return '{} on {}'.format(self._kind, self.phys_name)

    def _get_available_channels(self):
        raise NotImplementedError

    def _daq_default(self):
        from devices import NIDAQ
        return NIDAQ()

    @property_depends_on('nsamp')
    def _get_shape(self):
        return (self.nsamp,)

    @property_depends_on('user_name, phys_name, _kind')
    def _get_name(self):
        if self.user_name:
            return self.user_name
        elif self.phys_name:
            return self.phys_name
        else:
            return self._kind

    def add_to_task(self):
        raise NotImplemented


class BaseDAQReadChannel(BaseDAQChannel):
    provides = {IOService.DAQ_READ}
    reader = Any(transient=True)

    def read_data(self):
        if self.reader:
            data = self.reader.read_data()
            return data.pop(self.phys_name, np.array([np.nan]))
        else:
            from global_state_manager import GlobalStateManager
            gsm = GlobalStateManager()
            self.reader = gsm.active_state
            data = self.reader.read_data()
            return data.pop(self.phys_name, np.array([np.nan]))
            


class BaseDAQWriteChannel(BaseDAQChannel):
    provides = {IOService.DAQ_WRITE}
    writer = Any(transient=True)



class MeasureVoltageChannel(BaseDAQReadChannel):
    _kind = 'Measure Voltage'
    name = 'Measure Voltage'
    provides = {IOService.DAQ_READ_VOLTAGE}
    terminal_cfg = Enum(TerminalConfiguration.DEFAULT,[cfg for cfg in TerminalConfiguration])
    units = Enum(VoltageUnits.VOLTS,[unit for unit in VoltageUnits])
    vmin = Float(-10)
    vmax = Float(10)

    view = View(

        VGroup(
            HGroup(Item(name='user_name', label='Name', ),
                   Item(name='phys_name', label='Channel',
                        editor=EnumEditor(name='available_channels'), ),
                   Item(name='terminal_cfg', label='Terminal Configuration', ),
                   Item(name='units', label='Units', ),
                   ),
                   HGroup(
                       Item(name='vmin', label='Vmin', width=-60),
                       Item(name='vmax', label='Vmax', width=-60),
                   ),
                   HGroup(
                       # Item(name='nsamp', label='Samples', width=-60),
                       Item(name='timeout', label='Timeout', width=-60),
                   ),

                ),


    )

    def _get_available_channels(self):
        if hasattr(self,'daq'):
            return self.daq.ai_chan_names
        else:
            return []

    def add_to_task(self):
        #vmin,vmax = self.vrange
        self._task.ai_channels.add_ai_voltage_chan(self.phys_name,
                #name_to_assign_to_channel=u"",
                terminal_config=self.terminal_cfg,
                min_val=self.vmin,max_val=self.vmax,
                units=self.units,
                #custom_scale_name=u""
                                                   )




class OutputVoltageChannel(BaseDAQWriteChannel):
    _kind = 'Output Voltage'
    name = 'Output Voltage'
    provides = {IOService.DAQ_WRITE_VOLTAGE}
    terminal_cfg = Enum(TerminalConfiguration.DEFAULT,[cfg for cfg in TerminalConfiguration])
    units = Enum(VoltageUnits.VOLTS,[unit for unit in VoltageUnits])
    vmin = Float(-10)
    vmax = Float(10)

    view = View(
        VGroup(

            HGroup(Item(name='user_name', label='Name', ),
                   Item(name='phys_name', label='Channel',
                        editor=EnumEditor(name='available_channels'), ),
                   Item(name='terminal_cfg', label='Terminal Configuration',),
                   Item(name='units', label='Units',),
                   ),

                   HGroup(
                       Item(name='vmin', label='Vmin', width=-60),
                       Item(name='vmax', label='Vmax', width=-60),
                   ),
                   HGroup(
                       # Item(name='nsamp', label='Samples', width=-60),
                       Item(name='timeout', label='Timeout', width=-60),
                   ),



              )
                )

    def _get_available_channels(self):
        if hasattr(self, 'daq'):
            return self.daq.ao_chan_names
        else:
            return []

    def add_to_task(self):
        #vmin,vmax = self.vrange

        self._task.ao_channels.add_ao_voltage_chan(self.phys_name,
                name_to_assign_to_channel="",
                terminal_config=self.terminal_cfg,
                min_val=self.vmin,max_val=self.vmax,
                units=self.units,
                custom_scale_name=u"")

    def write_to_stream(self,stream, arr=None):
        if not self.writer:
            from nidaqmx.stream_readers import AnalogSingleChannelWriter
            self.writer = AnalogSingleChannelWriter(stream)

        if arr is None:
            data = np.zeros(self.nsamp, dtype=np.float64)
            nsamp = self.nsamp
        else:
            data = arr
            nsamp = arr.size

        nwrote = self.writer.write_many_sample(data,

            timeout=self.timeout)
        if nwrote==nsamp:
            return data
        else:
            return None

class CountEdgesChannel(BaseDAQReadChannel):
    _kind = 'Count Edges'
    edge = Enum(Edge.RISING, [a for a in Edge])
    count_direction = Enum(CountDirection.COUNT_UP, [a for a in CountDirection])
    initial_val = Int(0)
    provides = {IOService.DAQ_READ_COUNT}
    view = View(
        HGroup(
            Item(name='user_name', label='Name',),
            Item(name='phys_name', label='Channel',
                 editor=EnumEditor(name='available_channels'), ),
            Item(name='initial_val', label='Start at',),
        ),
        HGroup(
            Item(name='edge', label='Edge', style='custom'),
            Item(name='count_direction', label='Direction', ),

        )
    )
    def _get_available_channels(self):
        if hasattr(self, 'daq'):
            return self.daq.ci_chan_names
        else:
            return []

    def add_to_task(self):
        self._task.ci_channels.add_ci_count_edges_chan(self.phys_name,
                            name_to_assign_to_channel=self.user_name,
                            edge=self.edge,
                            initial_count=self.initial_val,
                            count_direction=self.count_direction,)





class MeasureFrequencyChannel(BaseDAQReadChannel):
    _kind = 'Measure Frequency'
    name = 'Measure Frequency'
    provides = {IOService.DAQ_READ_FREQUENCY}
    units = Enum(FrequencyUnits.HZ,[a for a in FrequencyUnits])
    edge = Enum(Edge.RISING,[a for a in Edge])
    meas_method = Enum(CounterFrequencyMethod.LARGE_RANGE_2_COUNTERS,[a for a in CounterFrequencyMethod])
    meas_time = Float(0.001)
    divisor = Int(4)
    minval = Float(100.0)
    maxval = Float(1e6)

    traits_view = View(
        VGroup(
        HGroup(Item(name='user_name', label='Channel'),
            Item(name='phys_name', label='Channel',
                 editor=EnumEditor(name='available_channels'), style='custom'),
            Item(name='meas_method', label='Method', style='custom'),
            ),
            HGroup(
            Item(name='edge', label='Edge', style='custom'),
            Item(name='units', label='Units', style='custom'),
            ),
            HGroup(
            Item(name='meas_time', label='Time', ),
            Item(name='divisor', label='Divisor',),
            ),
            HGroup(
                Item(name='minval', label='Fmin', width=-60),
                Item(name='maxval', label='Fmax', width=-60),
            ),

        columns=2),
    )

    def _get_available_channels(self):
        if hasattr(self, 'daq'):
            return self.daq.ci_chan_names
        else:
            return []

    def add_to_task(self):

        self._task.ci_channels.add_ci_freq_chan(self.phys_name,
                            name_to_assign_to_channel=self.user_name,
                            min_val=self.minval,max_val=self.maxval,
                            units=self.units,
                            edge=self.edge,
                            meas_method=self.meas_method,
                            meas_time=self.meas_time,
                            divisor=self.divisor,
                            custom_scale_name=u''
         )

    def remove_from_task(self):
        pass




class MockChannel(BaseDAQReadChannel):
    provides = {a for a in IOService if 'DAQ_READ' in a.name }
    _kind = Str('Mock Channel')

    name = Str('Mock Channel')
    length = 1
    #recorded_samples = Array()
    #length = Int(10)
    amp = Float(1.0)
    sigma_sqrd = Float(10.0)
    center = Int(3)
    noise_factor = Float(0.01)
    ndim = Int(3)
    steps = Int(100)

    view = View(
        HGroup(
            Item(name='length', label='Samples', width=20),
            Item(name='amp', label='Amplitude', width=20),
            Item(name='center', label='Ceneter', width=20,style='simple'),
            Item(name='sigma_sqrd', label='Sigma^2', width=20),
            Item(name='noise_factor', label='Noise fact.', width=20),
            Item(name='ndim', label='Dimensions', width=20),
        show_border=True,label='ND Gaussian'),

    )


    def initialize(self):
        steps = int(3*np.sqrt(self.sigma_sqrd))
        positions =  [range(steps) for d in range(self.ndim)]
        self.pos = product(*positions)

    def add_to_task(self):
        pass
        #self.initialize()


    def _get_available_channels(self):
        if hasattr(self, 'daq'):
            return self.daq.ci_chan_names+self.daq.ai_chan_names

    def read_data(self):
        sleep(0.03)
        read = self.read_from_stream(None)
        return read[self.phys_name]

    def read_from_stream(self,stream, arr=None):
    #def perform(self, idx=0, nmeas=1):
        #try:
        meas = self.noise_factor*self.amp*np.random.standard_normal(self.shape)
               #self.ndgauss(self.pos.next())
        # if arr:
        #     arr[:] = meas
        #     return True
        # else:
        return {self.phys_name:meas}

        # except StopIteration:
        #     self.initialize()
        #     return self.read_from_stream(stream, arr)

        # except:
        #     return None


    def ndgauss(self,x):
        X = np.asarray(x)
        try:
            X0 = [self.center]*len(X)#[0]*(len(X)-2)+[self.center]*2
        except:
            X0 = self.center
        return self.amp*np.exp(-np.sum( (X-X0)**2/(2*self.sigma_sqrd) ) )

def format_service_set(s):
    return ', '.join([serv.name for serv in s])


class DAQChannelTable(TableEditor):
    columns = [
        #ColoredNumberColumn(name='channel_num', label='#', width=0.1,style='readonly'),
        ObjectColumn(name='user_name', label='Name', width=0.15,),
        ObjectColumn(name='_kind', label='Type', width=0.15,style='readonly'),
        ObjectColumn(name='phys_name',
                     editor=EnumEditor(name='available_channels'), label='Physical channel', width=0.15),
        #ObjectColumn(name='nsamp', label='Samples', width=0.15, ),
        ObjectColumn(name='provides', label='Provides', width=0.55, format_func=format_service_set),
        #ObjectColumn(name='vmax', label='Max. Voltage', width=0.10),
        #ReadonlyCheckboxColumn(name='in_use',label='In Use',editable=False)
        ]
    #auto_size = False

channel_dict = {
    'Output Voltage': OutputVoltageChannel,
    'Measure Voltage': MeasureVoltageChannel,
    'Count Edges': CountEdgesChannel,
    'Measure Frequency': MeasureFrequencyChannel,

    #'Mock Channel': MockChannel,

}


class BaseDAQTask(BaseDAQControl):
    """
    Wrapper with TraitsUI for nidaqmx Task
    """
    name = Str('New Task')
    _task = Instance(nidaqmx.Task, transient=True)
    provides = Property(Set)
    run = Bool(True)
    channel = Instance(BaseDAQChannel)
    channels = List(BaseDAQChannel)
    nchannels = Property(fget=length_of('channels'))
    reader = Any(transient=True)
    #kind_options = List(channel_dict.keys())
    #add_kinds = List([])
    add_channel = Button('Add')
    remove_channel = Button('Remove selected')
    samp_per_chan = Int(100)

    configured = Bool(False)
    running = Bool(False)
    user_wants_stop = Bool(False)
    #mode_name = None
    #mode = Property()

    #min_val = Float(0.0)
    #max_val = Float(10.0)

    #unit_name = None
    unit = Property()

    done_callback = Function()
    every_n_callback = Function()
    timeout = Float(1.0)

    clk = Property(Str)
    clk_source = Enum('Internal',['Internal', 'External'])
    ext_clk_chan = Instance(BaseDAQChannel)
    clk_rate = Float(10000.0)
    clk_edge_name = Enum('Rising', ['Rising', 'Falling'])
    clk_edge = Property()

    sample_mode_name = Enum('FiniteSamps', ['FiniteSamps', 'ContSamps' ])
    sample_mode = Property()


    ext_start_trigger = Bool(False)
    start_trig = Property()
    start_trig_chan = Instance(BaseDAQChannel)
    start_trig_edge_name = Enum('Rising', ['Rising', 'Falling'])
    start_trig_edge = Property()

    daq = Instance(HasTraits, transient=True)
    #details = Property(Str)

    view = View(
        VGroup(
            VGroup(

                #Item(name='samp_per_chan',label='Samples',width=150),

                HGroup(
                    Item(name='add_channel', show_label=False),
                    Item(name='remove_channel', show_label=False),
                ),
                Item(name='channels', editor=DAQChannelTable(selected='channel'),
                     label='Channels', show_label=False, width=100),
                Item(name='channel', editor=InstanceEditor(), style='custom',show_label=False),
                show_border=True, label='Channels'),
        ),
    )

    def __repr__(self):
        return self.name

    def __str__(self):
        return self.name

    def __enter__(self):
        self.configure()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
        self.close()

    def _daq_default(self):
        from devices import NIDAQ
        return NIDAQ()

    def _get_provides(self):
        prov = set()
        for chan in self.channels:
            prov = prov.union(chan.provides)
        return prov

    def _channels_default(self):
        return []


    def _remove_channel_fired(self):
        self.channel._task = None
        self.channels.remove(self.channel)
        self.channel = None

    def configure(self):
        self._task = nidaqmx.Task()
        for chan in self.channels:
            chan._task = self._task
            chan.add_to_task()
        self.configured = True


    def start(self):
        if not self.configured:
            self.configure()
        self._task.start()
        self.running = True

    def stop(self):
        if self.running:
            self._task.stop()
        self.running = False

    def close(self):
        for chan in self.channels:
            chan._task = None
            chan.reader = None
        if self._task:
            self._task.close()
            self._task = None
        self.configured = False



    def verify(self):
        pass

    def commit(self):
        pass


    def write_data(self, arr):
        pass

class VITask(BaseDAQTask):
    name = 'Voltage In'

    def _add_channel_fired(self):
        chan = MeasureVoltageChannel()
        self.channels.append(chan)

    def read_data(self, arr=None):
        if not self.reader:
            from nidaqmx.stream_readers import AnalogMultiChannelReader
            self.reader = AnalogMultiChannelReader(self._task.in_stream)
        #chan_names = stream._task.ai_channels.channel_names
        number_of_channels = len(self.channels)
        nsamp = self.samp_per_chan
        data = np.empty((number_of_channels, nsamp),dtype=np.float64)

        nread = self.reader.read_many_sample(data,
            number_of_samples_per_channel=nsamp,
            timeout=self.timeout)
        data_dict = {}
        for k, chan in enumerate(self.channels):
            #print(chan.phys_name)
            #print(data[k,:])
            data_dict[chan.phys_name] = data[k,:]
        return data_dict


class FrequencyTask(BaseDAQTask):
    name = 'Frequency In'

    def _add_channel_fired(self):
        chan = MeasureFrequencyChannel()
        self.channels.append(chan)

    def read_data(self, arr=None):
        if self.reader is None:
            from nidaqmx.stream_readers import CounterReader
            self.reader = CounterReader(self._task.in_stream)

        #number_of_channels = len(self.channels)
        nsamp = self.samp_per_chan
        if arr is None:
            data = np.empty((nsamp,), dtype=np.float64)
        else:
            data = arr
        dcycles = np.empty((nsamp,), dtype=np.float64)

        nread = self.reader.read_many_sample_double(data,
                    number_of_samples_per_channel=nsamp, timeout=self.timeout)
        nread = self.reader.read_many_sample_pulse_frequency(data,dcycles,
                                                    number_of_samples_per_channel=nsamp, timeout=self.timeout)

        if nread != nsamp:
            return {}
        return {self.channels[0].phys_name:data}



class MockDAQTask(BaseDAQTask):
    name = Str('Mock Task')

    def _channels_default(self):

        return [MockChannel()]

    def configure(self):
        self.configured = True

    def start(self):
        if not self.configured:
            self.configure()
        self.running = True

    def stop(self):
        self.running = False

    # def read_data(self, arr_dict=None, names=None):
    #     if arr_dict is None:
    #         data = {}
    #     for channel in self.channels:
    #         if channel.phys_name in data.keys():
    #             n = data[channel.phys_name].size
    #         else:
    #             n=1
    #         if 'ci' in channel.phys_name:
    #             data[channel.phys_name] = np.random.randint(1,1000,size=n)
    #         elif 'ai' in channel.phys_name:
    #             data[channel.phys_name] = np.random.random(n)
    #         elif 'di' in channel.phys_name:
    #             data[channel.phys_name] = np.random.choice([True, False],size=n)
    #     return data

    def write_data(self,arr, names=None):
        return arr

    def _add_channel_fired(self):
        self.channels.append(MockChannel())

from auxilary_functions import format_truth
from readonly_checkbox_column import ReadOnlyCheckboxColumn
class DAQTaskTable(TableEditor):
    columns = [
        #CheckboxColumn(name='run', label='Run', editable=False)
        ObjectColumn(name='name', label='Name', width=0.2),
        ObjectColumn(name='nchannels', label='Channels', width=0.10,style='readonly'),
        ObjectColumn(name='samp_per_chan', label='Samples', width=0.20),
        #ObjectColumn(name='configured', label='Configured', width=0.05, style='readonly',),
        ReadOnlyCheckboxColumn(name='configured', label='Configured', width=0.05,
                               style='readonly', horizontal_alignment='center'),
        ReadOnlyCheckboxColumn(name='running', label='Running', width=0.05,
                               horizontal_alignment='center',style='readonly',),
        #ObjectColumn(name='running', label='Running', width=0.05, style='readonly', format_func=format_truth),


        ]


task_dictionary = {
    'Voltage In Task': VITask,
    'Frequency In Task': FrequencyTask,

    'Mock DAQ Task': MockDAQTask,
}
# class ColoredNumberColumn(ObjectColumn):
#     editable = False
#
#     def is_editable( self, object ):
#         return False
#     def get_width( self ):
#         return 40
#
#     def get_cell_color( self, object ):
#         if object.in_use:
#             return '#7FFFD4'
#         else:
#             return 255,255,255

if __name__=='__main__':
    pass
