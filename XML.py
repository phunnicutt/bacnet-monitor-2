#!/usr/bin/python

"""
XML Processing
"""

import sys
import re
import os
import math
import types
from io import StringIO
from typing import Any, Dict, List, Optional, Set, Tuple, Union, TypeVar, Callable, Iterator, cast, Type, Sequence, IO

# Import from the compatibility module instead of directly from bacpypes
from bacpypes_compat import set_bacpypes_version, get_debugging

# Initialize bacpypes version (default to bacpypes, will fall back to bacpypes3 if needed)
set_bacpypes_version(False)  # Use bacpypes by default

# Get debugging components
_, ModuleLogger, DebugContents = get_debugging()

# Python 3 compatibility - string functions
# Replace string module imports with Python 3 compatible code
from cgi import escape as _escape

# Define string constants for Python 3
letters = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
digits = '0123456789'

# Define replacements for string module functions
def lower(s: str) -> str:
    return s.lower()

def join(items: List[str], sep: str = '') -> str:
    return sep.join(items)

def replace(s: str, old: str, new: str) -> str:
    return s.replace(old, new)

_debug = 0
_log = ModuleLogger(globals())

_coreattrs = {'id': 1, 'idref': 1, 'xmlns': 1 }
_translations = {'id_': 'ID', 'idref_': 'IDREF', 'type_': 'type', 'class_': 'class' }

_nbsp = "&nbsp;"
_safe = letters + digits + '_,.-'

def quote(s: str) -> str:
    r = ''
    for c in s:
        if c == '<': r += '&lt;'
        elif c == '>': r += '&gt;'
        elif c == '&': r += '&amp;'
        elif c == '"': r += '&quot;'
        else: r += c
    if _debug:
        print("quote(%r) -> %r" % (s, r))
    return r
    
def url_encode(s: str) -> str:
    l = []
    for c in s:
        if c in _safe: l.append(c)
        elif c == ' ': l.append('+')
        else:          l.append("%%%02x" % ord(c))
    return join(l, '')

#----------------------------------------------------------------------

