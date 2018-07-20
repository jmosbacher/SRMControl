from traits.api import List
from traitsui.api import View
from managers import BaseManager
from manual_controls import BaseManualControl,manual_controls_dict


class ControlManager(BaseManager):
    name = 'Manual Controls'
    controls = List(BaseManualControl)

    view = View()

    def _controls_default(self):
        return [cntrl() for cntrl in manual_controls_dict.values()]