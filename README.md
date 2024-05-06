# Simple Message Generator

SMG是一个使用python实现的简单报文生成器，可以用于批量生成符合特定描述的二进制数据。它使用一种易于理解的网络协议元语言SML来描述文本的格式规范。在具体实现上，它通过XML表示SML的实际结构，使用XML中的层次结构对文本的字段进行划分，用节点属性指定生成文本的类别、内容和关系，并能够按照依赖关系和优先级顺序处理具有特殊语义的文本段。凭借以上特性，SMG可以被用于自动化生成例如协议报文等具有特定格式、字段间有约束关系、字段内容具有特殊语义的文本。

# Simple Message Language

网络协议都有严格的格式规范和字段限制，而诸如报文长度、校验和等特殊报文字段的生成又依赖于其他字段信息，所以如何描述协议的格式规范和依赖关系对指导协议报文的生成起着关键作用。SMG提供了一种用于描述协议报文规范的网络协议元语言SML。和其他上下文无关文法类似，它由一系列派生规则组成。为了能够更好地描述报文中字段长度、字段内容和字段间依赖关系等信息，SML中还定义了用于特殊生成规则的操作语义。

## Overview

SML的语法规范如下：

```bash
<message> ::=<group>*
<group> ::=<field>* 
<field> ::= <string> | gen(length, limit, type) | function(arg...)
<string> ::= a list of visible character
<length> ::= the length of field
<value> ::= the limitation of value within field
<type> ::= bits | bytes | string
<arg> ::= dependent field | dependent group
```

任何报文都是由许多字段组组成的，而字段组则由各种字段组成。接下来是对不同字段所表示信息的详细描述：

- string：string代表的字面值是报文中常见的字段，例如http协议中的版本号和做为协议标识符的HTTP，MQTT中connect报文中的MQTT等。这些字段在生成报文时不会随其他字段信息改变、不需要随机生成且能够用可见字符表示，所以可以直接用字符串表示。

### Operational Semantic

除了固定的字面值字符串，SML中还有几个具有特殊语义的字段，其操作语义的表述遵从以下规则，Operation表示采用的操作，conditions表示生成需要的条件信息，generation表示生成的结果。
```math
Operation:\frac{conditions}{generation}
```
SML的语义规则如下：
```math
Gen:{\frac{\<length>,\<value>,\<type\>}{generation}}
\\
Func:{\frac{\<specified-function>,\<arguments>...}{computation\space result}}
```

- gen(length, value, type)：gen()表示的是一个被生成规则限制的字段，限制信息包括由length指定的字段的长度范围，由value指定的字段内字符数值范围，由type指定的字段的具体种类。其中type可以分为bits、bytes、string三种，bits指明生成的信息为由0或1表示的比特，bytes指明生成的信息是由字节组成，string指明生成的信息是一个字符串。
- function(arg...)：function()处理的是协议中的一类特殊字段，这些字段内容生成往往依赖于其他字段的内容，例如校验和、计算其他字段的长度、用于标识报文类别的标志位等。这些字段的内容无法在描述报文规范时确定，甚至还需要采用复杂的生成规则（比如计算校验和）。因此针对不同的报文需求，需要提供不同的处理函数。

## XML Script of SML

SML是通过XML来实现实际功能的（如果从头到尾写一个语言解析器有点太麻烦了...）。XML提供了层次化的节点结构和充足的自定义功能，借助XML和python中的XML解析库lxml，我们可以很方便地设计并实现SML的解析脚本和基于解析结果的报文生成器。

### Writing SML

下面是MQTT中connect和connack报文的SML脚本。

