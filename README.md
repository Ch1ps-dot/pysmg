# Simple Message Generator

SMG是一个使用python实现的简单报文生成器，可以用于批量生成符合给定规范的二进制数据。它使用XML描述给定文件的格式规范，通过XML的层次结构对文本的字段进行划分，用节点属性指定生成文本的类别、内容和关系，并能够按照调用关系和优先级顺序处理具有语义的特殊文本段。凭借以上特性，SMG可以被用于自动化生成例如协议报文等具有特定格式、字段间有约束关系、字段本身具有特殊语义的文本。

# Usage

SMG的主体是smg.py文件中的Smg类，其中包含了处理指定XML格式文件的基本框架。通过继承Smg类和提供处理特定文本节点语义的函数，SMG可以被扩展用于各类文本的生成。