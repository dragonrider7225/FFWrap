from abc import ABC, abstractmethod

class HTMLDOM:
    def __init__(self, head=None, body=None):
        if head:
            self.__head = head
        else:
            self.__head = HTMLTag("head")
        if body:
            self.__body = body
        else:
            self.__body = HTMLTag("body")

    def __str__(self):
        return "<html>{}{}</html>".format(str(self.__head), self.__body)

    def __repr__(self):
        return "HTMLDOM({}, {})".format(repr(self.__head), repr(self.__body))

    def appendToHead(self, html):
        self.__head.appendChild(html)

    def appendToBody(self, html):
        self.__body.appendChild(html)

class HTMLNode(ABC):
    @abstractmethod
    def toHTML(self):
        pass

    def __str__(self):
        return self.toHTML()

class HTMLTextNode(HTMLNode):
    def __init__(self, text):
        self.__text = text

    def __repr__(self):
        return 'HTMLTextNode({})'.format(repr(self.__text))

    def toHTML(self):
        return self.__text

class HTMLStyleNode(HTMLTextNode):
    def __init__(self, tagName=None, attrName=None, attrClass=None, **kwargs):
        HTMLNode.__init__("")
        self.__selector = [tagName, attrName, attrClass]
        self.__styles = {}
        for k, v in kwargs.items():
            self.__styles[k] = v

    def __repr__(self):
        ret = "HTMLStyleNode("
        ret += "{}, {}, {}".format(*map(repr, self.__selector))
        for k, v in self.__styles.items():
            ret += ", {}={}".format(repr(k), repr(v))
        return ret + ")"

    def toHTML(self):
        ret = ""
        if self.__selector[0] != None:
            ret += str(self.__selector[0])
        if self.__selector[1] != None:
            ret += "#" + str(self.__selector[1])
        if self.__selector[2] != None:
            ret += "." + str(self.__selector[2])
        if len(ret) <= 0:
            ret = "*"
        ret += "{"
        for k, v in self.__styles.items():
            ret += "{}:{};".format(str(k), str(v))
        return ret + "}"

    def addStyle(self, key, value):
        self.__styles[key] = value
        return self

class HTMLTag(HTMLNode):
    void = ["area", "base", "br", "col", "command", "embed", "hr", "img", "input", "keygen", "link", "meta", "param", "source", "track", "wbr"]

    def __init__(self, name, *children, **attributes):
        self.__name = name
        self.__children = []
        for dt in children:
            self.appendChild(dt)
        self.__attributes = {}
        for k, v in attributes.items():
            self.addAttribute(k, v)

    def __repr__(self):
        return 'HTMLTag({}, {}, **{})'.format(repr(self.__name), repr(self.__children), repr(self.__attributes))

    def getName(self):
        return self.__name

    def getChildren(self):
        """Return the list backing this tag if this tag can have children
        """
        if self.__name in HTMLTag.void:
            return None
        return self.__children

    def toHTML(self):
        ret = "<" + str(self.__name)
        for k, v in self.__attributes.items():
            ret += " {}=\"{}\"".format(k, v)
        if self.__name in HTMLTag.void:
            ret += " />"
            return ret
        ret += ">"
        ret += self.innerHTML()
        ret += "</" + str(self.__name) + ">"
        return ret

    def innerHTML(self):
        ret = ""
        if self.__name not in HTMLTag.void:
            for c in self.__children:
                ret += c.toHTML()
        return ret

    def addAttribute(self, key, value):
        self.__attributes[key] = value
        return True

    def appendChild(self, node):
        if self.__name in HTMLTag.void:
            return False
        self.__children.append(node)
        return True

    def insertChildBefore(self, node, present):
        """If present is a child of this tag, insert node immediately before it
        Otherwise, append node to the end of this tag.
        """
        if self.__name in HTMLTag.void:
            return False
        if present not in self.__children:
            self.appendChild(node)
            return True
        self.__children.insert(self.__children.index(present), node)
        return True

    def hasChild(self, node=None):
        """If node is given, return True iff it is a child of this tag.
        Otherwise, return True iff this tag has at least one child.
        """
        if self.__name in HTMLTag.void:
            return False
        if node != None:
            return node in self.__children
        return len(self.__children) > 0

    def getFirstChild(self):
        if self.hasChild():
            return self.__children[0]
        return None

    def getLastChild(self):
        if self.hasChild():
            return self.__children[-1]
        return None

    def popFirstChild(self):
        if self.hasChild():
            ret, self.__children = self.__children[0], self.__children[1:]
            return ret
        return None

    def popLastChild(self):
        if self.hasChild():
            ret, self.__children = self.__children[-1], self.__children[:-1]
            return ret
        return None

class StyleSheet(HTMLTag):
    def __init__(self, *args, **kwargs):
        HTMLTag.__init__(self, "style", *args, **kwargs)

    def appendChild(self, node):
        if isinstance(node, HTMLStyleNode):
            HTMLTag.appendChild(self, node)

    def insertChildBefore(self, node, present):
        if isinstance(node, HTMLStyleNode):
            HTMLTag.insertChildBefore(self, node, present)
