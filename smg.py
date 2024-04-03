import random
import socket
from lxml import etree
from types import MethodType

class Smg():
    """
        Implementation of protocol generator.
        Output the protocol message with the template.
    """

    def __init__(self) -> None:
        """
            Every element of datamodel stands for a node of protocol AST.
            The attribute of the node includes name, type, value, lenth.
            - The definitions of type include:
                string: The token can not be changed.
                strings: The token is selected from a list.
                bits/bytes: The token is generated within the range given by value.
                function: Invoking special function to generate token.
                set: Node set, be able to carry nodes of any type include set.

            - The definition of value must obey the rules:
                string: If the type of node is string, the value is determined at parse time.
                strings: If it is strings, the strings must be seperated by '|' (e.g. 502|404|201 ). 
                bits/bytes: The context of token was randomly selected from given list, and the length is determinated
                        by the prefix number (e.g. 10:[0x1-0x20][0x30-0x40]). The range of charater must be offered
                        by hex.
                function: Some token has special semantic. 
                        It can not be determined until other nodes has been parsed. 

            - The length attribute is counted at runtime. Besides the suffix character indicates the size
                of length.
        """

        self.modified = False
        self.conent = [] # Store the content of Elements. Aiming to buffer the temporary message 
                         # in every generating process.
        self.funcSeq = [] # Function evoking sequence
        self.argSeq = {}
        self.buffer = '0b'

    def fromstring(self, src):
        self.root = etree.fromstring(src)

    def addFunction(self, name, func):
        """
            add user-defined function to smg
        """
        setattr(self, name, MethodType(func, self))

    def __getcontent(self, attrib):
        """
            Help Elements get content from buffer
        """
        index = int(attrib['content'])
        return self.conent[index]
    
    def __setcontent(self, attrib, content):
        """
            Help Elements put content into buffer
        """
        self.conent.append(content)
        attrib['content'] = str(len(self.conent) - 1)

    def __parseRange(self, str):
        j = 0
        while str[j] != '~': j = j + 1
        lower = eval(str[1:j])
        i = j
        while j < len(str): j = j + 1
        upper = eval(str[i+1:j])
        return lower, upper
    
    def __parseMap(self, str):
        j = 0
        while str[j] != '-': j = j + 1
        src = str[0:j]
        i = j
        while j < len(str): j = j + 1
        dst = str[i+1:j]
        print(f'  map: {src}-{dst}')
        return src, dst
    
    def __funcEvoke(self, funcSeq, argSeq):
        """
            evoke functions with the sequence of function
        """
        print('\t\t[BEGIN EVOKING FUNCTION]')
        for i in range(len(funcSeq)):
            if(i == 0): print(f"EVOKING SEQ: {funcSeq[i]}", end='')
            else: print(f' --> {funcSeq[i]}', end='')
        print('\n')
        for funcname in funcSeq:
            print(f'EVOKE: {funcname}')
            func = self.__getattribute__(funcname)
            if len(argSeq) == 0:        
                func()
            else:
                args = argSeq[funcname]
                func(args)
        print('\t\t[END EVOKING FUNCTION]')

    def send(self, ip, port, f):
        """
            interface for tcp connection
        """
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((ip, int(port)))
        client_socket.sendall(f.read())

    def __outSet(self, nodes, f):
        for node in nodes:
            print(f"OUTPUT: {node.tag}")
            attrib = node.attrib
            type = attrib['type']
            if (type == 'set'):
                self.__outSet(node)
            else:
                length = attrib['length']
                size = length[-1]

                if(type == 'string' or type == 'strings'):
                    f.write(self.__getcontent(attrib).encode())
                elif(size == 'B'):
                    f.write(self.__getcontent(attrib))
                elif(size == 'b'):
                    c = self.__getcontent(attrib)
                    self.buffer += c[2:]

                    if(len(self.buffer) == 10):
                        # output bits with big-endian
                        f.write(eval(self.buffer).to_bytes(1,'big'))
                        self.buffer = '0b'

    def output(self, f):
        """
            Concatenate the message of nodes and output the result.
        """
        self.__parse(self.root)
        self.__funcEvoke(self.funcSeq, self.argSeq)
        self.modified = True

        print("\n\t\t[BEGIN OUTPUT]")
        for node in self.root:
            
            attrib = node.attrib
            type = attrib['type']
            if (type == 'set'):
                print(f'SET[{node.tag}]')
                self.__outSet(node, f)
            else:
                print(f"OUTPUT: {node.tag}")
                length = attrib['length']
                size = length[-1]

                if(type == 'string' or type == 'strings'):
                    f.write(self.__getcontent(attrib).encode())
                elif(size == 'B'):
                    f.write(self.__getcontent(attrib))
                elif(size == 'b'):
                    c = self.__getcontent(attrib)
                    self.buffer += c[2:]

                    if(len(self.buffer) == 10):
                        # output bits with big-endian
                        f.write(eval(self.buffer).to_bytes(1,'big'))
                        self.buffer = '0b'
        
        if(len(self.buffer) != 2):
            raise Exception("Message doesn't fullfill bytes aligning")
        

    def __parseString(self, node):
        attrib = node.attrib
        self.__setcontent(attrib, attrib['value'])

        if (self.modified == False):
            attrib['length'] = str(len(attrib['value']))

        print(f'parseString: {self.__getcontent(attrib)}')


    def __parseStrings(self, node):
        """
            Select one item from the 'value' list, 
            then add it to tokens.
        """
        attrib = node.attrib

        # Deal with the value attribute when parsing choice node at first time       
        choices = attrib['value'].split('|')
        upper = len(choices)-1
        option = random.randint(0, upper)

        self.conent.append(choices[option])
        attrib['content'] = str(len(self.conent)-1)
        attrib['length'] = str(len(attrib['content']))

        print(f"parseCoice: select {attrib['content']}")


    def __parseBytes(self, node):
        """
            Generating bytes-like data with the content of 'value'.
        """
        attrib = node.attrib
        bound = []
        num = 0
        s = attrib['value']

        # parse attribute of value
        for i in range(len(s)):

            # extract the length of value
            if (s[i] == ':' and self.modified == False):
                if(s[0] == '['):
                    lower, upper = self.__parseRange(s[1:])
                    num = random.randint(lower, upper)
                else:
                    num = int(s[0:i])
                attrib['length'] = str(num) + 'B'

            # extract the range of byte
            if (s[i] == '['):
                j = i
                while s[j] != '~': j = j + 1
                lower = eval(s[i+1:j])
                i = j
                while s[j] != ']': j = j + 1
                upper = eval(s[i+1:j])
                bound.append([lower, upper])
        
        # generate content of value
        c = []
        for i in range(num):
            r = bound[random.randint(0,len(bound)-1)]
            c.append(random.randint(r[0],r[1])) 

        c = bytes(c) # translate int to bytes
        self.__setcontent(attrib, c)
        print(f"parseBytes: generate {self.__getcontent(attrib)}")


    def __parseBits(self, node):
        """
            Generating bits-like data according to the content of 'value'.
        """
        attrib = node.attrib
        bound = []
        num = 0
        s = attrib['value']

        # extract the length of value
        for i in range(len(s)):
            if (s[i] == ':' and self.modified == False):
                if(s[0] == '['):
                    lower, upper = self.__parseRange(s[1:])
                    num = random.randint(lower, upper)
                else:
                    num = int(s[0:i])
                
                attrib['length'] = str(num)+ 'b'

            # extract the range of byte
            if (s[i] == '['):
                j = i
                while s[j] != '~': j = j + 1
                lower = eval(s[i+1:j])
                i = j
                while s[j] != ']': j = j + 1
                upper = eval(s[i+1:j])
                bound.append([lower, upper])
        
        # generate content of value    
        r = bound[random.randint(0,len(bound)-1)]
        c = random.randint(r[0],r[1])
        c = bin(c) # translate int to bin

        # add prefix zero to fullfill length requirment
        c = '0b' + (num-len(c)+2)*'0'+ c[2:]

        # store the bits vlaue as string like 0b0010
        self.__setcontent(attrib, c)
        print(f"parseBits: generate {self.__getcontent(attrib)}")
        

    def __parseFunc(self, node):
        """
            Parse function node.
            There are some pre-defined functions, users can define function by themselves as well.
            Functions should be evoked after all nodes has been parsed. 
        """
        attrib = node.attrib
        str = attrib['value']
        args = []
        funcname = ''

        for i in range(len(str)):
            if(str[i] == ':'):
                funcname = str[:i]
                print(f'parseFunc: {funcname}')
                if(not hasattr(self, funcname)): raise Exception("Undefinde function")
                self.funcSeq.append(funcname)

            if(str[i] == '['):
                j = i
                while(str[j] != ']'): j = j + 1
                args.append(str[i+1:j])
        self.argSeq[funcname] = args
  

    def __parse(self, root):
        for node in root:
            print(f"[NODE]: {node.tag}")
            attr = node.attrib
            if attr['type'] == 'string':
                self.__parseString(node)
            elif attr['type'] == 'strings':
                self.__parseStrings(node)
            elif attr['type'] == 'bytes':
                self.__parseBytes(node)
            elif attr['type'] == 'bits':
                self.__parseBits(node)
            elif attr['type'] == 'function':
                self.__parseFunc(node)
            elif attr['type'] == 'set':
                self.__parse(node)
                
    def mqtt_map(self, args):
        src, dst = self.__parseMap(args[0])
        src = self.root.find('.//'+src)
        dst = self.root.find('.//'+dst)
        src_attrib = src.attrib
        dst_attrib = dst.attrib
        src_type = self.__getcontent(src_attrib)
        
        src_type = eval(src_type)
        if src_type in [0x1,0x2,0x4,0x5,0x7,0x9,0xb,0xc,0xd,0xe]:
            self.__setcontent(dst_attrib, '0b0000')
        elif src_type in [0x6,0x8,0xa]:
            self.__setcontent(dst_attrib,'0b0010')

        dst_attrib['length'] = '4b'
    
    def mqtt_length(self, args):
        pass

    def bitCount(self):
        pass

    def byteCount(self):
        """
            count the byte number with the tag name.
        """

    def checkSum(self):
        pass

    def valueCount(self):
        pass

    


