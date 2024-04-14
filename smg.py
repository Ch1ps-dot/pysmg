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
                ref: reference to node placed under data node. Reference method usually have special syntax. It is a
                    special function, so the ntype of ref is function, but with the dtype R. When we parse node of
                    ref type, its special reference function should be invoked at once. Thus we can determine which
                    node have been referenced and should be parsed.

            - The content of value must obey the rules:
                string: If the type of node is string, the value is determined at parse time.
                strings: If it is strings, the string which may be selected must be seperated by '|' (e.g. 502|404|201 ). 
                bits/bytes: The context of token would be randomly selected from given list, and the length is depended on 
                        the prefix number (e.g. 10:[0x1-0x20][0x30-0x40]).Besides the length can be randomly selected from
                        a range.(e.g. [10-20]:[0x1-0x20][0x30-0x40])
                function: Some token has special semantic, you have to specify a function to calculate the result.
                        Functions can not be invoked until other nodes have been parsed.
                        !!! Normal function must finish following things:
                            1. set the dtype of node
                            2. return the length of content of node.
                            3. set the content of node.   
                ref: the content of ref is the node which is referenced to.
                        !!! ref function must finish following things:
                            1. return name of the node which is reference ti
                            2. set the content of src node with the name of dst node

            - The length attribute is counted at runtime. We use bit as the basic unit. Because of the priority of
                function, how to count the length of node with function type is a big problem. It must be delayed
                until the function has been executed. The length of ref node counldn`t be determinated until all
                function had been invoked. 

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
        self.refs = {}
        self.dataset = []

    def setfunctionSize(self, node, length):
        """
            add the length of node of function type.
            Recursively add to set node.
        """
        attrib = node.attrib
        attrib['length'] = str(length + int(attrib['length']))
        
        if(node.getparent().tag == "SMG" or node.getparent().tag == "data"): pass
        elif(node.getparent().tag == 'text' or node.getparent().attrib['ntype'] == 'set'):
            self.setfunctionSize(node.getparent(), length)

    def getcontent(self, attrib):
        """
            Get content from content buffer
        """
        index = eval(attrib['content'])
        return self.content[index]
    
    def setcontent(self, attrib, content):
        """
            Put content into content buffer
        """
        self.content.append(content)
        attrib['content'] = str(len(self.content) - 1)

    def parseRange(self, str):
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
    
    def parseMap(self, str):
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
    
    def setfunctionPriority(self):
        """
            If the priority of function has been defined, set function sequence with the priority.
        """
        if (hasattr(self, 'priority')):
            attrib = self.priority.attrib
            str = attrib['value']
            funcSeq = []
            for i in range(len(str)):
                if (str[i] == '['):
                    j = i
                    while(str[j] != ']'): j = j + 1
                    funcSeq.append(str[i+1:j])
            self.funcSeq = funcSeq

    def funcRef(self, args):
        """
            Generating the content of node which is referenced to.
            Besides set the length of src node.
        """
        ref_name = args[0]
        src_node = self.root.find('.//' + ref_name)  
        dst_name = self.getcontent(src_node.attrib)
        dst_node = self.root.find('.//' + dst_name)

        print(dst_node.tag)
        length = int(dst_node.attrib['length'])
        self.setfunctionSize(src_node, length)
        
    def funcinvoke(self, funcSeq, argSeq):
        """
            invoke functions with the sequence of function
        """
        self.setfunctionPriority()
        print('\n\t\t[BEGIN INVOKING FUNCTION]')
        for i in range(len(funcSeq)):
            if(i == 0): print(f"EVOKING SEQ: {funcSeq[i]}", end='')
            else: print(f' --> {funcSeq[i]}', end='')
        print('\n')

        for funcname in funcSeq:
            print(f'invoke: {funcname}')
            if  funcname[0] == '@':
                # reference function call        
                self.funcRef(argSeq[funcname])
            else:
                args = argSeq[funcname]
                func = self.__getattribute__(funcname)
                fnode = self.root.find('.//'+args[0])
                # invoke function
                args = argSeq[funcname]

                # set the length of node
                length = func(args)
                self.setfunctionSize(fnode, length)
        print('\t\t[END EVOKING FUNCTION]')
    
    def clearMark(self, root):
        root.attrib['parsed'] = 'N'
        for node in root:
            node.attrib['parsed'] = 'N'
            if(node.attrib['ntype'] == 'set'):
                self.clearMark(node)

    def send(self, ip, port, f):
        """
            interface for tcp connection
        """
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((ip, int(port)))
        client_socket.sendall(f.read())

    def genSet(self, nodes, f):
        """
            recursively output the message of set-node
        """
        if(nodes.tag=='text' or nodes.attrib['ntype']=='set'):
            print(f"\nENTER: [{nodes.tag}]\tlength: {nodes.attrib['length']}b")
            print(f"  |- FUNCTIONS {nodes.attrib['content']}")

        for node in nodes:
            attrib = node.attrib
            ntype = attrib['ntype']
            if (ntype == 'set'):
                self.genSet(node, f)
            else:
                length = attrib['length']
                dtype = attrib['dtype']
                if(dtype != 'R'):
                    print(f"  GENERATE: [{node.tag}]\tlength: {length}b")

                if(ntype == 'string' or ntype == 'strings'):
                    f.write(self.getcontent(attrib).encode())
                elif(dtype == 'B'):
                    f.write(self.getcontent(attrib))
                elif(dtype == 'b'):
                    c = self.getcontent(attrib)
                    self.buffer += c[2:]

                    if(len(self.buffer) == 10):
                        # output bits with big-endian
                        f.write(eval(self.buffer).to_bytes(1,'big'))
                        self.buffer = '0b'
                elif(dtype == 'R'):
                    # deal with node reference
                    
                    ref = self.getcontent(attrib)
                    ref_node = self.data.find('.//' + ref)
                    if(ref_node == None): raise Exception("reference null node")
                    print(f'{node.tag} reference {ref_node.tag}')
                    self.genSet(ref_node, f)
        

    

    def parseString(self, node):
        """
            parse the node of string type
        """
        print(f"[NODE]: {node.tag}")
        attrib = node.attrib
        attrib['parsed'] = 'Y'
        self.setcontent(attrib, attrib['value'])
        attrib['dtype'] = 'B'

        if (self.modified == False):
            attrib['length'] = str(len(attrib['value'])*8)

        print(f'parseString: {self.getcontent(attrib)}')
        return int(attrib['length'])


    def parseStrings(self, node):
        """
            Parse the node of strings type.
            Randomly selecting one item from the lists.
        """
        print(f"[NODE]: {node.tag}")
        attrib = node.attrib
        attrib['parsed'] = 'Y'
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


    def parseBytes(self, node):
        """
            Parse the node of Bytes type.
            Generating bytes-like data with the content of 'value', then storing these data
            into the content buffer.
        """
        print(f"[NODE]: {node.tag}")
        attrib = node.attrib
        bound = []
        num = 0
        s = attrib['value']
        attrib['dtype'] = 'B'
        attrib['parsed'] = 'Y'
        print(s)
        # parse attribute of value
        for i in range(len(s)):
            # extract the length of value
            if (s[i] == ':' and self.modified == False):
                if(s[0] == '['):
                    lower, upper = self.parseRange(s[1:])
                    num = random.randint(lower, upper)
                else:
                    num = int(s[0:i])
                attrib['length'] = str(num*8)

                if (s[i+1] != '['): 
                    bound.append([eval(s[i+1:]),eval(s[i+1:])])
                    break

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
        self.setcontent(attrib, c)
        print(f"parseBytes: generate {self.getcontent(attrib)}")
        return int(attrib['length'])


    def parseBits(self, node):
        """
            Parse the node of Bits type.
            Generating bits-like data according to the content of 'value', and do the same
            thing as parseBytes
        """
        print(f"[NODE]: {node.tag}")
        attrib = node.attrib
        bound = []
        num = 0
        s = attrib['value']
        attrib['dtype'] = 'b'
        attrib['parsed'] = 'Y'

        # extract the length of value
        for i in range(len(s)):
            if (s[i] == ':' and self.modified == False):
                if(s[0] == '['):
                    lower, upper = self.parseRange(s[1:])
                    num = random.randint(lower, upper)
                else:
                    num = int(s[0:i])
                
                attrib['length'] = str(num)
                if (s[i+1] != '['): 
                    bound.append([eval(s[i+1:]),eval(s[i+1:])])
                    break


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
        self.setcontent(attrib, c)
        print(f"parseBits: generate {self.getcontent(attrib)}")
        return int(attrib['length'])
    
    def extractArgs(self, str):
        args = []
        for i in range(len(str)): 
            if(str[i] == '['):
                j = i
                while(str[j] != ']'): j = j + 1
                args.append(str[i+1:j])

        return args
    
    def parseRef(self, node):
        """
            Parsing node of reference type.
            Invoke the function at once, then return the funcname which is specified for reference.
        """
        attrib = node.attrib
        str = attrib['value']
        attrib['parsed'] = 'Y'
        attrib['length'] = '0'
        args = [node.tag]
        funcname = ''

        for i in range(len(str)):
            if(str[i] == ':'):
                funcname = str[:i]
                print(f'parseRef: {funcname}')
                if(not hasattr(self, funcname)): raise Exception(f"Undefinde function {funcname}")
            if(str[i] == '['):
                j = i
                while(str[j] != ']'): j = j + 1
                args.append(str[i+1:j])
        
        func = self.__getattribute__(funcname)
        if(func != None):   
            ref = func(args)
            ref_node = self.data.find('.//'+ref)
            self.parse(ref_node)
            # Invoke a special function call to deal with reference.
            self.funcSeq.append('@'+funcname)
            self.argSeq['@'+funcname] = [node.tag] 
        return funcname


    def parseFunc(self, node):
        """
            Parse node of function type.
            There are some pre-defined functions, users can define function by themselves as well.
            Functions should be invoked after all nodes has been parsed. We stored the functions which haven't
            been invoked as a FuncSeq, and store their arguments in argSeq. The first argument of every node of
            argSeq must be the tag name of the node.
        """
        print(f"[NODE]: {node.tag}")
        attrib = node.attrib
        if(attrib['dtype'] == 'R'):
            return self.parseRef(node)

        attrib['parsed'] = 'Y'
        attrib['length'] = '0'
        str = attrib['value']
        args = [node.tag]
        funcname = ''

        for i in range(len(str)):
            if(str[i] == ':'):
                funcname = str[:i]
                print(f'parseFunc: {funcname}')
                if(not hasattr(self, funcname)): raise Exception(f"Undefinde function {funcname}")
                
            if(str[i] == '['):
                j = i
                while(str[j] != ']'): j = j + 1
                args.append(str[i+1:j])
        for arg in args:
            # The node which is referenced to as argument should be parsed.
            print(f' |- arg node: {arg}')     

        for arg in args:
            # The node which is referenced as argument should be parsed.
            n = self.root.find('.//'+arg)
            if(n == None): raise Exception(f"invalid argument {arg}")
            if(n != None and n.attrib['parsed'] == 'N'):     
                self.parse(n)
            

        self.funcSeq.append(funcname)
        self.argSeq[funcname] = args

        return funcname

    def addFuncname(self, root, funcname):
        attrib = root.attrib
        attrib['content'] = attrib['content'] + '[' + funcname + ']'

    def parse(self, root):
        """
            The main parser loop.
            After parsing node, the content(include value), length, dtype of normal node will be determinated.
            The function which will be invoked later as well as its arguments will be added to funcSeq.
        """
        length = 0
        
        if(root.tag == 'text' or root.attrib['ntype'] == 'set'):
            if(root.attrib['parsed'] == 'Y'): return int(root.attrib['length'])
            root.attrib['parsed'] = 'Y'
            print(f"[SET NODE]: {root.tag}")
            root.attrib['content'] = ''

            for node in root:    
                attr = node.attrib
                if(attr['parsed'] == 'Y'): 
                    length = length + int(attr['length'])
                    continue
                if attr['ntype'] == 'string':
                    length = length + self.parseString(node)
                elif attr['ntype'] == 'strings':
                    length = length + self.parseStrings(node)
                elif attr['ntype'] == 'bytes':
                    length = length + self.parseBytes(node)
                elif attr['ntype'] == 'bits':
                    length = length + self.parseBits(node)
                elif attr['ntype'] == 'function':
                    funcname = self.parseFunc(node) # the length of function couldn't be counted when parsing.
                    self.addFuncname(root, funcname)
                elif attr['ntype'] == 'set':
                    length = length + self.parse(node)
        else:    
            attr = root.attrib
            if(attr['parsed'] == 'Y'): return # single node will be parsed in advance when it is considered as argument.
            if attr['ntype'] == 'string':
                length = length + self.parseString(root)
            elif attr['ntype'] == 'strings':
                length = length + self.parseStrings(root)
            elif attr['ntype'] == 'bytes':
                length = length + self.parseBytes(root)
            elif attr['ntype'] == 'bits':
                length = length + self.parseBits(root)
            elif attr['ntype'] == 'function':
                funcname = self.parseFunc(root) # the length of function couldn't be counted when parsing.
                if(root.getparent().tag == 'text' or root.getparent().attrib['dtype'] == 'set'):
                    self.addFuncname(root.getparent(), funcname)
        root.attrib['length'] = str(length)
        return length

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
                for n in node:
                    self.dataset.append(n.tag)
            if (node.tag == 'priority'):
                self.priority = node

    def addFunction(self, name, func):
        """
            add user-defined function to smg
        """
        setattr(self, name, MethodType(func, self))

    def gen(self, f):
        """
            Concatenate the message of nodes and generate the result.
        """
        
        print("\t\t[BEGIN PARSE]")
        self.clearMark(self.text)
        self.clearMark(self.data)
        self.parse(self.text)
        self.funcinvoke(self.funcSeq, self.argSeq)
        self.modified = True
        self.text.attrib['content'] = ''

        print(f"\n\t\t[BEGIN GENERATION]\ttotal length: {self.text.attrib['length']}b")
        self.genSet(self.text, f)
        # for node in self.text:
            
        #     attrib = node.attrib
        #     ntype = attrib['ntype']
        #     if (ntype == 'set'):
        #         print(f"ENTER SET: [{node.tag}]\tset length:{attrib['length']}b")
        #         self.genSet(node, f)
        #     else:
        #         length = attrib['length']
        #         dtype = attrib['dtype']
        #         print(f"GENERATE: [{node.tag}]\tlength: {length}b")

        #         if(ntype == 'string' or ntype == 'strings'):
        #             f.write(self.getcontent(attrib).encode())
        #         elif(dtype == 'B'):
        #             f.write(self.getcontent(attrib))
        #         elif(dtype == 'b'):
        #             c = self.getcontent(attrib)
        #             self.buffer += c[2:]

        #             if(len(self.buffer) == 10):
        #                 # output bits with big-endian
        #                 f.write(eval(self.buffer).to_bytes(1,'big'))
        #                 self.buffer = '0b'
        #         elif(dtype == 'R'):
        #             pass
        
        if(len(self.buffer) != 2):
            raise Exception("Message doesn't fullfill bytes aligning")
        f.close()
        

class mqtt_gen(Smg):

    def __init__(self) -> None:
        super().__init__()

    def mqtt_map_func(self, args):
        """
            Specified function of mqtt protocol.
            Generating content of flags bits with the information of type.
        """
        src = args[1]
        dst = args[0]
        src = self.root.find('.//'+src)
        dst = self.root.find('.//'+dst)
        src_attrib = src.attrib
        dst_attrib = dst.attrib
        src_type = self.getcontent(src_attrib)
        
        src_type = eval(src_type)
        if src_type in [0x1,0x2,0x4,0x5,0x7,0x9,0xb,0xc,0xd,0xe]:
            self.setcontent(dst_attrib, '0b0000')
        elif src_type in [0x6,0x8,0xa]:
            self.setcontent(dst_attrib,'0b0010')

        dst_attrib['dtype'] = 'b'

        return 4
    
    def mqtt_length_func(self, args):
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
        self.setcontent(attrib, bytes(length_byte))
        print(f'  actual_length: {length}B')
        print(f'  mqtt_length: {length_byte}')
        attrib['dtype'] = 'B'
        return len(length_byte)*8
    
    def mqtt_vheader_ref(self,args):
        """
            Specified function of mqtt protocol.
            map variable header to message type.
        """
        vheader = self.text.find('.//' + args[0])
        types = self.text.find('.//' + args[1])
        attrib_types = types.attrib
        type = self.getcontent(attrib_types)
        map = ['reserved', 'connect', 'connack']

        mtype = map[eval(type)]
        print(f' |- ref: {mtype}')
        self.setcontent(vheader.attrib, mtype)   
        return mtype

    def ck_returncode(self, args):
        returncode = self.root.find('.//' + args[0])
        flags = self.root.find('.//' + args[1])
        if(eval(self.getcontent(flags.attrib)) == 0):
            self.setcontent(returncode.attrib, 0)
        else:
            self.setcontent(returncode.attrib, random.randint(1,5))
        
        return 8


