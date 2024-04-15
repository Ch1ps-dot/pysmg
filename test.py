from smg import mqtt_gen

def add(self, b):
    print(b[0]+b[1])


f = open("xml-sample/mqtttest.xml",'r')
o = open("out",'+bw')
src = f.read()
p = mqtt_gen()
p.fromstring(src)
p.gen(o)

f = open("out",'rb')
p.send('127.0.0.1', '1880', f)
# root = etree.fromstring(src)
# b = root.find('.//sheader')
# print(b.getparent())


