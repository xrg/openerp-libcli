# -*- coding: utf-8 -*-
# Copyright (c) 2011, P. Christeas <xrg@openerp.com>
# All rights reserved.

# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:

# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.

# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

import re
_doxygen_reprs = []

__doxygen_mode_tmpls = {'word': (r'%s\s([\S]+)\s', r'%s`\1` '),
        'word-in': (r'%s\s([\S]+)\s', r':%s \1: '),
        'inline': (r'%s\s', r':%s: '),
        'nextline': (r'%s\s', r'\n:%s: '),
        'oneline': (r'%s\s(.*)$', r'%s \1'),
        'oneline-c': (r'%s\s(.*)$', r'%s'),
        }

def _add_doxy_key(key, mode, repl):
    mtmpl, mrepl = __doxygen_mode_tmpls.get(mode, ('%s', '%s')) 
    
    print "match", mtmpl % key
    _doxygen_reprs.append((re.compile(mtmpl % key), mrepl % repl))

def proc_docstring(app, what, name, obj, options, lines):
    global _doxygen_reprs
    n = 0
    while n < len(lines):
        l = lines[n]
        for dre, dpl  in _doxygen_reprs:
            l2 = dre.sub(dpl, l)
            
            if l2 != l:
                lines2 = l2.split('\n')
                lines[n] = lines2[0]
                lines2 = lines2[1:]
                for i, l2 in enumerate(lines2):
                    lines.insert(n+i+1, l2)
                break # the inner loop
        n += 1
    # end for

def setup(app):
    app.require_sphinx('1.0')
    _add_doxy_key('@param','word-in', 'param')
    _add_doxy_key('@return', 'nextline', 'return')
    _add_doxy_key('@note', 'nextline', 'note')
    _add_doxy_key('@brief', 'oneline-c', '\n\1') #no equivalent, we just suppress
    _add_doxy_key('@code', 'oneline', '\1') # TODO
    app.connect('autodoc-process-docstring', proc_docstring)

#eof
