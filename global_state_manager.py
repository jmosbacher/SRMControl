from traits.api import *
from traitsui.api import *

from global_states import BaseGlobalState,global_states_dict
from managers import BaseManager
import cfg
GLOBALS = cfg.Globals()


class GlobalStateManager(BaseManager):
    name = Str('Global States')
    global_states = List(BaseGlobalState)
    global_state = Instance(BaseGlobalState)
    available_state_types = List(global_states_dict.keys())
    active_state = Instance(BaseGlobalState)
    active_sources = Property(List)

    selected_name = Str()
    add = Button('Add')
    remove = Button('Remove')
    activate_selected = Button('Activate')

    traits_view = View(
        VSplit(
            VGroup(

                HGroup(
                    Item(name='selected_name', style='simple',
                         editor=EnumEditor(name='available_state_types'), show_label=False),
                    Item(name='add', show_label=False),
                    Item(name='remove', show_label=False),
                    spring,
                    Item(name='active_state', style='readonly',
                         editor=TextEditor(), label='Active state'),
                ),
                HGroup(
                    Item(name='global_states', show_label=False, width=-0.5,
                         editor=ListStrEditor(selected='global_state'), ),
                    Item(name='global_state', editor=InstanceEditor(),
                    width=-0.5,style='custom', show_label=False),
                ),
            scrollable=True),
    spring,),
        resizable=True,
    )


    select_view = View(
        Item(name='global_state', editor=EnumEditor(name='global_states', cols=5),
              style='custom',show_label=False),
    )

    def __enter__(self):
        self.activate()
        return self.active_state

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.deactivate()
        return True


    def _global_states_default(self):
        #key = global_states_dict.keys()[0]
        return [gs() for gs in global_states_dict.values()]

    @property_depends_on('active_state')
    def _get_active_sources(self):
        srcs = []
        if self.active_state and self.active_state.sources:
            srcs = self.active_state.sources
        return srcs

    def _activate_selected_fired(self):
        self.activate()

    def _add_fired(self):
        new = global_states_dict[self.selected_name]()
        self.global_states.append(new)


    def _remove_fired(self):
        self.global_states.remove(self.global_state)

    def activate(self):
        self.activate_state(self.global_state)

    def activate_state(self, new_state):
        for state in self.global_states:
            if state.active:
                state.deactivate()
        new_state.activate()
        self.active_state = new_state

    def deactivate(self):
        for state in self.global_states:
            if state.active:
                state.deactivate()

