#from traitsui.api import *
from traits.api import SingletonHasTraits, Str


class BaseManager(SingletonHasTraits):
    name = Str('Manager')


