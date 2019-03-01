from traits.api import *
from traitsui.api import *
import cfg
try:
    import PyDAQmx
except:
    pass
import os
from daq_control import BaseDAQTask, MockDAQTask, DAQTaskTable
from devices import NIDAQ, BaseDevice
from device_manager import DeviceManager
from cameras import BaseCamera, camera_dict
import cfg
GLOBALS = cfg.Globals()
from constants import IOService
from itertools import product

# Why am I important?
class BaseGlobalState(HasTraits):
    name = Str('Base Global State')
    device_manager = Instance(DeviceManager,())
    active = Bool(False)
    initialized = Bool(False)
    requires = Set()
    provides = Property(List)
    sources = Property(List)


    def _get_provides(self):
        raise NotImplemented

    #def _get_requires(self):
        #raise NotImplemented

    def _get_sources(self):
        raise NotImplemented

    def activate(self):
        raise NotImplemented

    def deactivate(self):
        raise NotImplemented

    def initialize(self):
        raise NotImplemented

    def __repr__(self):
        return self.name

    def __str__(self):
        return self.name


class BaseDAQState(BaseGlobalState):
    name = 'DAQ State'
    daq = Instance(NIDAQ, transient=True)
    avail_tasks = Property(List)
    sel_task = Instance(BaseDAQTask)

    tasks = List(BaseDAQTask)
    task = Instance(BaseDAQTask)

    add_task = Button('Add')
    rem_task = Button('Remove selected')

    requires = {IOService.DAQ}
    channels = Property(List)

    traits_view = View(
        VGroup(
            HGroup(
                Item(name='sel_task', show_label=True,
                     editor=EnumEditor(name='avail_tasks'), style='custom'),
                Item(name='add_task', show_label=False),
                Item(name='rem_task', show_label=False),
            ),

            Item(name='tasks', show_label=False,
                 editor=DAQTaskTable(selected='task'), style='custom', width=-0.5),

            Item(name='task', show_label=True, style='custom',
                 editor=InstanceEditor()),
            label='Tasks', show_border=True),

        scrollable=True,
        resizable=True)

    def _get_provides(self):
        return self.task.provides

    def _daq_default(self):
        return NIDAQ()

    def _get_sources(self):
        srcs = []
        if self.tasks:
            for task in self.tasks:
                srcs.extend(task.channels)
        return srcs

    def _get_avail_tasks(self):
        tasks = []
        if self.daq:
            for task in self.daq.tasks:
                if IOService.services_all(self.requires, task.provides):
                    tasks.append(task)
        return tasks

    def _tasks_default(self):
        tasks = []
        if self.daq:
            for task in self.daq.tasks:
                if IOService.services_all(self.requires, task.provides):
                    tasks.append(task)
        return tasks

    def _add_task_fired(self):
        if IOService.services_all(self.requires, self.sel_task.provides):
            self.tasks.append(self.sel_task)

    def _rem_task_fired(self):
        if self.task in self.tasks:
            self.tasks.remove(self.task)

    def activate(self):
        if self.initialized and self.tasks:
            self.active = True
            # for task in self.tasks:
            #     task.start()
        else:
            if self.initialize():
                self.activate()

    def deactivate(self):
        if self.active and self.tasks:
            for task in self.tasks:
                task.stop()
                task.close()
        self.active = False

    def initialize(self):
        if self.tasks:
            self.initialized = True
            return True
        else:
            return False

class DAQRead(BaseDAQState):
    name = 'DAQ Read'
    requires = {IOService.DAQ_READ}
    data = Dict({})

    def read_data(self, names=None):
        data_dict = {}
        for task in self.tasks:
            task.start()
            data = task.read_data()
            task.stop()
            for key, val in data.items():
                data_dict[key] = val
        self.data = data_dict
        return data_dict


class DAQWrite(BaseDAQState):
    name = 'DAQ Write'
    requires = {IOService.DAQ_WRITE}

    def write_data(self, data, names=None):
        for src in self.sources:
            src.write_data(data)


class CameraRead(BaseGlobalState):
    name = 'Camera Read'
    requires = {IOService.CAM_READ}
    cameras = List(BaseDevice)
    camera = Instance(BaseDevice)
    add = Button('Add')
    avail_cameras = Property(List)

    view = View(
        HGroup(Item(name='camera',editor=EnumEditor(name='avail_cameras',cols=4), style='custom',show_label=False,),
               Item(name='add', show_label=False,), spring),
        Item(name='cameras', style='custom', show_label=False,
             editor=ListEditor(use_notebook=True, page_name='.name'),
             ),
    )

    def _cameras_default(self):
        return []

    def _get_avail_cameras(self):
        cams = []
        for dev in self.device_manager.devices:
            if IOService.services_all(self.requires, dev.provides):
                cams.append(dev)
        return cams

    def _add_fired(self):
        self.cameras.append(self.camera)

    def _get_sources(self):
        return self.cameras

    def activate(self):
        if self.initialized:
            self.active = True
            for cam in self.cameras:
                cam.start()
        else:
            self.initialize()
            self.activate()


    def deactivate(self):
        if self.active:
            for cam in self.cameras:
                cam.stop()
        self.active = False

    def initialize(self):
        for cam in self.cameras:
            cam.initialize()
        self.initialized = True

    def read_data(self, names=None):
        data = {}
        for cam in self.cameras:
            data[cam.name] = cam.read_data()
        return data


class MockDAQRead(DAQRead):
    name = 'Mock DAQ Read'
    view = View()
    task = Instance(MockDAQTask)
    requires = {IOService.DAQ_READ}



    def activate(self):
        pass
        self.active = True

    def deactivate(self):
        pass
        self.active = False

    def read_data(self, names=None):
        data = {}
        for src in self.sources:
            data[src.name] = src.read_data()
        return data

global_states_dict = {
    'DAQ Read': DAQRead,
    'DAQ Write': DAQWrite,
    'Camera Read': CameraRead,
    'Mock DAQ Read':  MockDAQRead,


}

class MultiState(BaseGlobalState):
    name = Str('Multi State')
    add_kind = Enum(global_states_dict.keys())
    add = Button('Add')
    remove = Button('Remove')
    provides = Property()
    states = List(BaseGlobalState)
    state = Instance(BaseGlobalState)


    traits_view = View(
        VGroup(
            HGroup(
                Item(name='add_kind', show_label=False,),
                Item(name='add', show_label=False,),
                Item(name='remove', show_label=False, )

            ),
        ),
        Item(name='states', show_label=False, style='custom',
             editor=ListEditor(use_notebook=True, page_name='.name', selected='state' ))
    )

    @property_depends_on('states[]')
    def _get_provides(self):
        prov = set()
        for state in self.states:
            prov.update(state.provides)
        return prov

    @property_depends_on('states[]')
    def _get_sources(self):
        srcs = []
        for state in self.states:
            srcs.extend(state.sources)
        return srcs


    def _add_fired(self):
        new = global_states_dict[self.add_kind]()
        self.states.append(new)

    def _remove_fired(self):
        if self.state:
            self.states.remove(self.state)
        if self.states:
            self.state = self.states[-1]
        else:
            self.state = None

    def activate(self):
        for state in self.states:
            state.activate()
        self.active = True

    def deactivate(self):
        for state in self.states:
            state.deactivate()
        self.active = False

    def read_data(self, names=None):
        data = {}
        for state in self.states:
            data.update(state.read_data(names))
        return data

global_states_dict['Multiple'] = MultiState