class Element(DebugContents):

    _quoted = True
    _debugContents = ('_quoted', 'name', 'dict', 'content++')
    
    content_model = 1
    defaults: Dict[str, Any] = {}

    attlist = _coreattrs
    attr_translations = _translations

    def __init__(self, *content: Any, **attr: Any) -> None:
        """Initialize an element."""
        if not hasattr(self, 'name'):
            self.name = lower(self.__class__.__name__.replace('_','-'))

        # make sure this element should have content
        if not self.content_model and content:
            raise TypeError("No content for this element")

        # make sure the attributes are valid
        for k in list(attr.keys()):
            if k.count('__') == 0:
                k2 = self.attr_translations.get(k, k).replace('_','-')
                if not self.valid_attr(self.attlist, k2):
                    raise AttributeError("invalid attribute %s" % (k2,))

        # start with no attributes
        self.dict: Dict[str, Any] = {}

        # add the defaults if there are any
        if self.defaults:
            self.update(self.defaults)

        # add the attributes provided
        if attr:
            self.update(attr)

        # make a list of the content
        self.content: List[Any] = list(content)
        
    def append(self, *items: Any) -> None:
        if not hasattr(self, 'content'):
            raise RuntimeError("missing content, verify ctor was given valid attributes")
        for item in items:
            if isinstance(item, list):
                self.append(*item)
            else:
                self.content.append(item)

    def valid_attr(self, attrs: Union[Dict[str, Any], List[Dict[str, Any]]], k: str) -> bool:
        """Attribute lists can be dictionaries or lists of dictionaries,
        recursively.  Return a True iff the key is somewhere in the tree."""
        if isinstance(attrs, dict):
            return k in attrs
        elif isinstance(attrs, list):
            for item in attrs:
                if self.valid_attr(item, k):
                    return True
            return False
        else:
            raise TypeError("attrs must be a dictionary or list, got" + str(type(attrs)))
        
    def __getitem__(self, k: str) -> Any:
        if (not isinstance(k, str)) or k.startswith('_'):
            raise AttributeError("invalid attribute %s" % (k,))

        return self.dict[k]

    def __setitem__(self, k: str, v: Any) -> None:
        if (not isinstance(k, str)) or k.startswith('_'):
            raise AttributeError("invalid attribute %s" % (k,))

        if k.count('__'):
            self.dict[k.replace('__',':')] = v
        else:
            k2 = self.attr_translations.get(k, k).replace('_','-')
            if self.valid_attr(self.attlist, k2):
                self.dict[k2] = v
            else:
                raise AttributeError("invalid attribute %s" % (k2,))

    def get(self, k: str, v: Any) -> Any:
        """Make get() work on the attribute dictionary so
        elements can be tested for an attribute."""
        return self.dict.get(k,v)
    
    def update(self, d: Dict[str, Any]) -> None:
        for k, v in list(d.items()):
            self[k] = v

    def str_attribute(self, k: str) -> str:
        v = _escape(str(self.dict[k]), 1)
        return k + '="' + v + '"'

    def str_attribute_list(self) -> str:
        return join(list(map(self.str_attribute, list(self.dict.keys()))))

    def start_tag(self) -> str:
        a = self.str_attribute_list()
        if self.content:
            if a:
                return "<%s %s>" % (self.name, a)
            else:
                return "<%s>" % (self.name,)
        else:
            if a:
                return "<%s %s />" % (self.name, a)
            else:
                return "<%s />" % (self.name,)

    def end_tag(self) -> str:
        return self.content and "</%s>" % self.name or ''

    def __str__(self, indent: int = 0, perlevel: int = 0) -> str:
        if _debug:
            print("Element.__str__", self.__class__.__name__)
        slist = [self.start_tag()]
        for c in self.content:
            if _debug:
                print("   - c:", repr(c))
            try:
                s = c.__str__(indent+perlevel, perlevel)
                if _debug:
                    print("   - s:", repr(s))
                slist.append(s)
            except:
                if self._quoted and isinstance(c, str):
                    s = quote(c)
                    if _debug:
                        print("   - quote(c):", repr(s))
                else:
                    s = str(c)
                    if _debug:
                        print("   - str(c):", repr(s))
                slist.append(s)
        slist.append(self.end_tag())
        return ''.join(slist)

    def writeto(self, fp: IO = sys.stdout, indent: int = 0, perlevel: int = 0) -> None:
        fp.write(self.start_tag())
        for c in self.content:
            if hasattr(c, 'writeto'):
                getattr(c, 'writeto')(fp, indent+perlevel, perlevel)
            elif self._quoted and isinstance(c, str):
                fp.write(quote(c))
            else:
                fp.write(str(c))
        fp.write(self.end_tag())

class Markup(Element):
    
    _quoted = False
        
    def __init__(self, name: str, *content: Any) -> None:
        self.name = name
        self.dict = {}
        self.content = list(content)

    start_tag_string = "<!%s "

    def start_tag(self) -> str:
        return self.start_tag_string % self.name

    def end_tag(self) -> str:
        return ">\n"

class Comment(Element):
    
    _quoted = False
        
    def __init__(self, *content: Any) -> None:
        self.content = list(content)
        
    def start_tag(self) -> str:
        return "<!-- "

    def end_tag(self) -> str:
        return " -->"

class Unquoted(Element):
    
    _quoted = False
        
    def __init__(self, *content: Any) -> None:
        self.content = list(content)
        
    def start_tag(self) -> str:
        return ""

    def end_tag(self) -> str:
        return ""

class CDATA(Element):

    _quoted = False
        
    def __init__(self, *content: Any) -> None:
        self.content = list(content)
        
    def start_tag(self) -> str:
        return "<![CDATA["

    def end_tag(self) -> str:
        return "]]>"

class ProcessingInstruction(Element):

    def __init__(self, name: str, *content: Any, **attr: Any) -> None:
        self.name = name
        Element.__init__(self, *content, **attr)

    start_tag_string = "<?%s %s"
    end_tag_string = "?>"

    def valid_attr(self, attrs: Union[Dict[str, Any], List[Dict[str, Any]]], k: str) -> bool:
        return True
        
    def start_tag(self) -> str:
        a = self.str_attribute_list()
        if a:
            return self.start_tag_string % (self.name, a)
        else:
            return self.start_tag_string % (self.name, "")

    def end_tag(self) -> str:
        return self.end_tag_string

class XMLPI(ProcessingInstruction):

    defaults = {'version': '1.0'}
    attlist = {'version': 1, 'encoding': 1}
    
    def __init__(self, *content: Any, **attrs: Any) -> None:
        ProcessingInstruction.__init__(self, 'xml', *content, **attrs)
        
