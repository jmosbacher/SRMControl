from traits.api import *
from traitsui.api import *
import os
import cfg
from devices import BaseDevice
from experiments import BaseExperiment
from manual_controls import BaseManualControl
from global_states import BaseGlobalState
from saving import CanSaveMixin, SaveHandler
from microscopes import SuperResolutionMicroscope, BaseMicroscope
#from experiments import BaseExperiment
from experiment_manager import ExperimentManager
from device_manager import DeviceManager
from control_manager import ControlManager
from global_state_manager import GlobalStateManager
from log_viewer import LogStream
from traitsui.qt4.tree_editor \
    import NewAction, CopyAction, CutAction, \
           PasteAction, DeleteAction, RenameAction
try:
    import cPickle as pickle
except:
    import pickle
from pyface.api import ImageResource
import cfg
import random
import logging
GLOBALS = cfg.Globals()


class MainApp(CanSaveMixin):
    microscope = Instance(BaseMicroscope)

    selected = Instance(HasTraits,transient=True)
    log = Instance(LogStream,transient=True)
    status_str = Str(GLOBALS.STATUS,transient=True)
    save_load_message = Str('')
    dirty = Property()
    #dirty = Constant(cfg.status.dirty,transient=True)

    save_action = Action(name='Save', action='save')
    toggle_autosave = Action(name='Autosave', action='toggle_autosave',style='toggle', checked_when='handler.autosave',  )
    save_as_action = Action(name='Save as', action='saveAs')
    load_action = Action(name='Load file', action='load')



    traits_view = View(

            HSplit(
                VSplit(
                Item(name='microscope', show_label=False,editor=TreeEditor(

                nodes=[
                    TreeNode(node_for=[SuperResolutionMicroscope],
                             auto_open=True,
                             children='',
                             label='',
                             # add=[Project],
                             menu = Menu(RenameAction,)

                             ),

                    TreeNode(node_for=[SuperResolutionMicroscope],
                             auto_open=True,
                             children='managers',
                             label='name',
                             icon_group='microscope100.png',
                             icon_open='microscope100.png',
                             icon_path=GLOBALS.ICON_DIR,
                             # add=[Project],
                             menu=Menu(RenameAction,)
                             ),

                    TreeNode(node_for=[ExperimentManager],
                             auto_open=True,
                             children='experiments',
                             icon_group='experiments.png',
                             icon_open='experiments.png',
                             icon_path=GLOBALS.ICON_DIR,
                             label='=Experiment Manager',
                             # add=[Project],
                             menu=Menu(RenameAction, )

                             ),

                    TreeNode(node_for=[BaseExperiment],
                             auto_open=True,
                             children='',
                             label='name',
                             icon_item='graph_node.png',
                             icon_path=GLOBALS.ICON_DIR,
                             # add=[Project],
                             menu=Menu(RenameAction, )

                             ),
                    TreeNode(node_for=[ControlManager],
                             auto_open=True,
                             children='controls',
                             label='name',
                             icon_group='controls.png',
                             icon_open='controls.png',

                             add=[],
                             menu=Menu(RenameAction,)
                             ),
                    TreeNode(node_for=[BaseManualControl],
                             auto_open=True,
                             children='',
                             label='name',
                             icon_item='graph_node.png',
                             icon_path=GLOBALS.ICON_DIR,
                             # add=[Project],
                             menu=Menu(RenameAction,)
                             ),

                    TreeNode(node_for=[DeviceManager],
                             auto_open=True,
                             children='devices',
                             label='name',
                             icon_open='devices.png',
                             icon_group='devices.png',
                             icon_path=GLOBALS.ICON_DIR,
                             # add=[Project],
                             menu=Menu(RenameAction,)
                             ),

                    TreeNode(node_for=[BaseDevice],
                             auto_open=True,
                             children='',
                             label='name',
                             icon_item='graph_node.png',
                             icon_path=GLOBALS.ICON_DIR,
                             # add=[Project],
                             menu=Menu(RenameAction,)
                             ),
                    TreeNode(node_for=[GlobalStateManager],
                             auto_open=True,
                             children='global_states',
                             label='name',
                             icon_open='global.png',
                             icon_group='global.png',
                             icon_path=GLOBALS.ICON_DIR,
                             # add=[Project],
                             menu=Menu(RenameAction, )
                             ),

                    TreeNode(node_for=[BaseGlobalState],
                             auto_open=True,
                             children='',
                             label='name',
                             icon_item='graph_node.png',
                             icon_path=GLOBALS.ICON_DIR,
                             # add=[Project],
                             menu=Menu(RenameAction, )
                             ),
                ],
                hide_root=True,
                editable=False,
                selected='selected')
                 , height=0.7),

                    Item(name='log', show_label=False, style='custom', height=0.3),
                ),


            Item(name='selected', show_label=False,editor=InstanceEditor(),
                 style='custom',width=0.85),
            ),
        width=1200,
        height=700,
        icon=ImageResource(os.path.join(GLOBALS.ICON_DIR,'microscope100.png')),
        resizable=True,
        title='Super Resolution Microscope',
        handler = SaveHandler,
        menubar=MenuBar(
            Menu(save_action, save_as_action, load_action, toggle_autosave,
                 name='File'),
            # Menu(exp_int_tool, comp_tool, comp_int_tool, plot_tool, fit_tool,
            # name='Tools'),
        ),
        statusbar=[StatusItem(name='save_load_message', width=0.5),
                   StatusItem(name='blank', width=0.35),
                   #StatusItem(name='label', width=0.05),
                   StatusItem(name='status_str', width=0.15),
                   ],
    )
    blank = Str('  ')
    label = Str('Status: ')

    def _get_dirty(self):
        return GLOBALS.DIRTY

    def _set_dirty(self, val):
        GLOBALS.DIRTY = val

    def _microscope_default(self):
        return SuperResolutionMicroscope()

    def _log_default(self):
        log = LogStream()
        log.config_logger(__name__)
        return log

    def validate(self):
        #if os.path.isfile(self.filepath):
            #return True, ''
        #else:
            #return False, 'No such file {}'.format(self.filepath)
        return True, ''

    def save(self):
        self.dirty = True
        self.save_load_message = 'Saving to {}...'.format(self.filepath)
        with open(self.filepath,'wb') as f:
            pickle.dump(self.microscope,f)
            self.dirty = False
            self.save_load_message = 'File saved successfully.'
        if self.dirty:
            self.save_load_message = 'Could not save file.'

    def load(self):
        self.dirty = True
        self.save_load_message = 'Loading from {}...'.format(self.filepath)
        with open(self.filepath,'rb') as f:
            self.microscope = pickle.load(f)
            self.dirty = False
            self.save_load_message = 'Successfully loaded file.'
        if self.dirty:
            self.save_load_message = 'Could not load file.'


if __name__ == '__main__':
    app = MainApp()
    app.configure_traits()
