from traits.api import *
from traitsui.api import *
from devices import BaseDevice
from manual_controls import  BaseManualControl
from experiment_manager import ExperimentManager
from managers import BaseManager
import cfg


class BaseMicroscope(HasTraits):
    class_name = 'BaseMicroscope'

class SuperResolutionMicroscope(BaseMicroscope):
    class_name = 'SuperResolutionMicroscope'
    name = 'Microscope'
    managers = List(BaseManager)
    GLOBALS = Instance(cfg.Globals,())

    traits_view = View(
        Item(name='GLOBALS', style='custom', show_label=False),
    )

    tabbed_view = View(
            Item(name='managers', show_label=False,style='custom',
                 editor=ListEditor(use_notebook=True, page_name='.name') ),

    )
    def _managers_default(self):
        c = []
        try:
            from experiment_manager import ExperimentManager
            c.append(ExperimentManager())
        except:
            pass
        try:
            from device_manager import DeviceManager
            c.append(DeviceManager())
        except:
            pass
        try:
            from control_manager import ControlManager
            c.append(ControlManager())
        except:
            pass
        try:
            from global_state_manager import GlobalStateManager
            c.append(GlobalStateManager())
        except:
            pass

        return c



microscope_dict = {
    'SuperResolutionMicroscope': SuperResolutionMicroscope,

}
