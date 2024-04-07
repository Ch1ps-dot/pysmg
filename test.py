from smg import Smg
from types import MethodType
from lxml import etree

def add(self, b):
    print(b[0]+b[1])


f = open("xml-sample/mqtttest.xml",'r')
o = open("out",'+bw')
src = f.read()
p = Smg()
p.fromstring(src)
p.gen(o)

# root = etree.fromstring(src)
# b = root.find('.//sheader')
# print(b.getparent())