class XMLStyleSheet(ProcessingInstruction):

    attlist = {'href': 1, 'type': 1}
    attr_translations = {'type_':'type'}
    attr_translations.update(_translations)
    
    def __init__(self, *content: Any, **attrs: Any) -> None:
        ProcessingInstruction.__init__(self, 'xml-stylesheet', *content, **attrs)
        
class PrettyTagsMixIn:

    def __str__(self, indent: int = 0, perlevel: int = 2) -> str:
        if _debug:
            print("PrettyTagsMixIn.__str__", self.__class__.__name__)
        slist = [' ' * indent, self.start_tag(), '\n']
        for c in self.content:
            try:
                s = c.__str__(indent+perlevel, perlevel)
                slist.append(s)
                slist.append('\n')
            except:
                if self._quoted and isinstance(c, str):
                    s = quote(c)
                else:
                    s = str(c)
                slist.append(' ' * (indent+perlevel))
                slist.append(s)
                slist.append('\n')
        slist.append(' ' * indent)
        slist.append(self.end_tag())
        return ''.join(slist)

    def writeto(self, fp: IO = sys.stdout, indent: int = 0, perlevel: int = 2) -> None:
        fp.write(' ' * indent)
        fp.write(self.start_tag())
        fp.write('\n')
        for c in self.content:
            if hasattr(c, 'writeto'):
                getattr(c, 'writeto')(fp, indent+perlevel, perlevel)
            else:
                if self._quoted and isinstance(c, str):
                    fp.write(' ' * (indent+perlevel))
                    fp.write(quote(c))
                else:
                    fp.write(' ' * (indent+perlevel))
                    fp.write(str(c))
                fp.write('\n')
        fp.write(' ' * indent)
        fp.write(self.end_tag())

#----------------------------------------------------------------------

def _merge(seqs: List[List[Any]]) -> List[Any]:
#   print('\n\nCPL[%s]=%s' % (seqs[0][0],seqs))
    res: List[Any] = []; i=0
    while 1:
      nonemptyseqs=[seq for seq in seqs if seq]
      if not nonemptyseqs: return res
      i+=1
#     print('\n',i,'round: candidates...')
      for seq in nonemptyseqs: # fin merge candidates among seq heads
          cand = seq[0]
#         print(' ',cand)
          nothead=[s for s in nonemptyseqs if cand in s[1:]]
          if nothead: cand=None #reject candidate
          else: break
      if not cand:
          raise RuntimeError("Inconsistent hierarchy")
      res.append(cand)
      for seq in nonemptyseqs: # remove cand
          if seq[0] == cand: del seq[0]

def _mro(C: Type) -> List[Type]:
    """Compute the class precedence list (mro) according to C3"""
    return _merge([[C]]+list(map(_mro,C.__bases__))+[list(C.__bases__)])

#
#   CGIMixIn
#

class CGIMixIn:

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.headers: List[Tuple[str, str]] = []

        # get the mro, find this class, and trim
        mro = _mro(self.__class__)
        self._mro = mro[mro.index(CGIMixIn)+1:]

        # continue initialization to the next class in the chain
        for cls in self._mro:
            try:
                cls.__init__(self,*args,**kwargs)
                break
            except:
                pass
        
    def send_header(self, k: str, v: str) -> None:
        self.headers.append((k, v))
        
    def __str__(self, indent: int = 0, perlevel: int = 2) -> str:
        # build the headers
        s = []
        if self.content_type:
            s.append('Content-Type: %s\r\n' % (self.content_type,))
        for hdr in self.headers:
            s.append("%s: %s\r\n" % hdr)
        if s:
            s.append('\r\n')
        
        # call the next class in the chain
        for cls in self._mro:
            try:
                s.append(cls.__str__(self, indent, perlevel))
                break
            except:
                pass

        # join the results
        return ''.join(s)

    def writeto(self, fp: IO = sys.stdout, indent: int = 0, perlevel: int = 2) -> None:
        # write the headers
        if self.content_type:
            fp.write('Content-Type: %s\r\n' % (self.content_type,))
        for hdr in self.headers:
            fp.write("%s: %s\r\n" % hdr)
        fp.write("\r\n")
        
        # call the next class in the chain
        for cls in self._mro:
            try:
                cls.writeto(self,fp,indent,perlevel)
                break
            except:
                pass

#
#   HTTPMixIn
#

