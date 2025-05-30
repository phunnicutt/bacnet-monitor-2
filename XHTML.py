#!/usr/bin/python

"""
XHTML
"""

# Python 3 compatibility - string functions
# replace old 'from string import join, replace' with Python 3 compatible code
import types
from typing import Any, Dict, List, Optional, Set, Tuple, Union, TypeVar, Callable, cast, Type, Sequence, IO

import XML

# join is now a method on strings
def join(items: List[str], sep: str = '') -> str:
    return sep.join(items)

# replace is now a method on strings, but we'll define it for compatibility
def replace(s: str, old: str, new: str) -> str:
    return s.replace(old, new)

_coreattrs = {'id': 1, 'class': 1, 'style': 1, 'title': 1}
_coretranslations = {'id_':'id', 'class_':'class', 'type_':'type'}

_i18n = {'lang': 1, 'dir': 1}
_intrinsic_events = {'onload': 1, 'onunload': 1, 'onclick': 1,
                    'ondblclick': 1, 'onmousedown': 1, 'onmouseup': 1,
                    'onmouseover': 1, 'onmousemove': 1, 'onmouseout': 1,
                    'onfocus': 1, 'onblur': 1, 'onkeypress': 1,
                    'onkeydown': 1, 'onkeyup': 1, 'onsubmit': 1,
                    'onreset': 1, 'onselect': 1, 'onchange': 1 }

_attrs = XML._coreattrs.copy()
_attrs.update(_coreattrs)
_attrs.update(_i18n)
_attrs.update(_intrinsic_events)

_translations = XML._translations.copy()
_translations.update(_coretranslations)

_alternate_text = {'alt': 1}
_image_maps = {'shape': 1, 'coords': 1}
_anchor_reference = {'href': 1}
_target_frame_info = {'target': 1}
_tabbing_navigation = {'tabindex': 1}
_access_keys = {'accesskey': 1}

_tabbing_and_access = _tabbing_navigation.copy()
_tabbing_and_access.update(_access_keys)

_visual_presentation = {'height': 1, 'width': 1, 'border': 1, 'align': 1,
                       'hspace': 1, 'vspace': 1}

_cellhalign = {'align': 1, 'char': 1, 'charoff': 1}
_cellvalign = {'valign': 1}

_font_modifiers = {'size': 1, 'color': 1, 'face': 1}

_links_and_anchors = {'href': 1, 'hreflang': 1, 'type': 1, 'rel': 1, 'rev': 1}
_borders_and_rules = {'frame': 1, 'rules': 1, 'border': 1}

class CommonElement(XML.Element):

    attlist = _attrs
    attr_translations = _translations

class PCElement(XML.PrettyTagsMixIn,CommonElement): pass

#----------------------------------------------------------------------

class A(CommonElement):
    
    attlist = [{'charset': 1}]
    attlist.append(CommonElement.attlist)
    attlist.append(_links_and_anchors)
    attlist.append(_image_maps)
    attlist.append(_target_frame_info)
    attlist.append(_tabbing_and_access)

class ABBR(CommonElement): pass
class ACRONYM(CommonElement): pass
class CITE(CommonElement): pass
class CODE(CommonElement): pass
class DFN(CommonElement): pass
class EM(CommonElement): pass
class KBD(CommonElement): pass
class PRE(CommonElement): pass
class SAMP(CommonElement): pass
class STRONG(CommonElement): pass
class VAR(CommonElement): pass
class ADDRESS(CommonElement): pass
class B(CommonElement): pass
class BIG(CommonElement): pass
class I(CommonElement): pass
class S(CommonElement): pass
class SMALL(CommonElement): pass
class STRIKE(CommonElement): pass
class TT(CommonElement): pass
class U(CommonElement): pass
class SUB(CommonElement): pass
class SUP(CommonElement): pass
 
class DD(PCElement): pass
class DL(PCElement): pass
class DT(PCElement): pass
class NOFRAMES(PCElement): pass
class NOSCRIPTS(PCElement): pass
class P(PCElement): pass

class AREA(PCElement):

    attlist = [{'nohref': 0}]
    attlist.append(PCElement.attlist)
    attlist.append(_image_maps)
    attlist.append(_anchor_reference)
    attlist.append(_tabbing_and_access)
    attlist.append(_alternate_text)

class MAP(AREA): pass

class BASE(PCElement):

    attlist = [_anchor_reference,_target_frame_info]
    content_model = None

class BDO(XML.Element):

    attlist = [_coreattrs,_i18n]

class BLOCKQUOTE(CommonElement):

    attlist = [{'cite': 1}]
    attlist.append(CommonElement.attlist)

