from traits.api import *
from traitsui.api import *
from repeat_button import AutoRepeatButtonEditor
from pyface.api import ImageResource
import os
import time
import cfg
GLOBALS = cfg.Globals()


settings_gr = VGroup(
HGroup(
            Item(name='RL', label='RL',width=-30),
            Item(name='FB', label='FB', width=-30),
            Item(name='UD', label='UD', width=-30),
            ),
            HGroup(
                Item(name='position', show_label=False, enabled_when='False', width=180),
            ),
            HGroup(
                Item(label='Step:'),
                Item(name='step_nm', label='x',width=-45),
                Item(name='step_factor', label='nm', width=-55),
                spring,
            show_left=False),


            )

button_gr = VGroup(
        spring,
        HGroup(
            spring,
            VGroup(
            HGroup(
                Item(name='FL', show_label=False,
                     editor= AutoRepeatButtonEditor(label='', width_padding = 0, height_padding = 0,
                    image=ImageResource(os.path.join(GLOBALS.ICON_DIR,'FL.png'))),
                      width=-40,height=-40),

                spring,
                Item(name='F', show_label=False,
                     editor= AutoRepeatButtonEditor(label='', width_padding = 0, height_padding = 0,
                    image=ImageResource(os.path.join(GLOBALS.ICON_DIR,'F.png'))),
                     width=-40,height=-40),
                spring,
                Item(name='FR', show_label=False,
                     editor= AutoRepeatButtonEditor(label='', width_padding = 0, height_padding = 0,
                    image=ImageResource(os.path.join(GLOBALS.ICON_DIR,'FR.png'))),
                 width=-40,height=-40),
            ),
            spring,
            HGroup(
                Item(name='L', show_label=False,
                     editor= AutoRepeatButtonEditor(label='', width_padding = 0, height_padding = 0,
                    image=ImageResource(os.path.join(GLOBALS.ICON_DIR,'L.png'))),
                     width=-40,height=-40),
                spring,
                HGroup(
                    Item(name='D', show_label=False,
                         editor= AutoRepeatButtonEditor(label='', width_padding = 0, height_padding = 0,
                    image=ImageResource(os.path.join(GLOBALS.ICON_DIR,'D.png'))),
                         width=-30,height=-40),
                    Item(name='U', show_label=False,
                         editor= AutoRepeatButtonEditor(label='', width_padding = 0, height_padding = 0,
                    image=ImageResource(os.path.join(GLOBALS.ICON_DIR,'U.png'))),
                         width=-30,height=-40),
                ),
                spring,
                Item(name='R', show_label=False,
                     editor=AutoRepeatButtonEditor(label='', width_padding=0, height_padding=0,
                                                   image=ImageResource(os.path.join(GLOBALS.ICON_DIR, 'R.png'))),
                     width=-40,height=-40),
            ),
            spring,
            HGroup(
                Item(name='BL', show_label=False,
                     editor=AutoRepeatButtonEditor(label='', width_padding=0, height_padding=0,
                                                   image=ImageResource(os.path.join(GLOBALS.ICON_DIR, 'BL.png'))),
                     width=-40,height=-40),
                spring,
                Item(name='B', show_label=False,
                     editor=AutoRepeatButtonEditor(label='', width_padding=0, height_padding=0,
                                                   image=ImageResource(os.path.join(GLOBALS.ICON_DIR, 'B.png'))),
                     width=-40,height=-40),
                spring,
                Item(name='BR', show_label=False,
                     editor=AutoRepeatButtonEditor(label='', width_padding=0, height_padding=0,
                                                   image=ImageResource(os.path.join(GLOBALS.ICON_DIR, 'BR.png'))),
                     width=-40,height=-40),
            ),
            ),
            spring,



                #Item(name='camera', style='custom', show_label=False),
            ),
        spring,
            )


class XYZNavigator(HasTraits):
    name = Str('Navigator')
    labels = ['RL', 'FB', 'UD']


    controller = Instance(HasTraits, transient=True)
    RL = Enum(1,[1,2,3])
    RL_rev = Bool(False)
    FB = Enum(2,[1,2,3])
    FB_rev = Bool(False)
    UD = Enum(3,[1,2,3])
    UD_rev = Bool(False)
    reverse = List([])
    #xlow = Float(-1e6) #Property(property_depends_on='x_axis')
    #xhigh = Float(1e6)
    position = Tuple((0., 0., 0.), cols=1, labels=labels)  # RL, FB, UD  mm

    pos_mm = Float(0.)
    pos_um = Float(0.)
    pos_nm = Float(0.)
    step_nm = Range(1,10, mode='spinner') #nm
    #step_factor = Range(1,1000)
    step_factor = Enum(10,[1,10,20,50,100,500,1000])
    #camera = Instance(BaseCamera)

    U = Button()
    D = Button()
    F = Button()
    B = Button()
    R = Button()
    L = Button()

    FR = Button()
    FL = Button()
    BR = Button()
    BL = Button()

    #controller = Instance(BaseSerialController)

    button_view = View(

        button_gr,
        #handler = ,
        resizable=False,

    )

    settings_view = View(
        settings_gr,
    resizable=True)
    traits_view = View(
        VGroup(button_gr, settings_gr),
    )
    #def _camera_default(self):
        #return IDSCamera()

    def __init__(self,*args, **kwargs):
        super(XYZNavigator, self).__init__(*args, **kwargs)
        self.mapping = {'U':'UD', 'D':'UD',
                        'R':'RL', 'L':'RL',
                       'F':'FB', 'B':'FB'}
        self.refresh_position()


    def step_mm(self):
        return self.step_nm*(1e-6)

    @on_trait_change('U,D,R,L,F,B,FR,FL,BR, BL')
    def move(self, obj, name, old, new):
        pos = list(self.position)
        for d in name:
            axis = getattr(self,self.mapping[d])
            stp = self.step_mm()*self.step_factor
            if getattr(self,self.mapping[d]+'_rev'):
                stp = -stp
            if d in ['D', 'L','B']:
                stp = -stp
            self.controller.move_rel(axis, stp)
            for i,label in enumerate(self.labels):
                if d in label:
                    pos[i] = round(self.controller.position(axis)[1],6)
        self.position = tuple(pos)

    def refresh_position(self):
        pos = []
        for label in self.labels:
            axis = getattr(self, label)
            p = round(self.controller.position(axis)[1],6)
            pos.append(p)
        self.position = tuple(pos)
