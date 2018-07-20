from traits.api import *
from traitsui.api import *
from log_viewer import LogStream
import logging
import numpy as np
import threading
from time import sleep
from constants import IOService, ReadMode
#from threading import RLock
from collections import deque


#####################################################################
############ DEPRECATED #############################################
#####################################################################
class BaseCamera(HasTraits):
    name = Str('')
    initialized = Bool(False)
    recording = Bool(False)
    read_mode = Enum([mode for mode in ReadMode])
    shape = Tuple()
    img_buffer = Instance(deque,transient=True)
    buffer_size = Int(100)
    user_wants_stop = Bool(False)
    t = Any(transient=True)
    provides = Set({IOService.CAM_READ})
    view = View()


    def __repr__(self):
        return self.name

    def __str__(self):
        return self.name

    def _read_mode_default(self):
        return ReadMode.LIVE

    def initialize(self):
        try:
            if self.mode==ReadMode.LIVE:
                self.img_buffer = deque(maxlen=1)
            else:
                self.img_buffer = deque(maxlen=self.buffer_size)
            success  = self.init_cam()
            self.initialized = success
        except:
            return False

    def init_cam(self):
        raise NotImplementedError

    def start(self, num=None):
        #self.recorder(num=num)
        self.user_wants_stop = False
        if not self.initialized:
            self.initialize()
        self.t = threading.Thread(target=self.recorder,args=(num,))
        self.t.start()
        self.recording = True

    def read_data(self, nsamp=1):
        if self.recording:
            pass
        else:
            self.start(nsamp)
            sleep(0.05)
        try:
            for i in range(20):
                if len(self.img_buffer)<nsamp:
                    sleep(0.05)
                else:
                    break

            imgs = [self.read_next() for n in range(nsamp)]
            return np.squeeze(np.array(imgs))
        except:
            return np.full(self.shape, np.nan)

    def read_next(self):
        if self.read_mode == ReadMode.FIFO:
            img = self.img_buffer.popleft()
        else:
            img = self.img_buffer.pop()
        return img

    def record(self):
        raise NotImplemented

    def stop(self):
        pass

    def on_close(self):
        pass

    def close(self):
        self.user_wants_stop = True
        try:
            self.t.join(self.exposure+5)
        except:
            pass

        self.on_close()
        self.initialized = False

    def add_to_queue(self, img):
        self.img_buffer.append(img)

    def recorder(self, num=None):
        self.recording = True
        try:
            if num:
                nleft = num
                while nleft:
                    self.record()
                    nleft -= 1
                    if self.user_wants_stop:
                        break
            else:
                while True:
                    self.record()
                    sleep(0.02)
                    if self.user_wants_stop:
                        break
        except:
            pass
        finally:
            self.stop()
            self.recording = False


class OpenCVCamera(BaseCamera):
    name = 'Generic Camera'

    cap = Any(transient=True)
    cam_num = Int(0)
    exposure = Int(5)
    gain = Int(1)
    shape = Tuple((480,640,3),cols=2,labels=['Rows','Columns'])
    color_mode = Enum('GREYSCALE', ['RGB','GREYSCALE'])
    #image_buffer = List
    #buffer_size = Int(50)

    image = Array

    log = Instance(LogStream,transient=True)

    traits_view = View(
        HGroup(
            Item(name='read_mode', label='Mode', width=-100),
            Item(name='cam_num',label='Cam Number',width=-60),
            Item(name='shape', show_label=False, enabled_when='False',width=-250),
            Item(name='exposure', label='Exposure', enabled_when='False',width=-60),
            Item(name='gain', label='Gain', enabled_when='False',width=-60),
               ),
    )

    #def _shape_default(self):
        #return (1280,1024)


    def init_cam(self):
        if self.initialized:
            return True
        try:
            import cv2
            #import ids
        except:
            return False

        logger = logging.getLogger('__main__')
        self.cap = cv2.VideoCapture(self.cam_num)
        rows = self.cap.get(3)
        cols = self.cap.get(4)
        self.shape = (rows,cols)
        #self.cam.color_mode = ids.ids_core.COLOR_RGB8
        #self.cam.exposure = self.exposure
        if self.cap.isOpened():
            self.initialized = True
            logger.info('Cam opened.')
            return True
        else:
            self.cap.release()
            logger.info('Cam wont open')
            return False
            #raise RuntimeError, 'Cam wont open'
        #self.figure.tight_layout()

    def record(self):
        if self.initialized:
            ret, img = self.cap.read()
            if ret:
                #grey = img.sum(axis=2)
                if self.color_mode=='GREYSCALE':
                    img = np.dot(img[...,:3], [0.299, 0.587, 0.114])
                if img.shape != self.shape:
                    self.shape = img.shape
                self.add_to_queue(img)
                return True
        return None

    def on_close(self):
        if self.initialized and self.cap.isOpened():
            self.cap.release()
        self.initialized = False
        logger = logging.getLogger('__main__')
        logger.info('Camera closed.')
        

        
class MockCamera(BaseCamera):
    name = 'Mock Camera'
    _shift = Int(0)
    frate = Int(100)
    shape = Tuple((50, 50),cols=2,labels=['rows', 'cols'])
    traits_view = View(
        HGroup(
            Item(name='read_mode', label='Mode', width=-120),
            Item(name='frate', label='FPS', width=-60),
            Item(name='shape', label='Dimensions', width=-200),
            #Item(name='_shift', label='Shift', width=-60),

        ),
    )

    def init_cam(self):
        pass

    def record(self):
        x = np.linspace(0.,1.,num=self.shape[0])
        y = np.arange(0.,self.shape[1])
        img = np.meshgrid(x,y)[1]
        img = np.roll(img, self._shift, axis=0)
        self.shape = img.shape
        self._shift += self.shape[1]//50
        if self._shift > self.shape[1]:
            self._shift = 0
        sleep(1/self.frate)
        self.add_to_queue(img)

camera_dict = {
'OpenCV Camera': OpenCVCamera,
'Mock Camera':MockCamera,

}

if __name__=='__main__':
    from time import sleep
    app = OpenCVCamera()
    app.initialize()
    app.start()
    for n in range(3):
        img = app.read_data()
        print(img)
        sleep(0.5)
    app.close()
    #app.configure_traits()