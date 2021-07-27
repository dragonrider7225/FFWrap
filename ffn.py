import base64
from base64 import b64encode as enc

from html.parser import HTMLParser

from htmldom import HTMLTag, HTMLTextNode, HTMLDOM, StyleSheet, HTMLStyleNode

from style import *

import urllib.request
from urllib.request import Request, urlopen

def loadFFN(story, chapter=0):
    if chapter == 0:
        return # TODO: load story details
    url = "https://www.fanfiction.net/s/{}/{}".format(story, chapter)
    # Request `url1' as if to embed in page `url2'
    # req = Request(url1, headers={"referer": url2})
    page = str(urllib.request.urlopen(url).read())
    parser = FFNParser()
    return parser.getReplacement(page, url)

class FFNParser(HTMLParser):
    def __init__(self, *args, **kwargs):
        HTMLParser.__init__(self, *args, **kwargs)

    def reset(self):
        HTMLParser.reset(self)
        self.__title = None
        self.__fandom = None
        self.__coverSmall = None
        self.__coverLarge = None
        self.__sTitle = None
        self.__cTitle = None
        self.__author = None
        self.__desc = None
        self.__rating = None

    @staticmethod
    def fixSplitAttribute(attrs, attrName):
        # Index of the kv pair that actually contains the attrName
        mindex = -1
        # Index of last kv pair that is part of attrName
        maxdex = -1
        for i in range(len(attrs)):
            if attrs[i][0] == attrName:
                # attrName was not split
                if attrs[i][1][-1] == "'":
                    return attrs
                mindex = i
                maxdex = i
                attrs[i] = list(attrs[i])
                continue
            if mindex >= 0:
                maxdex = i
                # Add space if next subject of append is not just closing quote
                if attrs[i][0] != "\\'":
                    attrs[mindex][1] += " "
                attrs[mindex][1] += attrs[i][0]
                # If closing quote found, stop looking
                if attrs[i][0].endswith("\\'"):
                    break
        # Remove "attributes" that are actually part of the attribute to be fixed
        for i in range(mindex, maxdex):
            del attrs[mindex + 1]
        # Fix un-tupled attribute
        if mindex >= 0:
            attrs[mindex] = tuple(attrs[mindex])
        return attrs

    @staticmethod
    def fixSplitAttributes(attrs):
        names = []
        for k, v in attrs:
            if v != None and v[:2] == "\\'" and v[-1] != "'":
                names.append(k)
        for name in names:
            FFNParser.fixSplitAttribute(attrs, name)
        return attrs

    @staticmethod
    def unquoteAttributes(attrs):
        for i in range(len(attrs)):
            if attrs[i][1] == None:
                continue
            if attrs[i][1][:2] == "\\'" and attrs[i][1][-2:] == "\\'":
                v = attrs[i][1][2:-2]
                attrs[i] = (attrs[i][0], v if len(v) else None)
        return attrs

    @staticmethod
    def fixDomains(attrs):
        for i in range(len(attrs)):
            attr = attrs[i]
            if attr[1] == None:
                continue
            if attr[1][0] == "/" and (len(attr[1]) == 1 or attr[1][1] != "/"):
                attrs[i] = (attr[0], "//www.fanfiction.net" + attr[1])
        return attrs

    @staticmethod
    def fixAttrs(attrs):
        # HTMLParser splits on space regardless of whether that space is part of a class or style string
        FFNParser.fixSplitAttributes(attrs)
        # HTMLParser escapes quotes around attributes
        FFNParser.unquoteAttributes(attrs)
        # Files from the current domain can be referenced with just their (UNIX-style) path
        FFNParser.fixDomains(attrs)
        return attrs

    def handle_starttag(self, tag, attrs):
        attrs = dict(FFNParser.fixAttrs(attrs))
        if self.__title == None and tag.lower() == "title":
            self.__title = 1
            return
        if self.__fandom == None and tag.lower() == "div":
            if "id" in attrs.keys() and attrs["id"] == "pre_story_links":
                self.__fandom = "psl"
                return
        if self.__fandom == "psl" and tag.lower() == "a":
            self.__fandom = "tll"
            return
        if self.__fandom == "tll" and tag.lower() == "a":
            self.__fandom = [attrs["href"]]
            return
        if self.__coverLarge == None and tag.lower() == "img":
            # Build original tag
            # self.__coverLarge = "<img"
            # for k, v in attrs:
            #     self.__coverLarge += " {}=\"{}\"".format(k, v)
            # self.__coverLarge += ">"
            self.__coverLarge = dict(attrs)["data-original"]
            if self.__coverLarge[:2] == "//":
                self.__coverLarge = "https:" + self.__coverLarge
            elif self.__coverLarge[0] == "/":
                self.__coverLarge = "https://www.fanfiction.net" + self.__coverLarge
            return
        if self.__coverSmall == None and tag.lower() == "img":
            # Build original tag
            # self.__coverSmall = "<img"
            # for k, v in attrs:
            #     self.__coverSmall += " {}=\"{}\"".format(k, v)
            # self.__coverSmall += ">"
            self.__coverSmall = dict(attrs)["src"]
            if self.__coverSmall[:2] == "//":
                self.__coverSmall = "https:" + self.__coverSmall
            elif self.__coverSmall[0] == "/":
                self.__coverSmall = "https://www.fanfiction.net" + self.__coverSmall
            return
        if self.__coverSmall != None and tag.lower() == "b":
            self.__sTitle = 1
            return
        if "href" in attrs.keys() and attrs["href"][20:23].lower() == "/u/":
            self.__author = [attrs["href"]]
            return
        if self.__author != None and len(self.__author) == 2:
            if self.__desc == None and tag.lower() == "div":
                if "class" in attrs.keys() and "xcontrast_txt" in attrs["class"].split():
                    self.__desc = 1
                    return
        if self.__desc != None and tag.lower() == "a":
            if self.__rating == None:
                self.__rating = 1
                return

    def handle_endtag(self, tag):
        pass

    def handle_data(self, data):
        if self.__title == 1:
            # Remove " fanfic | FanFiction" from the end of the page title
            self.__title = data[:-20]
            return
        if self.__fandom != None and self.__fandom[0].startswith("/"):
            self.__fandom.append(data)
            self.__fandom = ["tld"] + self.__fandom
            self.__title = self.__title[:-(len(data) + 4)]
            return
        if self.__sTitle == 1: # data argument contains story title
            # Remove story title from __title field
            self.__title = self.__title[len(data) + 1:]
            # __title is of the form "Chapter [1-9][0-9]*: .+"
            if self.__title.find(":") > -1:
                chNum = int(self.__title[8:self.__title.find(":")])
                self.__title = self.__title[self.__title.find(":") + 2:]
            # __title is of the form "Chapter [1-9][0-9]*"
            elif len(self.__title) > 0:
                chNum = int(self.__title[self.__title.rfind(" "):])
                self.__title = ""
            else:
                chNum = 1
            if self.__title.lower()[:8] == "chapter ":
                s = self.__title[8:]
                s = s[:s.find(" ")]
                if s.isnumeric():
                    chNum = int(s)
                    self.__title = self.__title[:8 + len(s)]
            cTitle = self.__title
            self.__title = "{}, Chapter {}".format(data, chNum)
            if len(cTitle) > 0:
                self.__title += ": {}".format(cTitle)
            self.__sTitle = data
            return
        if self.__author != None and len(self.__author) == 1:
            self.__author.append(data)
            return
        if self.__desc == 1:
            self.__desc = bytes(data, "utf-8").decode("unicode_escape")
            return
        if self.__rating == 1:
            self.__rating = data.split()[-1]
            return

    def getReplacement(self, origin, url):
        self.reset()
        self.feed(origin)
        print(self.__title)
        ret = HTMLDOM()
        ret.appendToHead(HTMLTag("title", HTMLTextNode(self.__title)))
        style = StyleSheet()
        bodyStyle = HTMLStyleNode("body").addStyle("background-color", BACKGROUND_COLOR)
        style.appendChild(bodyStyle)
        coverlStyle = HTMLStyleNode("img", "coverLarge")
        coverlStyle.addStyle("opacity", "0.5")
        coverlStyle.addStyle("border-radius", COVER_FRAME_RADIUS)
        style.appendChild(coverlStyle)
        headerBoxStyle = HTMLStyleNode("div", "headerContainer")
        headerBoxStyle.addStyle("color", HEADER_TEXT_COLOR)
        headerBoxStyle.addStyle("background-color", HEADER_COLOR)
        headerBoxStyle.addStyle("padding", "{} {}".format(HEADER_BOX_VPADDING, HEADER_BOX_HPADDING))
        style.appendChild(headerBoxStyle)
        headerStyle = HTMLStyleNode("div", "header")
        headerStyle.addStyle("display", HEADER_DISPLAY)
        headerStyle.addStyle("min-height", HEADER_HEIGHT)
        headerStyle.addStyle("max-height", HEADER_HEIGHT)
        headerStyle.addStyle("max-width", HEADER_WIDTH)
        headerStyle.addStyle("margin", HEADER_MARGIN)
        style.appendChild(headerStyle)
        coverFrameStyle = HTMLStyleNode("div", "coverFrame")
        coverFrameStyle.addStyle("position", COVER_FRAME_POSITION)
        coverFrameStyle.addStyle("background", BACKGROUND_COLOR)
        coverFrameStyle.addStyle("border-radius", COVER_FRAME_RADIUS)
        coverFrameStyle.addStyle("max-width", COVER_WIDTH)
        coverFrameStyle.addStyle("max-height", COVER_HEIGHT)
        style.appendChild(coverFrameStyle)
        coversStyle = HTMLStyleNode("img", "coverSmall")
        coversStyle.addStyle("position", COVER_S_POSITION)
        coversStyle.addStyle("left", COVER_S_LEFT)
        coversStyle.addStyle("top", COVER_S_TOP)
        style.appendChild(coversStyle)
        infoBoxStyle = HTMLStyleNode("div", "infobox")
        infoBoxStyle.addStyle("padding-left", INFOBOX_PADDING_LEFT)
        style.appendChild(infoBoxStyle)
        titleBoxStyle = HTMLStyleNode("div", "titlebox")
        titleBoxStyle.addStyle("display", TITLEBOX_DISPLAY)
        titleBoxStyle.addStyle("padding-right", TITLEBOX_PADDING_RIGHT)
        style.appendChild(titleBoxStyle)
        titleStyle = HTMLStyleNode("h1", "title")
        titleStyle.addStyle("margin-bottom", TITLE_MARGIN_BOTTOM)
        titleStyle.addStyle("margin-top", TITLE_MARGIN_TOP)
        style.appendChild(titleStyle)
        authorBoxStyle = HTMLStyleNode("div", "authorbox")
        authorBoxStyle.addStyle("display", AUTHORBOX_DISPLAY)
        style.appendChild(authorBoxStyle)
        authorStyle = HTMLStyleNode("h2", "author")
        authorStyle.addStyle("margin-top", AUTHOR_MARGIN_TOP)
        style.appendChild(authorStyle)
        ret.appendToHead(style)
        headerContainer = HTMLTag("div", id="headerContainer")
        storyHeader = HTMLTag("div", id="header")
        coverFrame = HTMLTag("div", id="coverFrame")
        coverlReq = Request(self.__coverLarge, headers={"referer": url})
        coverlb64 = B64DATA_PREFIX + enc(urlopen(coverlReq).read()).decode("utf-8")
        coverlTag = HTMLTag("img", [], src=coverlb64, id="coverLarge")
        coverFrame.appendChild(coverlTag)
        coversReq = Request(self.__coverSmall, headers={"referer": url})
        coversb64 = B64DATA_PREFIX + enc(urlopen(coversReq).read()).decode("utf-8")
        coversTag = HTMLTag("img", [], src=coversb64, id="coverSmall")
        coverFrame.appendChild(coversTag)
        storyHeader.appendChild(coverFrame)
        infoBox = HTMLTag("div", id="infobox")
        titleBox = HTMLTag("div", id="titlebox")
        titleHeading = HTMLTag("h1", HTMLTextNode(self.__sTitle), id="title")
        titleBox.appendChild(titleHeading)
        infoBox.appendChild(titleBox)
        authorBox = HTMLTag("div", id="authorbox")
        authorHeading = HTMLTag("h2", id="author")
        authorLink = HTMLTag("a", href=self.__author[0])
        authorLink.appendChild(HTMLTextNode(self.__author[1]))
        authorHeading.appendChild(authorLink)
        authorBox.appendChild(authorHeading)
        infoBox.appendChild(authorBox)
        descBox = HTMLTag("div", id="descbox")
        descBox.appendChild(HTMLTextNode(self.__desc))
        infoBox.appendChild(descBox)
        storyHeader.appendChild(infoBox)
        headerContainer.appendChild(storyHeader)
        ret.appendToBody(headerContainer)
        return ret

def testFFN():
    # Test fanfiction.net parser on a story with only one chapter
    with open("ffnTestSingleton.html", "w+") as fout:
        fout.write(str(loadFFN(12920816, 1)))
    # Test fanfiction.net parser on a story with multiple unnamed chapters
    with open("ffnTestMulti.html", "w+") as fout:
        fout.write(str(loadFFN(12472897, 1)))
    # Test fanfiction.net parser on a story with multiple named chapters
    with open("ffnTestMultiName.html", "w+") as fout:
        fout.write(str(loadFFN(12919509, 1)))
