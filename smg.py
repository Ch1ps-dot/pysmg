import random
import socket
from lxml import etree

class Smg():
    """
        Implementation of protocol generator.
        Output the protocol message according to the template as result.
    """

    def __init__(self) -> None:
        """
            Every element of template stands for a node of protocol AST.
            The attribute of the node includes name, type, value, lenth.
            - The definitions of type include:
                string: The token can not be changed.
                choice: The token is selected from a list.
                bits/bytes: The token is generated among the range given by value.
                function: Invoking special function to generate token.
            - The definition of value must obey the rules:
                string: If the type of node is string, the value is determined at parse time.
                strings: If it is choice, the choices must be seperated by '|' (e.g. 502|404|201 ). 
                range: The context of token was randomly selected from given list, and the length is determinated
                        by the prefix number (e.g. 10:[0x1-0x20][0x30-0x40]). The range of charater must be offered
                        by hex.
                function: Some token has special semantic. 
                        It can not be determined until other nodes has been parsed. 
            - The length attribute is counted at runtime
        """

        self.modified = False
        self.conent = [] # Store the content of Elements. Aiming to buffer the temporary message 
                         # in every generating process.

    def fromstring(self, src):
        self.root = etree.fromstring(src)
    
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

    def send(self, ip, port, f):
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect((ip, int(port)))
        client_socket.sendall(f.read())

    def output(self, f):
        """
            Concatenate the nodes and output the message.
        """
        buffer = '0b'
        self.parse()
        self.modified = True

        print("\n\t\t[begin out]")
        for node in self.root:
            print(f"out {node.tag}")
            attrib = node.attrib
            type = attrib['type']

            if(type == 'string' or type == 'strings'):
                f.write(self.__getcontent(attrib).encode())
            elif(type == 'bytes'):
                f.write(self.__getcontent(attrib))
            elif(type == 'bits'):
                c = self.__getcontent(attrib)
                buffer += c[2:]

                if(len(buffer) == 10):
                    f.write(eval(buffer).to_bytes(1,'big'))
                    buffer = '0b'
        

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
                num = int(s[0:i])
                attrib['length'] = str(num)

            # extract the range of byte
            if (s[i] == '['):
                j = i
                while s[j] != '-': j = j + 1
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
                num = int(s[0:i])
                attrib['length'] = str(num)

            # extract the range of byte
            if (s[i] == '['):
                j = i
                while s[j] != '-': j = j + 1
                lower = eval(s[i+1:j])
                i = j
                while s[j] != ']': j = j + 1
                upper = eval(s[i+1:j])
                bound.append([lower, upper])
        
        # generate content of value    
        r = bound[random.randint(0,len(bound)-1)]
        c = random.randint(r[0],r[1])
        c = bin(c) # translate int to bin

        self.__setcontent(attrib, c)
        print(f"parseBits: generate {self.__getcontent(attrib)}")
        

    def __parseFunc(self):
        pass


    def parse(self):
        for node in self.root:
            print(f"tag name: {node.tag}")
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
                self.__parseFunc()

    def __charCount(self):
        pass

    def __bitCount(self):
        pass

    def __byteCount(self):
        pass

    def __checkSum(self):
        pass

    def __valueCount(self):
        pass

    


