import random
import socket
from lxml import etree
from types import MethodType

class Smg():
    """
        [Simple Message Generator]

        Every element of datamodel stands for a node of protocol AST.
            The attribute of the node includes name, ntype, value, length, dtype

            - The name of node indicated by the tag of node, therefore the tag is supposed to be unique.

            - The type of node(ntype) include:
                string: The token can not be changed.
                strings: The token is selected from a list.
                bits/bytes: The token is generated within the range given by value.
                function: Invoking special function to generate token.
                set: Node set, be able to carry nodes of any type include set.

            - The content of value must obey the rules:
                string: If the type of node is string, the value is determined at parse time.
                strings: If it is strings, the string which may be selected must be seperated by '|' (e.g. 502|404|201 ). 
                bits/bytes: The context of token would be randomly selected from given list, and the length is depended on 
                        the prefix number (e.g. 10:[0x1-0x20][0x30-0x40]).Besides the length can be randomly selected from
                        a range.(e.g. [10-20]:[0x1-0x20][0x30-0x40])
                function: Some token has special semantic, you have to specify a function to calculate the result.
                        Functions can not be invoked until other nodes have been parsed.
                        !!! Any function must deal with following things:
                            1. set the dtype of node
                            2. return the length of content of node.
                            3. set the content of node. 

            - The length attribute is counted at runtime. We use bit as the basic unit. Because of the priority of
                function, how to count the length of node with function type is a big problem. It must be delayed
                until the function has been executed.

            - The dtype indicated the type of data.
                B: bytes
                b: bits
                R: reference to another node.
    """

    def __init__(self) -> None:
        self.modified = False # Hasn't been used. May be used to accelerate the next time generation.
        self.content = [] # Content buffer
        self.funcSeq = [] # Evoking sequence of function
        self.argSeq = {}  # Arguments dict of given function. 
        self.buffer = '0b' # Collecting bits and resembling them to byte.

    def fromstring(self, src):
        """
            read xml doc from string
        """
        self.root = etree.fromstring(src)
        if self.root.tag != 'SMG': raise Exception("invalid root tag")
        for node in self.root:
            if (node.tag == 'text'):
                self.text = node
            if (node.tag == 'data'):
                self.data = node
            if (node.tag == 'priority'):
                self.priority = node

    def addFunction(self, name, func):
        """
            add user-defined function to smg
        """
        setattr(self, name, MethodType(func, self))

    def __setfunctionSize(self, node, length):
        """
            add the length of node of function type.
            Recursively add to set node.
        """
        attrib = node.attrib
        attrib['length'] = str(length + int(attrib['length']))
        
        if(node.getparent().tag == "SMG"): pass
        elif(node.getparent().tag == 'text' or node.getparent().attrib['ntype'] == 'set'):
            self.__setfunctionSize(node.getparent(), length)

    def __getcontent(self, attrib):
        """
            Get content from content buffer
        """
        index = int(attrib['content'])
        return self.content[index]
    
    def __setcontent(self, attrib, content):
        """
            Put content into content buffer
        """
        self.content.append(content)
        attrib['content'] = str(len(self.content) - 1)

    def __parseRange(self, str):
        """
            Parse value units which stands for number range.
        """
        j = 0
        while str[j] != '~': j = j + 1
        lower = eval(str[1:j])
        i = j
        while j < len(str): j = j + 1
        upper = eval(str[i+1:j])
        return lower, upper
    
    def __parseMap(self, str):
        """
            Parse value units which stands for map relation of nodes.
        """
        j = 0
        while str[j] != '-': j = j + 1
        src = str[0:j]
        i = j
        while j < len(str): j = j + 1
        dst = str[i+1:j]
        print(f'  map: {src}-{dst}')
        return src, dst
    
    def __setfunctionPriority(self):
        """
            If the priority of function has been indicated, set function sequence with the priority.
        """
        attrib = self.priority.attrib
        str = attrib['value']
        funcSeq = []
        for i in range(len(str)):
            if (str[i] == '['):
                j = i
                while(str[j] != ']'): j = j + 1
                funcSeq.append(str[i+1:j])
        self.funcSeq = funcSeq
    
    def __funcinvoke(self, funcSeq, argSeq):
        """
            invoke functions with the sequence of function
        """
        self.__setfunctionPriority()
        print('\n\t\t[BEGIN EVOKING FUNCTION]')
        for i in range(len(funcSeq)):
            if(i == 0): print(f"EVOKING SEQ: {funcSeq[i]}", end='')
            else: print(f' --> {funcSeq[i]}', end='')
        print('\n')
        for funcname in funcSeq:
            print(f'invoke: {funcname}')
            func = self.__getattribute__(funcname)
            if len(argSeq) == 0:        
                func()
            else:
                # invoke function
                args = argSeq[funcname]

                # set the length of node
                length = func(args)
                fnode = self.root.find('.//'+args[0])
                self.__setfunctionSize(fnode, length)
        print('\t\t[END EVOKING FUNCTION]')

    def send(self, ip, port, f):
        """
            interface for tcp connection
        """
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((ip, int(port)))
        client_socket.sendall(f.read())

    def __genSet(self, nodes, f):
        """
            recursively output the message of set-node
        """
        for node in nodes:
            attrib = node.attrib
            ntype = attrib['ntype']
            if (ntype == 'set'):
                print(f"ENTER SET: [{node.tag}]\tset length:{attrib['length']}b")
                self.__genSet(node, f)
            else:
                length = attrib['length']
                dtype = attrib['dtype']
                print(f"GENERATE: [{node.tag}]\tlength: {length}b")

                if(ntype == 'string' or ntype == 'strings'):
                    f.write(self.__getcontent(attrib).encode())
                elif(dtype == 'B'):
                    f.write(self.__getcontent(attrib))
                elif(dtype == 'b'):
                    c = self.__getcontent(attrib)
                    self.buffer += c[2:]

                    if(len(self.buffer) == 10):
                        # output bits with big-endian
                        f.write(eval(self.buffer).to_bytes(1,'big'))
                        self.buffer = '0b'
                elif(dtype == 'R'):
                    # deal with node reference
                    ref = self.__getcontent(attrib)
                    node = self.data.find('.//' + ref)
                    self.__genSet(node, f)

    def gen(self, f):
        """
            Concatenate the message of nodes and generate the result.
        """
        
        print("\t\t[BEGIN PARSE]")
        self.__parse(self.text)
        self.__funcinvoke(self.funcSeq, self.argSeq)
        self.modified = True

        print(f"\n\t\t[BEGIN GENERATION]\ttotal length: {self.text.attrib['length']}b")
        self.__genSet(self.text, f)
        # for node in self.text:
            
        #     attrib = node.attrib
        #     ntype = attrib['ntype']
        #     if (ntype == 'set'):
        #         print(f"ENTER SET: [{node.tag}]\tset length:{attrib['length']}b")
        #         self.__genSet(node, f)
        #     else:
        #         length = attrib['length']
        #         dtype = attrib['dtype']
        #         print(f"GENERATE: [{node.tag}]\tlength: {length}b")

        #         if(ntype == 'string' or ntype == 'strings'):
        #             f.write(self.__getcontent(attrib).encode())
        #         elif(dtype == 'B'):
        #             f.write(self.__getcontent(attrib))
        #         elif(dtype == 'b'):
        #             c = self.__getcontent(attrib)
        #             self.buffer += c[2:]

        #             if(len(self.buffer) == 10):
        #                 # output bits with big-endian
        #                 f.write(eval(self.buffer).to_bytes(1,'big'))
        #                 self.buffer = '0b'
        #         elif(dtype == 'R'):
        #             pass
        
        if(len(self.buffer) != 2):
            raise Exception("Message doesn't fullfill bytes aligning")
        

    def __parseString(self, node):
        """
            parse the node of string type
        """
        attrib = node.attrib
        self.__setcontent(attrib, attrib['value'])
        attrib['dtype'] = 'B'

        if (self.modified == False):
            attrib['length'] = str(len(attrib['value'])*8)

        print(f'parseString: {self.__getcontent(attrib)}')
        return int(attrib['length'])


    def __parseStrings(self, node):
        """
            Parse the node of strings type.
            Randomly selecting one item from the lists.
        """
        attrib = node.attrib
        attrib['dtype'] = 'B'

        # Deal with the value attribute when parsing choice node at first time       
        choices = attrib['value'].split('|')
        upper = len(choices)-1
        option = random.randint(0, upper)

        self.content.append(choices[option])
        attrib['content'] = str(len(self.content)-1)
        attrib['length'] = str(len(attrib['content'])*8)

        print(f"parseStrings: select {attrib['content']}")
        return int(attrib['length'])


    def __parseBytes(self, node):
        """
            Parse the node of Bytes type.
            Generating bytes-like data with the content of 'value', then storing these data
            into the content buffer.
        """
        attrib = node.attrib
        bound = []
        num = 0
        s = attrib['value']
        attrib['dtype'] = 'B'

        # parse attribute of value
        for i in range(len(s)):

            # extract the length of value
            if (s[i] == ':' and self.modified == False):
                if(s[0] == '['):
                    lower, upper = self.__parseRange(s[1:])
                    num = random.randint(lower, upper)
                else:
                    num = int(s[0:i])
                attrib['length'] = str(num*8)

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
        return int(attrib['length'])


    def __parseBits(self, node):
        """
            Parse the node of Bits type.
            Generating bits-like data according to the content of 'value', and do the same
            thing as parseBytes
        """
        attrib = node.attrib
        bound = []
        num = 0
        s = attrib['value']
        attrib['dtype'] = 'b'

        # extract the length of value
        for i in range(len(s)):
            if (s[i] == ':' and self.modified == False):
                if(s[0] == '['):
                    lower, upper = self.__parseRange(s[1:])
                    num = random.randint(lower, upper)
                else:
                    num = int(s[0:i])
                
                attrib['length'] = str(num)

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
        return int(attrib['length'])
        

    def __parseFunc(self, node):
        """
            Parse node of function type.
            There are some pre-defined functions, users can define function by themselves as well.
            Functions should be invoked after all nodes has been parsed. We stored the functions which haven't
            been invoked as a FuncSeq, and store their arguments in argSeq. The first argument of every node of
            argSeq must be the tag name of the node.
        """
        attrib = node.attrib
        str = attrib['value']
        attrib['length'] = '0'
        args = [node.tag]
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
        return 0
  

    def __parse(self, root):
        """
            The main parser loop.
            After parsing node, the content(include value), length, dtype of normal node will be determinated.
            The function which will be invoked later as well as its arguments will be added to funcSeq.
        """
        length = 0
        for node in root:
            print(f"[NODE]: {node.tag}")
            attr = node.attrib
            if attr['ntype'] == 'string':
                length = length + self.__parseString(node)
            elif attr['ntype'] == 'strings':
                length = length + self.__parseStrings(node)
            elif attr['ntype'] == 'bytes':
                length = length + self.__parseBytes(node)
            elif attr['ntype'] == 'bits':
                length = length + self.__parseBits(node)
            elif attr['ntype'] == 'function':
                length = length + self.__parseFunc(node) # noted the length couldn't be counted at once.
            elif attr['ntype'] == 'set':
                length = length + self.__parse(node)
        root.attrib['length'] = str(length)
        return length
                
    def mqtt_map(self, args):
        """
            Specified function of mqtt protocol.
            Generating content of flags bits with the information of type.
        """
        src, dst = self.__parseMap(args[1])
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

        dst_attrib['dtype'] = 'b'

        return 4
    
    def mqtt_length(self, args):
        """
            Specified function of mqtt protocol.
            Generating text of length.
        """
        node = self.root.find('.//'+args[0])
        attrib = node.attrib

        length = self.byteCount(args) # actual byte number
        length_bit = bin(length)[2:]  # translate int to byte
        length_byte = []              # store every byte of mqtt_length

        n = len(length_bit)
        cur = n
        while(cur > 0):
            
            if(cur <= 7): 
                length_byte.append(eval('0b'+length_bit[0:cur]))
                break
            else:
                length_byte.append(eval('0b1' + length_bit[cur-7:cur]))
            cur = cur - 7
        self.__setcontent(attrib, bytes(length_byte))
        print(f'  actual_length: {length}')
        print(f'  mqtt_length: {bytes(length_byte)}')
        attrib['dtype'] = 'B'
        return n // 7 + 1
    
    def mqtt_vheader(self,args):
        """
            Specified function of mqtt protocol.
            map variable header with message type.
        """
        types = self.text.find('.//' + args[0])
        vheader = self.text.find('.//' + args[1])
        attrib_types = types.attrib
        

        vheader.attrib['dtype'] = 'R'
        return 0

    def bitCount(self):
        pass

    def byteCount(self, args):
        """
            count the byte number of args.
        """
        length = 0
        for i in range(len(args)):
            if i == 0: continue
            node = self.root.find('.//' + args[i])
            length = length + int(node.attrib['length'])

        return length // 8

    def checkSum(self):
        pass

    def valueCount(self):
        pass

    


