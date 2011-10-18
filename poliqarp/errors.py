# This file is part of the Poliqarp suite.
#
# Copyright (C) 2009 by Instytut Podstaw Informatyki Polskiej
# Akademii Nauk (IPI PAN; Institute of Computer Science, Polish
# Academy of Sciences; cf. www.ipipan.waw.pl).  All rights reserved.
#
# This file may be distributed and/or modified under the terms of the
# GNU General Public License version 2 as published by the Free Software
# Foundation and appearing in the file gpl.txt included in the packaging
# of this file.  (See http://www.gnu.org/licenses/translations.html for
# unofficial translations.)
#
# A commercial license is available from IPI PAN (contact
# Michal.Ciesiolka@ipipan.waw.pl or ipi@ipipan.waw.pl for more
# information).  Licensees holding a valid commercial license from IPI
# PAN may use this file in accordance with that license.
#
# This file is provided AS IS with NO WARRANTY OF ANY KIND, INCLUDING
# THE WARRANTY OF DESIGN, MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE.

'''
Interface to Poliqarp daemon (protocol errors).
'''

class ProtocolViolation(Exception):
    pass

class ProtocolError(Exception):
    id = None
    message = None
    _dispatch = {}


    def __init__(self):
        Exception.__init__(self)

    def __str__(self):
        if self.message is None:
            return Exception.__str__(self)
        else:
            return self.message

PPE_ARGCOUNT = 1 # Incorrect number of arguments
PPE_NOSESSION = 3 # No session opened
PPE_SESSBOUND = 4 # Cannot create a session for a connection that is already bound
PPE_NOMEM = 5 # Not enough memory
PPE_INVSID = 6 # Invalid session ID
PPE_SIDUSED = 7 # Session with this ID is already bound
PPE_INVUID = 8 # Session user ID does not match the argument of RECONNECT
PPE_CORPUSALR = 10 # Session already has an open corpus
PPE_SYSOPEN = 12 # System error while opening the corpus
PPE_NOCORPUS = 13 # No corpus opened
PPE_INVJID = 14 # Invalid job ID
PPE_BUSY = 15 # A job is already in progress
PPE_INVQUERY = 16 # Incorrect query
PPE_INVRANGE = 17 # Invalid result range
PPE_INVOPT = 18 # Incorrect session option
PPE_INVVAL = 19 # Invalid session option value
PPE_INVCRIT = 20 # Invalid sorting criteria

def _(x): return x

class ArityErrror(ProtocolError):
    id = PPE_ARGCOUNT
    message = _('Incorrect number of arguments')

class NoSession(ProtocolError):
    id = PPE_NOSESSION
    message = _('No session opened')

class SessionAlreadyBound(ProtocolError):
    id = PPE_SESSBOUND
    message = _('Cannot create a session for a connection that is already bound')

class MemoryError(ProtocolError):
    id = PPE_NOMEM
    message = _('Not enough memory')

class InvalidSessionId(ProtocolError):
    id = PPE_INVSID
    message = _('Invalid session ID')

class SessionIdAlreadyBound(ProtocolError):
    id = PPE_SIDUSED
    message = _('Session with this ID is already bound')

class InvalidSessionUserId(ProtocolError):
    id = PPE_INVUID
    message = _('Session user ID does not match the argument of RECONNECT')

class CorpusAlreadyOpen(ProtocolError):
    id = PPE_CORPUSALR
    message = _('Session already has an open corpus')

class SystemOpenError(ProtocolError):
    id = PPE_SYSOPEN
    message = _('System error while opening the corpus')

class NoCorpus(ProtocolError):
    id = PPE_NOCORPUS
    message = _('No corpus opened')

class InvalidJobId(ProtocolError):
    id = PPE_INVJID
    message = _('Invalid job ID')

class Busy(ProtocolError):
    id = PPE_BUSY
    message = _('A job is already in progress')

class InvalidQuery(ProtocolError):
    id = PPE_INVQUERY
    message = _('Incorrect query')

class InvalidRange(ProtocolError):
    id = PPE_INVRANGE
    message = _('Invalid result range')

class InvalidSessionOption(ProtocolError):
    id = PPE_INVOPT
    message = _('Incorrect session option')

class InvalidSessionOptionValue(ProtocolError):
    id = PPE_INVVAL
    message = _('Invalid session option value')

class InvalidSortingCriteria(ProtocolError):
    id = PPE_INVCRIT
    message = _('Invalid sorting criteria')

_globals = list(globals().values())
for _cls in _globals:
    if not isinstance(_cls, type(Exception)):
        continue
    if not issubclass(_cls, ProtocolError):
        continue
    if _cls.__bases__ and _cls.__bases__[0] == ProtocolError:
        ProtocolError._dispatch[_cls.id] = _cls
del _cls, _globals

def protocol_error(id):
    try:
        subclass = ProtocolError._dispatch[int(id)]
    except (ValueError, TypeError, KeyError):
        return ProtocolViolation()
    return subclass()

# vim:ts=4 sw=4 et