class Q(BLOCKQUOTE): pass

class BR(PCElement):

    attlist = _coreattrs
    content_model = None

class BUTTON(CommonElement):

    attlist = [{'value': 1, 'type': 1, 'disabled': 0}]
    attlist.append(CommonElement.attlist)
    attlist.append(_tabbing_and_access)

class CAPTION(CommonElement):

    attlist = [{'align': 1}]
    attlist.append(_attrs)

class COLGROUP(PCElement):

    attlist = [{'span': 1, 'width': 1}]
    attlist.append(PCElement.attlist)
    attlist.append(_cellhalign)
    attlist.append(_cellvalign)

class COL(COLGROUP):

    content_model = None

class DEL(CommonElement):

    attlist = [{'cite': 1, 'datetime': 1}]
    attlist.append(_attrs)

class INS(DEL): pass

class FIELDSET(PCElement): pass

class LEGEND(PCElement):
    
    attlist = [{'align': 1}]
    attlist.append(PCElement.attlist)
    attlist.append(_access_keys)

class BASEFONT(CommonElement):

    attlist = [{'id': 1}]
    attlist.append(_font_modifiers)
    content_model = None

class FONT(CommonElement):

    attlist = [_font_modifiers,_coreattrs,_i18n]

class FORM(PCElement):

    attlist = [{'action': 1, 'method': 1, 'enctype': 1, 'accept_charset': 1,
        'target': 1, 'autocomplete': 1, 'onsubmit': 1, 'name': 1, 'onreset': 1}]
    attlist.append(PCElement.attlist)

class FRAME(PCElement):

    attlist = [{'longdesc': 1, 'src': 1, 'frameborder': 1,
               'marginwidth': 1, 'marginheight': 1, 'noresize': 0,
               'scrolling': 1}]
    attlist.append(_coreattrs)
    content_model = None

class FRAMESET(PCElement):

    attlist = [{'rows': 1, 'cols': 1, 'border': 1}]
    attlist.append(_coreattrs)
    attlist.append(_intrinsic_events)

class Heading(PCElement):

    attlist = [{'align': 1}]
    attlist.append(_attrs)

    def __init__(self, level: int, *content: Any, **attr: Any) -> None:
        self.name = "h%d" % level
        PCElement.__init__(self, *content, **attr)

class HEAD(PCElement):

    attlist = [{'profile': 1}]
    attlist.append(_i18n)

class HR(CommonElement):

    attlist = [{'align': 1, 'noshade': 0, 'size': 1, 'width': 1}]
    attlist.append(_coreattrs)
    attlist.append(_intrinsic_events)
    content_model = None

class HTML(PCElement):

    attlist = _i18n

class TITLE(HTML): pass

class BODY(PCElement):

    attlist = [{'background': 1, 'text': 1, 'link': 1, 'vlink': 1, 'alink': 1,
               'bgcolor': 1}]
    attlist.append(PCElement.attlist)

class IFRAME(PCElement):

    attlist = [{'longdesc': 1, 'src': 1, 'frameborder': 1,
               'marginwidth': 1, 'marginheight': 1, 'scrolling': 1, 
               'align': 1, 'height': 1, 'width': 1}]
    attlist.append(_coreattrs)

class IMG(CommonElement):

    attlist = [{'src': 1, 'longdesc': 1, 'usemap': 1, 'ismap': 0}]
    attlist.append(PCElement.attlist)
    attlist.append(_visual_presentation)
    attlist.append(_alternate_text)
    content_model = None

class INPUT(CommonElement):

    attlist = [{'name': 1, 'type': 1, 'value': 1, 'checked': 0, 'disabled': 0,
               'readonly': 0, 'size': 1, 'maxlength': 1, 'src': 1,
               'usemap': 1, 'accept': 1, 'border': 1}]
    attlist.append(CommonElement.attlist)
    attlist.append(_tabbing_and_access)
    attlist.append(_alternate_text)
    content_model = None

class LABEL(CommonElement):

    attlist = [{'for': 1}]
    attlist.append(CommonElement.attlist)
    attlist.append(_access_keys)
    attr_translations = {'for_': 'for'}
    attr_translations.update(CommonElement.attr_translations)

class UL(PCElement):
    
    attlist = [{'compact': 0}]
    attlist.append(PCElement.attlist)

class OL(PCElement):

    attlist = [{'compact': 0}, {'start': 1}]
    attlist.append(PCElement.attlist)

class LI(UL):

    attlist = [{'value': 1, 'type': 1}]
    attlist.append(UL.attlist)

class LINK(PCElement):

    attlist = [{'charset': 1, 'media': 1}]
    attlist.append(PCElement.attlist)
    attlist.append(_links_and_anchors)
    content_model = None

