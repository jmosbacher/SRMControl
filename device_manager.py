from traits.api import List #Class
from traitsui.api import View, Group, VGroup, HGroup, Item, SetEditor
from managers import BaseManager
from devices import BaseDevice, device_dict

class DeviceManager(BaseManager):
    name = 'Devices'

    available = List()
    included = List()
    devices = List(BaseDevice)
    view = View(
            VGroup(
                Item(name='included', editor=SetEditor(name='available',
                                                       left_column_title='Available',
                                                       right_column_title='System',),
                      show_label=False),

            ),
    )

    def _included_changed(self):
        self.devices = [dev() for dev in self.included]

    def _available_default(self):
        return [dev for dev in device_dict.values()]

    def _included_default(self):
        return [dev for dev in device_dict.values()]

    def _devices_default(self):
        return [dev() for dev in device_dict.values()]

