"""

class ManualCameraControlHandler(Handler):
    pass


class ManualCameraControl(BaseManualControl):
    class_name = 'ManualCameraControl'
    name = Str('Camera')

    ### Display ###
    figure = Instance(Figure,transient=True)
    axis = Any
    image = Any(transient=True)

    ### Camera ###
    camera_name = Enum(camera_dict.keys())
    cam = Instance(BaseCamera,transient=True)

    initialized = Bool(False)
    capture_on = Bool(False)
    user_wants_stop = Bool(False)

    message = Str()
    image_buffer = List
    #buffer_size = Int(50)

    save_directory = Directory()
    save_root = Str

    next_im = Button('>')
    prev_im = Button('<')
    im_num = Int(0)
    buffered = Property()
    save_frame = Button('Save Frame')
    frame_fmt = Enum(['jpg','bmp'])
    save_video = Button('Save Video')
    metadata = Dict({})

    nframes = Int(1)
    mode = Enum(['Live','Record'])
    sources = List([0])
    source = Int(0)

    rotation = Enum(0,[0,90,180,270])
    start = Button('Start')
    stop = Button('Stop')
    fps = Range(1,50,10)
    #live = Bool(False)
    animation = Any(transient=True)
    default_image = Array()
    log = Instance(LogStream,transient=True)

    view = View(
        VGroup(
            HGroup(

                Item(name='mode', show_label=False, visible_when='not capture_on'),
                Item(name='start', show_label=False,visible_when='not capture_on'),
                Item(name='stop', show_label=False, visible_when='capture_on'),
                Item(name='nframes', label='Frames', visible_when='mode=="Record"',width=-60),
                spring,
                Item(name='fps', label='FPS',enabled_when='not capture_on',width=-200),
            ),
            HGroup(Item(name='camera_name', show_label=False,),),

            HGroup(Item(name='cam',style='custom', show_label=False,),
                   show_border=True,label='Camera Settings'),

            HGroup(
                Item(name='rotation', label='Rotation',),
                spring,

            ),
            HGroup(spring,
                Item(name='figure',editor=MPLFigureEditor(), style='custom', show_label=False),
            spring),
            HGroup(
                spring,
                Item(name='prev_im', show_label=False, enabled_when='buffered and not capture_on', width=-30),
                Item(name='im_num', show_label=False, enabled_when='buffered and not capture_on', width=-40),
                Item(name='next_im', show_label=False, enabled_when='buffered and not capture_on', width=-30),
                spring,
            ),
        )

    )

    def _get_buffered(self):
        return len(self.image_buffer)!=0

    def _cam_default(self):
        cam = OpenCVCamera()
        initialized = cam.initialize()
        if initialized:
            cam.close()
            return cam
        else:
            return MockCamera()

    def _default_image_default(self):
        img = np.mgrid[0:1:0.002, 0:500:1][0]
        return img

    def _camera_name_changed(self,new):
        self.cam = camera_dict[new]()

    def _figure_default(self):
        fig = Figure()
        fig.patch.set_facecolor('none')
        self.axis = fig.add_subplot(111)
        for spine in ['top','bottom','left','right']:
            self.axis.spines[spine].set_visible(False)
        self.axis.set_position([0, 0, 1, 1])
        labels = [item.get_text() for item in self.axis.get_xticklabels()]
        empty_string_labels = [''] * len(labels)
        self.axis.set_xticklabels(empty_string_labels)
        labels = [item.get_text() for item in self.axis.get_yticklabels()]
        empty_string_labels = [''] * len(labels)
        self.axis.set_yticklabels(empty_string_labels)

        #self.axis.xaxis.set_major_formatter(plt.NullFormatter())
        #self.axis.yaxis.set_major_formatter(plt.NullFormatter())
        img = self.default_image
        self.image = self.axis.imshow(img)
        return fig


    def initialize_cam(self):
        initialized = self.cam.initialize()
        if initialized:
            return True
        else:
            return False

    def get_next_image(self,*args):
        if self.user_wants_stop:
            self.animation.event_source.stop()
            self.cam.close()
            self.capture_on = False
            self.user_wants_stop = False
        img = self.default_image

        if self.cam.initialized:
            img = self.cam.get_next_image()

        if self.rotation:
            img = np.rot90(img, self.rotation/90)

        self.image.set_array(img)

        if self.mode is 'Record':
            self.image_buffer.append(img)

            if len(self.image_buffer)>=self.nframes:
                self.user_wants_stop = True

        return img,

    def _start_fired(self):
        self.start_capture()

    def start_capture(self):
        self.capture_on = True
        plt.ion()
        interval = int(1000 / self.fps)
        if self.mode is 'Record':
            self.image_buffer = []
        self.animation = animation.FuncAnimation(self.figure, self.get_next_image,
                                                 init_func=self.initialize_cam,
                                                 #frames=self.nframes,
                                                 repeat=True,
                                                 interval=interval)
        self.animation.event_source.start()
        self.figure.canvas.draw()

    def _stop_fired(self):
        self.user_wants_stop = True
        try:
            self.cam.close()
        except:
            pass

    def _next_im_fired(self):
        self.iterate_display()

    def _prev_im_fired(self):
        self.iterate_display(-1)

    def iterate_display(self,step=1):
        images = len(self.image_buffer)-1
        if images:
            self.im_num = (self.im_num+step)%(images)

    def _im_num_changed(self,new):
        if len(self.image_buffer)>new:
            self.image.set_array(self.image_buffer[self.im_num])
            self.figure.canvas.draw()


"""

