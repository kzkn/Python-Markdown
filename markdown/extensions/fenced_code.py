"""
Fenced Code Extension for Python Markdown
=========================================

This extension adds Fenced Code Blocks to Python-Markdown.

See <https://pythonhosted.org/Markdown/extensions/fenced_code_blocks.html>
for documentation.

Original code Copyright 2007-2008 [Waylan Limberg](http://achinghead.com/).


All changes Copyright 2008-2014 The Python Markdown Project

License: [BSD](http://www.opensource.org/licenses/bsd-license.php)
"""

from __future__ import absolute_import
from __future__ import unicode_literals
from . import Extension
from ..preprocessors import Preprocessor
from ..util import parseBoolValue
from .codehilite import CodeHilite, CodeHiliteExtension, parse_hl_lines
import re


__LABEL_RE = re.compile(r'''[a-zA-Z0-9_+-]+''')
__VALUE_RE = re.compile(r'''(?P<quot>"|')(?P<value>.*)(?P=quot)''')


def __identity(x):
    return x


__OPTION_PARSERS = {
    'hl_lines': __identity,
    'linenums': parseBoolValue,
}


def __truncate_brackets(s):
    if len(s) >= 2 and s[0] == '{' and s[-1] == '}':
        return s[1:-1]
    else:
        return s


def __truncate_dot(s):
    if len(s) >= 1 and s[0] == '.':
        return s[1:]
    else:
        return s


def __do_parse(string):
    while True:
        m = __LABEL_RE.search(string)
        if not m:
            return

        label = m.group()
        string = string[m.end():].lstrip()
        if len(string) > 0 and string[0] == '=':
            m = __VALUE_RE.search(string[1:])
            if m:
                value = m.group('value')
                string = string[m.end():].lstrip()
                yield label, __OPTION_PARSERS.get(label, __identity)(value)
        else:
            yield 'lang', label


def parse_options(string):
    string = string.strip()
    string = __truncate_brackets(string)
    string = __truncate_dot(string)

    opts = dict()
    for k, v in __do_parse(string):
        opts[k] = v
    return opts


class FencedCodeExtension(Extension):

    def extendMarkdown(self, md, md_globals):
        """ Add FencedBlockPreprocessor to the Markdown instance. """
        md.registerExtension(self)

        md.preprocessors.add('fenced_code_block',
                             FencedBlockPreprocessor(md),
                             ">normalize_whitespace")


class FencedBlockPreprocessor(Preprocessor):
    FENCED_BLOCK_RE = re.compile(r'''
(?P<fence>^(?:~{3,}|`{3,}))[ ]*         # Opening ``` or ~~~
(?P<options>[a-zA-Z0-9 .{}="'_+-]*)\n
(?P<code>.*?)(?<=\n)
(?P=fence)[ ]*$''', re.MULTILINE | re.DOTALL | re.VERBOSE)
    CODE_WRAP = '<pre><code%s>%s</code></pre>'
    LANG_TAG = ' class="%s"'

    def __init__(self, md):
        super(FencedBlockPreprocessor, self).__init__(md)

        self.checked_for_codehilite = False
        self.codehilite_conf = {}

    def run(self, lines):
        """ Match and store Fenced Code Blocks in the HtmlStash. """

        # Check for code hilite extension
        if not self.checked_for_codehilite:
            for ext in self.markdown.registeredExtensions:
                if isinstance(ext, CodeHiliteExtension):
                    self.codehilite_conf = ext.config
                    break

            self.checked_for_codehilite = True

        text = "\n".join(lines)
        while 1:
            m = self.FENCED_BLOCK_RE.search(text)
            if m:
                opts = dict()
                lang = ''
                if m.group('options'):
                    opts = parse_options(m.group('options'))
                    lang = self.LANG_TAG % opts.get('lang', '')

                # If config is not empty, then the codehighlite extension
                # is enabled, so we call it to highlight the code
                if self.codehilite_conf:
                    highliter = CodeHilite(
                        m.group('code'),
                        linenums=self._option('linenums', opts),
                        guess_lang=self.codehilite_conf['guess_lang'][0],
                        css_class=self.codehilite_conf['css_class'][0],
                        style=self.codehilite_conf['pygments_style'][0],
                        lang=opts.get('lang'),
                        noclasses=self.codehilite_conf['noclasses'][0],
                        hl_lines=parse_hl_lines(opts.get('hl_lines'))
                    )

                    code = highliter.hilite()
                else:
                    code = self.CODE_WRAP % (lang,
                                             self._escape(m.group('code')))

                placeholder = self.markdown.htmlStash.store(code, safe=True)
                text = '%s\n%s\n%s' % (text[:m.start()],
                                       placeholder,
                                       text[m.end():])
            else:
                break
        return text.split("\n")

    def _escape(self, txt):
        """ basic html escaping """
        txt = txt.replace('&', '&amp;')
        txt = txt.replace('<', '&lt;')
        txt = txt.replace('>', '&gt;')
        txt = txt.replace('"', '&quot;')
        return txt

    def _option(self, name, inlineOptions):
        if name in inlineOptions:
            return inlineOptions.get(name)
        else:
            return self.codehilite_conf[name][0]


def makeExtension(*args, **kwargs):
    return FencedCodeExtension(*args, **kwargs)