class META(PCElement):

    attlist = [{'http-equiv': 1, 'content': 1, 'scheme': 1, 'name': 1}]
    attlist.append(_i18n)
    content_model = None

class OBJECT(PCElement):

    attlist = [{'declare': 0, 'classid': 1, 'codebase': 1, 'data': 1,
               'type': 1, 'codetype': 1, 'archive': 1, 'standby': 1,
               'height': 1, 'width': 1, 'usemap': 1, 'name': 1, 'tabindex': 1,
               'align': 1, 'border': 1, 'hspace': 1, 'vspace': 1}]
    attlist.append(PCElement.attlist)

class EMBED(PCElement):

    attlist = [{'src': 1, 'type': 1, 'pluginspace': 1, 'pluginurl': 1,
               'align': 1, 'width': 1, 'height': 1, 'units': 1, 'border': 1,
               'frameborder': 1, 'hidden': 1, 'autostart': 1, 'loop': 1,
               'volume': 1, 'controls': 1, 'controller': 1, 'mastersound': 1,
               'starttime': 1, 'endtime': 1}]
    attlist.append(PCElement.attlist)

class SELECT(PCElement):

    attlist = [{'name': 1, 'size': 1, 'multiple': 0, 'disabled': 0, 'onChange': 1}]
    attlist.append(PCElement.attlist)
    attlist.append(_tabbing_and_access)

class OPTGROUP(PCElement):

    attlist = [{'disabled': 0, 'label': 1}]
    attlist.append(PCElement.attlist)

class OPTION(OPTGROUP):

    attlist = [{'value': 1, 'selected': 0}]
    attlist.append(OPTGROUP.attlist)

class PARAM(CommonElement):

    attlist = [{'id': 1, 'value': 1, 'valuetype': 1, 'type': 1}]
    content_model = None

class SCRIPT(CommonElement):

    _quoted = False
    attlist = [{'charset': 1, 'type': 1, 'src': 1, 'defer': 0}]
    attlist.append(CommonElement.attlist)

class SPAN(CommonElement):

    attlist = [{'align': 1}]
    attlist.append(CommonElement.attlist)

class DIV(PCElement):

    attlist = [{'align': 1}]
    attlist.append(PCElement.attlist)

class STYLE(PCElement):

    attlist = [{'src': 1, 'type': 1, 'media': 1, 'title': 1}]
    attlist.append(PCElement.attlist)

class TABLE(PCElement):

    attlist = [{'cellspacing': 1, 'cellpadding': 1, 'summary': 1, 'align': 1,
               'bgcolor': 1, 'width': 1, 'cols': 1}]
    attlist.append(PCElement.attlist)
    attlist.append(_borders_and_rules)

class TBODY(PCElement):

    attlist = [CommonElement.attlist,_cellhalign,_cellvalign]

class THEAD(TBODY): pass
class TFOOT(TBODY): pass
class TR(TBODY): pass

class TH(TBODY):

    attlist = [{'abbv': 1, 'axis': 1, 'headers': 1, 'scope': 1,
               'rowspan': 1, 'colspan': 1, 'nowrap': 0, 'bgcolor': 1, 'width': 1,
               'height': 1}]
    attlist.append(TBODY.attlist)

class TD(TH): pass

class TEXTAREA(CommonElement):

    attlist = [{'name': 1, 'rows': 1, 'cols': 1, 'disabled': 0, 'readonly': 0, 'wrap': 0}]
    attlist.append(CommonElement.attlist)
    attlist.append(_tabbing_and_access)

def CENTER(*content: Any, **attr: Any) -> DIV:
    div = DIV(*content, **attr)
    divStyle = div.get('style', '')
    if divStyle:
        divStyle += '; text-align: center'
    else:
        divStyle = 'text-align: center'
    div['style'] = divStyle
    return div

class CSSRule(PCElement):

    attlist = [{'font': 1, 'font_family': 1, 'font_face': 1, 'font_size': 1,
               'border': 1, 'border_width': 1, 'color': 1,
               'background': 1, 'background_color': 1, 'background_image': 1,
               'text_align': 1, 'text_decoration': 1, 'text_indent': 1,
               'line_height': 1, 'margin_left': 1, 'margin_right': 1,
               'clear': 1, 'list_style_type': 1}]
    content = []
    content_model = None

    def __init__(self, selector: str, **decl: Any) -> None:
        self.dict = {}
        self.update(decl)
        self.name = selector

    start_tag_string = "%s { %s }"

    def start_tag(self) -> str:
        a = self.str_attribute_list()
        return self.start_tag_string % (self.name, a)

    def str_attribute(self, k: str) -> str:
        k2 = k.replace('_', '-')
        return "%s: %s" % (k2, self.dict[k])

    def str_attribute_list(self) -> str:
        return join(list(map(self.str_attribute, list(self.dict.keys()))), '; ')

    def update(self, d: Dict[str, Any]) -> None:
        for k, v in list(d.items()):
            self.dict[k] = v

