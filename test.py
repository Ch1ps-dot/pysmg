from smg import Smg
import random
import copy
from lxml import etree

f = open("httptest.xml",'r')
o = open("out",'+bw')
src = f.read()
p = Smg()
p.fromstring(src)
p.output(o)
o.close()
o = open("out",'rb')
p.send('127.0.0.1','12345',o)
