from traits.api import *
from traitsui.api import *
from managers import BaseManager
from experiments import BaseExperiment, ExperimentTableEditor,\
    ExperimentStatus, experiment_dict
from time import sleep
from threading import Thread


class ExperimentManagerHandler(Handler):
    def close( self, info, is_ok ):
        info.object.closing = True
        for exp in info.object.experiments:
            exp.status = ExperimentStatus.CANCELED
        info.object.thread.join(timeout=1)
        super(ExperimentManagerHandler, self).close(info, is_ok)

class ExperimentManager(BaseManager):

    experiments = List(BaseExperiment,[])
    experiment = Instance(BaseExperiment)

    thread = Any(transient=True)
    closing = Bool(False, transient=True)

    add_type = Enum(experiment_dict.keys())
    add = Button('Add')
    remove = Button('Remove')
    run = Button('Run')
    pause = Button('Pause')
    stop = Button('Stop')

    view = View(
         VGroup(
             HGroup(Item(name='run', show_label=False, enabled_when='experiment and experiment.status != 1'),
                    Item(name='pause', show_label=False, enabled_when='experiment.status == 1'),
                    Item(name='stop', show_label=False, enabled_when='experiment.status != 0'),
                    label='Control', show_border=True),
             HGroup(Item(name='add_type', show_label=False, ),
                    Item(name='add', show_label=False, ),
                    Item(name='remove', show_label=False, ),
             ),
             Group(Item(name='experiments', show_label=False,
                        editor=ExperimentTableEditor(selected='experiment')),
                   show_border=True, label='Experiments'),


             Group( Item(name='experiment', style='custom',
                          editor=InstanceEditor(view='summary_view'), show_label=False,),
                     label='Experiment Summary', show_border=True),


         ),
        handler=ExperimentManagerHandler,

     )

    def __init__(self,*args, **kwargs):
        super(ExperimentManager,self).__init__(*args, **kwargs)

        self.thread = Thread(target=self.experiment_runner)
        self.thread.setDaemon(True)
        self.thread.start()

    def _add_fired(self):
        if self.experiments:
            self.experiments.append(experiment_dict[self.add_type]())
        else:
            self.experiments = [experiment_dict[self.add_type]()]

    def _remove_fired(self):
        if self.experiment:
            self.experiments.remove(self.experiment)

    def _experiments_default(self):
        return [exp() for exp in experiment_dict.values()]

    def _run_fired(self):
        if self.experiment:
            self.experiment._start()

    def _pause_fired(self):
        if self.experiment:
            self.experiment._pause()

    def _stop_fired(self):
        if self.experiment:
            self.experiment._stop()

    def experiment_runner(self):
        while True:
            for exp in self.experiments:
                if exp.status == ExperimentStatus.QUEUED:
                    exp.exp_worker()
                sleep(0.2)
                if self.closing:
                    return