```XML
<SMG>
    <text>
        <sheader ntype="set">
            <types ntype="bits" dtype='b' value="4:1"/>
            <flags ntype="function" dtype="U" value="mqtt_map_func:[types]"/>
            <rlength ntype="function" dtype="U" value="mqtt_length_func:[vheader]"/>
        </sheader>
        <vheader ntype="function" dtype="R" value="mqtt_vheader_ref:[types]"/>
    </text>
    <data>
        <connect ntype="set">
            <ct_protocol_name ntype="set">
                <lmsb ntype="bytes" dtype="B" value="1:0x0"/>
                <llsb ntype="bytes" dtype="B" value="1:0x4"/>
                <mqttflag ntype="string" dtype="B" value="MQTT"/>
            </ct_protocol_name>
            <ct_protocol_level ntype="bytes" dtype="B" value="1:0x4"/>
            <ct_connect_flag ntype="bits" dtype="b" value="8:0b100"/>
            <ct_keep_alive ntype="bytes" dtype="B" value="2:[0x0~0xff]"/>
            <ct_connect_payload ntype="set">
            </ct_connect_payload>
        </connect>
        <connack ntype="set">
            <ck_protocol_name ntype="set">
                <ck_lmsb ntype="bytes" dtype="B" value="1:0x0"/>
                <ck_llsb ntype="bytes" dtype="B" value="1:0x4"/>
            </ck_protocol_name>
            <ck_protocol_level ntype="bytes" dtype="B" value="1:0x4"/>
            <ck_flags ntype="bits" dtype="b" value="8:[0~1]"/>
            <ck_returncode ntype="function" dtype="U" value="ck_returncode:[ck_flags]"/>
        </connack>
      </data>
</SMG>
```



### Structure

在结构上，SML文件以\<SMG\>作为顶层节点，指明该XML文件表示的是用于SMG的SML文件。在\<SMG\>下是两个子节点\<text\>和\<data\>，text节点下就是SML的实际结构，SML中的每个字段和组都可以对应于text中的节点。而data中存储了可以被text中节点使用的数据。data节点的存在是为了提高脚本的复用性，例如在MQTT协议中，不同种类的报文虽然拥有相同的固定报头，但是在可变头和载荷的结构上有很大的不同。所以在描述MQTT的SML结构时，我们可以让不同种类的报文共享相同的固定头，把不同的报文结构放在data节点下，在报文生成的过程中根据报文种类的不同动态解析和使用data中的部分。

### Node

节点中的ntype属性代表的就是SML中字段或者组的类别，其中set表示\<group>，string代表\<string>，bits和bytes表示这个字段需要使用gen操作，function表示这个字段需要使用function操作。dtype属性表示该字段的数据类型，这主要是为了区分byte和bit类型的数据在实际生成中的问题，在gen操作中也可以不标明（因为其实ntype就已经表示了该节点的数据类型）。而在function操作中，dtype可以分为U和R两种，U表示该function所在节点的内容是自己生成的，R表示该function所在节点其实是对其他节点的引用。例如在下面的脚本中，\<flags>节点只需要根据\<types>节点的值计算标志位的值，所以其dtype为U。而\<vheader>需要根据\<types>的值从\<data>中引用对应的节点作为该节点的内容，所以其dtype为R。

### value

SML中每个字段的具体内容由其value属性指定。

string字段的value只需要指明需要生成的字符内容即可。

```XML
string
```

strings字段表示生成的string可以从几个备选项中随机选取。

```
option1 | option2 | option3 | ...
```

bits/bytes字段的value结构如下，分号前的部分表示该字段的长度范围，分号后的内容表示字段内字符的ASCII码大小范围，而数值的大小可以用十六进制、十进制、二进制表示。

```xml
([least_length~max_length] | fixed_length ) : ([lower_bound~upper_bound] | fixed_value)
```

function字段由函数名和参数组成，函数指定处理节点需要调用的函数（这些函数需要由使用者自己实现），而参数指定了函数计算过程中需要使用的节点。

```
function_name:[arg1][arg2]...
```

### function

与普通字段不同，函数计算的内容通常无法在脚本编写时确定，因此需要通过提供特殊的处理函数来产生字段内容。函数的具体实现由使用者自己完成，对普通function来说必须在函数中设定节点的内容、数据类型dtype并把内容的长度作为函数的返回值。对引用function来说，必须在函数中设定引用的节点名字，并以该节点的名字作为返回值。
