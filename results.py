from traits.api import *
from traitsui.api import *

class BaseResult(HasTraits):
    class_name = 'BaseResult'

class MeasurementResult(BaseResult):
    class_name = 'MeasurementResult'

class ExperimentResult(BaseResult):
    class_name = 'ExperimentResult'
    positions = Dict({})
    measurement_results = List(MeasurementResult)