class HTTPMixIn(CGIMixIn):

    protocol_version = 'HTTP/1.0'
    response = (200, 'OK')
    
    def _str_http_response(self) -> str:
        return "%s %s %s\r\n" % (self.protocol_version, self.response[0], self.response[1])
        
    def __str__(self, indent: int = 0, perlevel: int = 2) -> str:
        return self._str_http_response() + CGIMixIn.__str__(self, indent, perlevel)

    def send_response(self, n: int, msg: str) -> None:
        self.response = (n, msg)
        
    def writeto(self, req: Any, indent: int = 0, perlevel: int = 2) -> None:
        req.wfile.write(self._str_http_response())
        CGIMixIn.writeto(self, req.wfile, indent, perlevel)

#----------------------------------------------------------------------

class Document(PrettyTagsMixIn, Element):

    doctype = None
    content_type: Optional[str] = None
    
    def __init__(self, *content: Any, **attrs: Any) -> None:
        Element.__init__(self, *content, **attrs)

        # lead everything off with an XML header
        self.piheaders = [XMLPI()]
        
    def __str__(self, indent: int = 0, perlevel: int = 2) -> str:
        s = list(map(str, self.piheaders))
        if self.doctype:
            s.append(str(self.doctype))
        s = join(s, '\n')
        s += PrettyTagsMixIn.__str__(self, indent, perlevel)
        return s

    def writeto(self, fp: IO = sys.stdout, indent: int = 0, perlevel: int = 2) -> None:
        sep = False
        for c in self.piheaders:
            if sep: fp.write('\n')
            if hasattr(c, 'writeto'):
                getattr(c, 'writeto')(fp, indent+perlevel, perlevel)
            else:
                fp.write(str(c))
            sep = True
        if self.doctype:
            if sep: fp.write('\n')
            if hasattr(self.doctype, 'writeto'):
                getattr(self.doctype, 'writeto')(fp, indent+perlevel, perlevel)
            else:
                fp.write(str(self.doctype))
            sep = True
        PrettyTagsMixIn.writeto(self, fp, indent, perlevel)

class CGIDocument(CGIMixIn, Document): pass
class HTTPDocument(HTTPMixIn, Document): pass

#----------------------------------------------------------------------

class TextDocument:

    content_type = 'text/plain'
    
    def __init__(self, *content: Any) -> None:
        if _debug:
            print("TextDocument.__init__")
            
        self.content: List[Any] = list(content)

    def append(self, *items: Any) -> None:
        if _debug:
            print("TextDocument.append", items)
            
        list(map(self.content.append, items))

    def __str__(self, indent: int = 0, perlevel: int = 2) -> str:
        if _debug:
            print("TextDocument.__str__", indent, perlevel)
            
        s = list(map(str,self.content))
        return join(s,'')

    def writeto(self, fp: IO = sys.stdout, indent: int = 0, perlevel: int = 2) -> None:
        if _debug:
            print("TextDocument.writeto", fp, indent, perlevel)
            
        for c in self.content:
            if hasattr(c, 'writeto'):
                getattr(c, 'writeto')(fp, indent+perlevel, perlevel)
            else:
                fp.write(str(c))

class CGITextDocument(CGIMixIn, TextDocument): pass
class HTTPTextDocument(HTTPMixIn, TextDocument): pass

#----------------------------------------------------------------------

class CSSDocument(TextDocument):

    content_type = 'text/css'

class CGICSSDocument(CGIMixIn, CSSDocument): pass
class HTTPCSSDocument(HTTPMixIn, CSSDocument): pass

#----------------------------------------------------------------------

class HTMLDocument(TextDocument):

    content_type = 'text/html'

class CGIHTMLDocument(CGIMixIn, HTMLDocument): pass
class HTTPHTMLDocument(HTTPMixIn, HTMLDocument): pass

#----------------------------------------------------------------------
#
#   This class is significantly different from the Document class in
#   the SVG module, which is designed to programatically build documents
#   while this one is used to present static content.
#

class SVGDocument(TextDocument):

    content_type = 'image/svg+xml'

class CGISVGDocument(CGIMixIn, SVGDocument): pass
class HTTPSVGDocument(HTTPMixIn, SVGDocument): pass

#----------------------------------------------------------------------

class ScriptDocument(TextDocument):

    content_type = 'text/javascript'

class CGIScriptDocument(CGIMixIn, ScriptDocument): pass
class HTTPScriptDocument(HTTPMixIn, ScriptDocument): pass

