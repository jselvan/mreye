from mreye.interface import Interface
from mreye.getLogger import getLogger

def test_reward():
    interface = Interface('test.bin', getLogger())
    interface.good_monkey()
    interface.stop()

if __name__ == '__main__':
    test_reward()
