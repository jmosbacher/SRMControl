from PyDAQmx import Task
import numpy as np
import PyDAQmx
import matplotlib.pyplot as plt
ext_start_trigger = False

task = Task()

"""
task.CreateAIVoltageChan("Dev2/ai0", "",PyDAQmx.DAQmx_Val_RSE , -10.0, 10.0, PyDAQmx.DAQmx_Val_Volts, None)
task.CfgSampClkTiming("", 10000, PyDAQmx.DAQmx_Val_Rising, PyDAQmx.DAQmx_Val_FiniteSamps, 1000)

if ext_start_trigger:
    task.DAQmxCfgDigEdgeStartTrig("chan",  PyDAQmx.DAQmx_Val_Rising)
else:
    pass
    #task.DAQmxDisableStartTrig()
#task.AutoRegisterEveryNSamplesEvent(PyDAQmx.DAQmx_Val_Acquired_Into_Buffer, self.nsamples, 0)
#task.AutoRegisterDoneEvent(0)


data = np.zeros(1000)
read = PyDAQmx.int32()

PyDAQmx.DAQmxWaitUntilTaskDone(task.taskHandle,PyDAQmx.float64(10.0))
task.ReadAnalogF64(1000, 10.0, PyDAQmx.DAQmx_Val_GroupByChannel,
                       data, 1000, PyDAQmx.byref(read), None)
print read
plt.plot(data)
plt.show()
"""

task.CreateCIFreqChan("Dev2/ctr1", "", 10.0, 100.0,PyDAQmx.DAQmx_Val_Hz,PyDAQmx.DAQmx_Val_Rising, PyDAQmx.DAQmx_Val_LowFreq1Ctr,
                          0.01,40, None)
task.CfgImplicitTiming(PyDAQmx.DAQmx_Val_FiniteSamps, 10)
task.StartTask()
data = np.zeros(100)
read = PyDAQmx.int32()

PyDAQmx.DAQmxWaitUntilTaskDone(task.taskHandle,PyDAQmx.float64(10.0))

task.ReadCounterF64(100, 10.0,data,100, PyDAQmx.byref(read), None)
print read
print np.mean(data)

#int32 DAQmxReadCounterF64 (TaskHandle taskHandle, int32 numSampsPerChan, float64 timeout, float64 readArray[], uInt32 arraySizeInSamps, int32 *sampsPerChanRead, bool32 *reserved);
"""

	DAQmxErrChk(DAQmxCreateTask("DAQTaskInProject3", &taskOut));

	DAQmxErrChk(DAQmxCreateCICountEdgesChan(taskOut, "Dev2/ctr1",
		"CountEdges", DAQmx_Val_Rising, 0, DAQmx_Val_CountUp));

	DAQmxErrChk(DAQmxCfgSampClkTiming(taskOut, "PFI0",
		1000, DAQmx_Val_Rising,
		DAQmx_Val_FiniteSamps, 100));

"""