def URL(*args: str, **kwargs: Any) -> str:
    uri = args[0]
    if (len(args) > 1):
        uri += '?' + urlencode(args[1:])
    if kwargs:
        # urllib expects a dictionary
        if (len(args) > 1):
            uri += '&' + urlencode(kwargs)
        else:
            uri += '?' + urlencode(kwargs)
    return uri

def Options(options: List[Tuple[str, str]], selected: List[str] = [], **attrs: Any) -> List[OPTION]:
    opts = []
    for i in options:
        if (len(i) == 2):
            key, value = i
        else:
            key, value = i[0], i[0]
        o = OPTION(value, value=key)
        if key in selected:
            o['selected'] = 1
        opts.append(o)
    return opts

def Select(options: List[Tuple[str, str]], selected: List[str] = [], **attrs: Any) -> SELECT:
    return SELECT(Options(options, selected), **attrs)

def Href(url: str, text: str, **attrs: Any) -> A:
    a = A(text, href=url, **attrs)
    return a

def Mailto(address: str, text: str, subject: str = '', **attrs: Any) -> A:
    if subject:
        href = "mailto:%s?subject=%s" % (address, XML.url_encode(subject))
    else:
        href = "mailto:%s" % (address,)
    return A(text, href=href, **attrs)

def Image(src: str, **attrs: Any) -> IMG:
    return IMG(src=src, **attrs)

def StyledTR(element: Type[TR], row: List[str], klasses: List[str]) -> TR:
    tr = element()
    for j in range(len(row)):
        td = TD(row[j])
        if j < len(klasses) and klasses[j]:
            td['class'] = klasses[j]
        tr.append(td)
    return tr

def StyledVTable(klasses: List[str], *rows: List[str], **attrs: Any) -> TABLE:
    table = TABLE(**attrs)
    for row in rows:
        table.append(StyledTR(TR, row, klasses))
    return table

def VTable(*rows: List[str], **attrs: Any) -> TABLE:
    table = TABLE(**attrs)
    for row in rows:
        tr = TR()
        table.append(tr)
        for cell in row:
            tr.append(TD(cell))
    return table

def StyledHTable(klasses: List[str], headers: List[str], *rows: List[str], **attrs: Any) -> TABLE:
    table = TABLE(**attrs)
    table.append(StyledTR(THEAD, headers, klasses))
    for row in rows:
        table.append(StyledTR(TR, row, klasses))
    return table

def HTable(headers: List[str], *rows: List[str], **attrs: Any) -> TABLE:
    table = TABLE(**attrs)
    tr = THEAD()
    table.append(tr)
    for header in headers:
        tr.append(TH(header))
    for row in rows:
        tr = TR()
        table.append(tr)
        for cell in row:
            tr.append(TD(cell))
    return table

def DefinitionList(*items: Tuple[str, str], **attrs: Any) -> DL:
    dl = DL(**attrs)
    for term, definition in items:
        dl.append(DT(term))
        dl.append(DD(definition))
    return dl

#----------------------------------------------------------------------

class Document(XML.Document):

    name = 'html'
    doctype = XML.Markup("DOCTYPE",
                 'html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" ' \
                 '"http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd"')
    content_type = 'text/html'
    
    generator = META(name="generator", content="HyperText package (Python)")
    body_element = BODY

    def __init__(self, *content: Any, **attrs: Any) -> None:
        XML.Document.__init__(self, **attrs)
        h = HEAD(TITLE())
        h.append(META(http_equiv="Content-Type", content="text/html; charset=utf-8"))
        h.append(self.generator)
        b = self.body_element()
        self.append(h, b)
        for c in content:
            b.append(c)

    def append(self, *items: Any) -> None:
        # pass new items along to the body by default
        try:
            body = self.content[1]
            body.append(*items)
        except:
            XML.Document.append(self, *items)

class FramesetDocument(Document):

    doctype = XML.Markup("DOCTYPE",
                 'html PUBLIC "-//W3C//DTD XHTML 1.0 Frameset//EN" ' \
                 '"http://www.w3.org/TR/xhtml1/DTD/xhtml1-frameset.dtd"')
    body_element = FRAMESET

class CGIDocument(XML.CGIMixIn,Document): pass
class HTTPDocument(XML.HTTPMixIn,Document): pass
