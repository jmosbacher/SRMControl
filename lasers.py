from traits.api import *


class BaseLaser(HasTraits):
    class_name = 'BaseLaser'
    name = Str
    on_chan_name = Str
    power_chan_name = Str


class ModulatedLaser(BaseLaser):
    class_name = 'ModulatedLaser'


class CWLaser(BaseLaser):
    class_name = 'CWLaser'


class PulsedLaser(BaseLaser):
    class_name = 'PulsedLaser'

