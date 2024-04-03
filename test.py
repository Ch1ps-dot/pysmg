from smg import Smg
from types import MethodType

def add(self, b):
    print(b[0]+b[1])


f = open("xml-sample/mqtttest.xml",'r')
o = open("out",'+bw')
src = f.read()
p = Smg()
p.fromstring(src)
p.output(o)
# o.close()
# o = open("out",'rb')
# p.send('127.0.0.1','12345',o)

# class T:
#     def __init__(self):
#         pass

#     def check(self, name):
#         if(hasattr(self, name)):
#             func = self.__getattribute__(name)
#             func()

# def say(self):
#     print("Hi")

# t = T()
# setattr(t, 'say', None)
# t.say = MethodType(say,t)
# t.check('say')