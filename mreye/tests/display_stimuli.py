from mreye.display import Display
from mreye.getLogger import getLogger
import time
import threading
def experiment(display,logger):
    logger.debug('experiment started')
    display.post_update([dict(type="circle", x=0, y=0, r=1, c=(0,0,255), z=1)])
    logger.debug('circle posted')
    time.sleep(2)
    display.post_update([dict(type='video', x=0, y=0, z=0, path=r"C:\Users\lreba\OneDrive\Desktop\ml\reward\stimuli\BodyPart_Block_1_Longer.avi")])
    time.sleep(16)
    display.post_update(['CLEAR'])
    logger.debug('clearing')
    time.sleep(2)
    display.post_update(['QUIT'])
    logger.debug('closing')
    
def test_display_stimuli():
    logger=getLogger(name='test',printLevel='DEBUG')
    display = Display([1920,0,1920,1080], 119, 38.4, logger=logger)
    threading.Thread(target=experiment, name='exp', args=(display,logger)).start()
    display.start()
if __name__=='__main__':
    test_display_stimuli()