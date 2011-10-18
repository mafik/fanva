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
Interface to Poliqarp daemon.
'''

import socket
import re
import datetime

from poliqarp.errors import ProtocolViolation, ProtocolError, InvalidQuery, SystemOpenError, Busy, protocol_error

DEBUG = False

def debug(s):
    import sys
    sys.stderr.write(s)

DEFAULT_HOST = '127.0.0.1'
DEFAULT_PORT = 4567

MAX_CONTEXT_SEGMENTS = 20
MAX_WCONTEXT_SEGMENTS = 200

class AsynchronousMessageExpected(Exception):
    pass

class UnsupportedCommand(Exception):
    pass

class Timeout(Exception):
    pass

class QueryRunning(Exception):
    pass

class EmptyQuery(ProtocolError):
    message = 'Query is empty'

JOB_NO = 0
JOB_RUNNING = 1
JOB_DONE = 2

class Date(object):

    def __init__(self, year=None, month=None, day=None):
        datetime.date(year or 2000, month or 1, day or 1)
        self.year = year or None
        self.month = month or None
        self.day = day or None

    def __str__(self):
        result = [self.year, self.month, self.day]
        while result[-1] is None:
            del result[-1]
        for i, n_digits in enumerate((4, 2, 2)):
            try:
                if result[i]:
                    result[i] = '%0*d' % (n_digits, result[i])
                else:
                    result[i] = '?' * n_digits
            except IndexError:
                break
        return '-'.join(result)

    def __cmp__(self, other):
        return cmp((self.year, self.month, self.day), (other.year, other.month, other.day))

    def __repr__(self):
        return '%s(%s)' % (self.__class__.__name__, ', '.join(
            '%s=%r' % (key, value)
            for key in ('year', 'month', 'day')
            for value in (getattr(self, key),) if value is not None
        ))

class Connection(object):

    def __init__(self, host=DEFAULT_HOST, port=DEFAULT_PORT):
        host = str(host)
        port = str(port)
        if port.isdigit():
            port = int(port)
        else:
            port = socket.getservbyname(port)
        self._address = host, port
        self._invalidate_corpus()
        self._session_id = None
        self._socket = self._file = None

    @property
    def socket(self):
        if self._socket is None:
            s = self._socket = socket.socket()
            s.connect(self._address)
        return self._socket

    @property
    def file(self):
        if self._file is None:
            self._file = self.socket.makefile(mode='rw')
        return self._file

    def __getstate__(self):
        self._n_stored_results = None
        if self._socket is not None or self._file is not None:
            raise ValueError('Cannot pickle an active connection')
        return self.__dict__

    def __setstate__(self, state):
        self.__dict__.update(state)

    def _put(self, s):
        self.file.write(s)
        self.file.write('\n')
        self.file.flush()
        if DEBUG:
            debug('> %s\n' % s)

    def _set_timeout(self, timeout):
        self.socket.settimeout(timeout)

    def _reset_timeout(self):
        self._set_timeout(None)

    def _handle_async_message(self, message):
        if message == 'OPENED':
            self._open_status = JOB_DONE
        elif message.startswith('OPENFAIL '):
            self._open_status = JOB_NO
            self._open_path = None
            try:
                raise protocol_error(message[9:])
            except SystemOpenError as ex:
                message = self.get_last_error();
                if message is None:
                    raise ProtocolViolation
                ex.message = message
                raise
        elif message == 'NEW-RESULTS':
            self._n_stored_results = None
        elif message == 'SORTED':
            self._sort_status = JOB_DONE
        elif message.startswith('QUERY-DONE '):
            self._query_status = JOB_DONE
            self._n_stored_results = int(message[10:])
        else:
            raise ProtocolViolation

    def _get_async_message(self, timeout=None):
        self._set_timeout(timeout)
        try:
            try:
                r = self.file.readline()[:-1]
            except socket.timeout:
                raise Timeout
        finally:
            self._reset_timeout()
        if DEBUG:
            debug('< %s\n' % r)
        if r.startswith('M '):
            self._handle_async_message(r[2:])
        elif r.startswith('R '):
            raise AsynchronousMessageExpected
        else:
            raise ProtocolViolation

    def _get_text(self):
        while True:
            r = self.file.readline()[:-1]
            if DEBUG:
                debug('< %s\n' % r)
            if r.startswith('R '):
                return r[2:]
            elif r.startswith('M '):
                self._handle_async_message(r[2:])
            else:
                raise ProtocolViolation

    def _get_reply(self):
        while True:
            r = self.file.readline()[:-1]
            if DEBUG:
                debug('< %s\n' % r)
            if r.startswith('R '):
                r = r[2:]
                if r.startswith('ERR '):
                    raise protocol_error(r[4:])
                elif r == 'UNSUPPORTED':
                    raise UnsupportedCommand()
                else:
                    return r
            elif r.startswith('M '):
                self._handle_async_message(r[2:])
            else:
                raise ProtocolViolation(r)

    def ping(self):
        self._put('PING')
        if self._get_reply() != 'PONG':
            raise ProtocolViolation

    def get_version(self):
        self._put('GET-VERSION')
        return self._get_reply()

    def get_default_session_name(self):
        return self.socket.getsockname()[0]

    '''
    Create new or resume existing session.

    Returns session id if a new session was created.
    '''
    def make_session(self, name=None, session_id=None):
        if name is None:
            name = self.get_default_session_name()
        if session_id is None:
            session_id = self._session_id
        new_session = session_id is None
        if new_session:
            command = 'MAKE-SESSION %s' % name
        else:
            command = 'RESUME-SESSION %s %s' % (session_id, name)
        self._put(command)
        r = self._get_reply()
        if not new_session:
            if r != 'OK':
                raise ProtocolViolation
        else:
            if r.startswith('OK '):
                session_id = r[3:]
            else:
                raise ProtocolViolation
        self._session_id = session_id
        if new_session:
            return session_id

    def close_session(self):
        self._put('CLOSE-SESSION')
        if self._get_reply() != 'OK':
            raise ProtocolViolation
        self._session_id = None

    def suspend_session(self):
        self._put('SUSPEND-SESSION')
        if self._get_reply() != 'OK':
            raise ProtocolViolation

    def open_corpus(self, path, timeout=None):
        path = str(path)
        if '\n' in path:
            raise ValueError
        if self._open_status == JOB_DONE and path != self._open_path:
            self.close_corpus()
        if self._open_status == JOB_NO:
            self._put('OPEN-CORPUS %s' % path)
            r = self._get_reply()
            if r != 'OK':
                raise ProtocolViolation
            self._open_path = path
            if self._open_status == JOB_NO:
                self._open_status = JOB_RUNNING
        else:
            if path != self._open_path:
                raise NotImplementedError # FIXME
            if self._open_status == JOB_DONE:
                return
        self._get_async_message(timeout=timeout)
        if self._open_status != JOB_DONE:
            raise ProtocolViolation

    def _invalidate_query(self):
        self._query = None
        self._query_status = JOB_NO
        self._sort_id = None
        self._sort_status = JOB_NO
        self._column_types = None
        self._n_stored_results = None

    def _invalidate_corpus(self):
        self._open_status = JOB_NO
        self._open_path = None
        self._invalidate_query()

    def close_corpus(self):
        self._put('CLOSE-CORPUS')
        r = self._get_reply()
        if r != 'OK':
            raise ProtocolViolation
        self._invalidate_corpus()

    def get_corpus_statistics(self):
        self._put('GET-CORPUS-STATS')
        r = self._get_reply()
        if not r.startswith('OK '):
            raise ProtocolViolation
        try:
            num_segments, num_types, num_lemmata, num_tags = map(int, r[3:].split())
        except ValueError:
            raise ProtocolViolation(r)
        return num_segments, num_types, num_lemmata, num_tags

    def get_job_status(self):
        self._put('GET-JOB-STATUS')
        r = self._get_reply()
        if r.startswith('OK '):
            try:
                return int(r[3:])
            except ValueError:
                pass
        raise ProtocolViolation(r)

    def cancel_job(self):
        self._put('CANCEL-JOB')
        r = self._get_reply()
        if r != 'OK':
            raise ProtocolViolation(r)

    def make_query(self, query, force=False):
        if not isinstance(query, str):
            query = str('query')
        #query = re.sub('[\x00-\x1f]', ' ', query) # Don't trust user-supplied data.
        if not query:
            raise EmptyQuery
        if query == self._query and not force:
            return
        if self._query_status == JOB_RUNNING:
            raise Busy
        self._invalidate_query()
        self._put('MAKE-QUERY %s' % query)
        try:
            r = self._get_reply()
            if r != 'OK':
                raise ProtocolViolation(r)
        except InvalidQuery as ex:
            message = self.get_last_error();
            if message is None:
                raise ProtocolViolation
            ex.message = message
            raise
        self._query = query

    def get_n_stored_results(self):
        n = self._n_stored_results
        if n is None:
            capacity, n = self.get_buffer_state()
            self._n_stored_results = n
        return n

    def get_n_spotted_results(self):
        self._put('GET-NUM-RESULTS')
        r = self._get_reply()
        if not r.startswith('OK '):
            raise ProtocolViolation(r)
        try:
            n, = map(int, r[3:].split(None, 1))
        except ValueError:
            raise ProtocolViolation(r)
        return n

    def run_query(self, n, m=None, timeout=None, force=False):
        if m is None:
            m = n
        if force:
            if self._query_status == JOB_DONE:
                self._query_status = JOB_NO
            elif self._query_status == JOB_RUNNING:
                raise Busy
        if self._query_status == JOB_DONE:
            return
        elif self._query_status == JOB_NO:
            self._put('RUN-QUERY %d' % n)
            r = self._get_reply()
            if r != 'OK':
                raise ProtocolViolation(r)
            if self._query_status == JOB_NO:
                self._query_status = JOB_RUNNING
        assert self._query_status == JOB_RUNNING
        while self.get_n_stored_results() < m and self._query_status == JOB_RUNNING:
            try:
                self._get_async_message(timeout=timeout)
            except Timeout:
                break
            # FIXME: Ideally, we should update timeout here.
            # But if we don't, we must break the loop right now:
            break
        #if self._query_status == JOB_RUNNING:
        #    raise QueryRunning

    def _get_result_segment(self, ct):
        orth = self._get_text()
        have_interps = ct.has_lemmata or ct.has_tags
        if have_interps:
            interps = []
        else:
            interps = None
        segment = Segment(orth, interps)
        if not have_interps:
            return segment
        r = self._get_reply()
        try:
            m = int(r)
        except ValueError:
            raise ProtocolViolation(m)
        if type(m) != int:
            raise ProtocolViolation(r)
        for j in range(m):
            lemma = tag = None
            if ct.has_lemmata:
                lemma = self._get_text()
            if ct.has_tags:
                tag = self._get_text()
            segment.add_interp(lemma=lemma, tag=tag)
        if ct.has_ids:
            segment.id = int(self._get_text())
        return segment

    def _get_result_column(self, ct):
        r = self._get_reply()
        try:
            n = int(r)
        except ValueError:
            raise ProtocolViolation(r)
        if type(n) != int:
            raise ProtocolViolation(r)
        return ct, [self._get_result_segment(ct) for i in range(n)]

    def _get_result(self, column_types):
        return [self._get_result_column(ct) for ct in column_types]

    def get_results(self, i, j):
        column_types = self.get_column_types()
        i = int(i)
        j = int(j)
        if i < 0:
            raise ValueError
        if j < i:
            return []
        self._put('GET-RESULTS %d %d' % (i, j))
        r = self._get_reply()
        if r != 'OK':
            raise ProtocolViolation(r)
        return [self._get_result(column_types) for k in range(i, j + 1)]

    def get_context(self, i):
        self._put('GET-CONTEXT %d' % i)
        r = self._get_reply()
        if r != 'OK':
            raise ProtocolViolation(r)
        r = tuple(self._get_text() for k in range(4))
        return r

    def get_metadata_types(self):
        self._put('GET-METADATA-TYPES')
        r = self._get_reply()
        if not r.startswith('OK '):
            raise ProtocolViolation(r)
        try:
            n = int(r[3:])
        except ValueError:
            raise ProtocolViolation(r)
        if type(n) != int:
            raise ProtocolViolation(r)
        try:
            result = dict(
                (key, dict(T=unicode, D=Date)[type])
                for i in range(n)
                for type, key in [self._get_text().split(None, 1)]
            )
        except KeyError as ex:
            raise ProtocolViolation(ex[0])
        return result

    def _get_metadata_value(self):
        r = self._get_text()
        if r == 'U':
            return
        if len(r) < 2 or r[1] != ' ':
            raise ProtocolViolation(r)
        if r[0] == 'T':
            return r[2:]
        elif r[0] == 'D':
            try:
                y, m, d = map(int, r[2:].split())
                return Date(y, m, d)
            except ValueError:
                raise ProtocolViolation(r)
        else:
            raise ProtocolViolation(r)

    def get_metadata(self, i, dict_type=dict):
        self._put('GET-METADATA %d' % i)
        r = self._get_reply()
        if not r.startswith('OK '):
            raise ProtocolViolation(r)
        try:
            n = int(r[3:])
        except ValueError:
            raise ProtocolViolation(r)
        result = dict_type(
            (key, value)
            for i in range(n)
            for key in [self._get_text()]
            for value in [self._get_metadata_value()]
        )
        return result

    def sort(self, column_type, atergo=False, ascending=True, timeout=None):
        sort_id = column_type.sort_id[atergo]
        if ascending:
            sort_id = sort_id.upper()
        else:
            sort_id = sort_id.lower()
        if self._sort_status != JOB_RUNNING:
            self._sort_status = JOB_NO
            self._put('SORT-RESULTS %s' % sort_id)
            r = self._get_reply()
            if r != 'OK':
                raise ProtocolViolation(r)
            self._sort_id = sort_id
            if self._sort_status != JOB_DONE:
                self._sort_status = JOB_RUNNING
        else:
            if self._sort_id != sort_id:
                raise Busy
        self._get_async_message(timeout=timeout)
        if self._sort_status != JOB_DONE:
            raise ProtocolViolation
        return True

    def get_buffer_state(self):
        self._put('GET-BUFFER-STATE')
        r = self._get_reply()
        if not r.startswith('OK '):
            raise ProtocolViolation(r)
        try:
            capacity, used = map(int, r[3:].split(None, 1))
        except ValueError:
            raise ProtocolViolation(r)
        return capacity, used

    def shift_buffer(self, n):
        raise NotImplementedError

    def resize_buffer(self, n):
        self._put('RESIZE-BUFFER %d' % n)
        r = self._get_reply()
        if not r == 'OK':
            raise ProtocolViolation(r)
        self._n_stored_results = None

    def _set_option(self, name, value):
        self._put('SET-OPTION %s %s' % (name, value))
        r = self._get_reply()
        if r != 'OK':
            raise ProtocolViolation(r)

    def set_left_context_width(self, value):
        self._set_option('left-context-width', int(value))

    def set_right_context_width(self, value):
        self._set_option('right-context-width', int(value))

    def set_wide_context_width(self, value):
        self._set_option('wide-context-width', int(value))

    def set_retrieve_lemmata(self, left_context=False, left_match=False, right_context=False, right_match=False):
        value = ''.join(str(0 + bool(x)) for x in
            (left_context, left_match, right_context, right_match)
        )
        self._set_option('retrieve-lemmata', value)
        self._column_types = None

    def set_retrieve_tags(self, left_context=False, left_match=False, right_context=False, right_match=False):
        value = ''.join(str(0 + bool(x)) for x in
            (left_context, left_match, right_context, right_match)
        )
        self._set_option('retrieve-tags', value)
        self._column_types = None

    def set_retrieve_ids(self, left_context=False, left_match=False, right_context=False, right_match=False):
        value = ''.join(str(0 + bool(x)) for x in
            (left_context, left_match, right_context, right_match)
        )
        self._set_option('retrieve-ids', value)
        self._column_types = None

    def set_notification_interval(self, value):
        value = int(value)
        self._set_option('notification-interval', value)

    def set_query_flags(self, query_case_sensitive=True, query_whole_words=False, metadata_case_sensitive=False, metadata_whole_words=True):
        value = ''.join(str(0 + bool(x)) for x in
            (not query_case_sensitive,
            query_whole_words,
            not metadata_case_sensitive,
            metadata_whole_words)
        )
        self._set_option('query-flags', value)


    def set_disamb(self, value=True):
        self._set_option('disamb', 0 + bool(value))

    def set_rewrite(self, value):
        self._set_option('rewrite', value)

    def set_random_sample(self, value):
        self._set_option('random-sample', 0 + bool(value))

    def create_alias(self, name, value):
        raise NotImplementedError

    def delete_alias(self, name):
        raise NotImplementedError

    def get_aliases(self):
        raise NotImplementedError

    def get_tagset(self):
        self._put('GET-TAGSET')
        r = self._get_reply()
        if not r.startswith('OK '):
            raise ProtocolViolation(r)
        try:
            n_categories, n_classes = map(int, r[3:].split(None, 1))
        except ValueError:
            raise ProtocolViolation(r)
        categories = {}
        classes = {}
        for i in range(n_categories):
            r = self._get_reply()
            key, value = r.split(None, 1)
            value = frozenset(value.split())
            categories[key] = value
        for i in range(n_classes):
            r = self._get_reply()
            try:
                key, value = r.split(None, 1)
            except ValueError:
                key = r
                value = ()
            else:
                value = tuple(value.split())
            classes[key] = value
        return (categories, classes)

    def get_column_types(self):
        if self._column_types is not None:
            return self._column_types
        self._put('GET-COLUMN-TYPES')
        r = self._get_reply()
        if not r.startswith('OK '):
            raise ProtocolViolation(r)
        types = r[3:].split(':')
        types = (re.match('^([LR]C|[LR]?M)<(l?t?i?)>$', tp).groups() for tp in types)
        result = tuple(
            dict(
                LC = LeftContextType,
                LM = LeftMatchType,
                M  = MatchType,
                RM = RightMatchType,
                RC = RightContextType
            )[id](has_tags = 't' in flags, has_lemmata = 'l' in flags, has_ids = 'i' in flags)
            for id, flags in types
        )
        self._column_types = result
        return result

    def get_last_error(self):
        self._put('GET-LAST-ERROR')
        r = self._get_reply()
        if r.startswith('ERROR '):
            return r[6:]
        elif r == 'NOERROR':
            return None
        else:
            raise ProtocolViolation(r)

    def set_locale(self, locale):
        self._put('SET-LOCALE %s' % locale);
        r = self._get_reply()
        if r != 'OK':
            raise ProtocolViolation(r)

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        self.close()

    def close(self):
        if self._socket is None:
            return
        self._socket.close()
        self._socket = None
        self._file = None

class ColumnType(object):

    def __init__(self, has_tags=False, has_lemmata=False, has_ids=False):
        self.has_tags = has_tags
        self.has_lemmata = has_lemmata
        self.has_ids = has_ids

    def __repr__(self):
        return '%s(%s)' % (
            self.__class__.__name__,
            ','.join(sorted(
                '%s=%s' % (key, value)
                for key, value in vars(self).items()
                if key.startswith('has_')
            ))
        )

class ContextType(ColumnType):
    is_context = True
    is_match = False

class MatchType(ColumnType):
    is_context = False
    is_match = True
    is_left = None

class LeftMatchType(MatchType):
    sort_id = 'b', 'f'
    is_left = True
    is_right = False

class RightMatchType(MatchType):
    sort_id = 'c', 'g'
    is_right = True
    is_left = False

class LeftContextType(ContextType):
    sort_id = 'a', 'e'
    is_left = True
    is_right = False

class RightContextType(ContextType):
    sort_id = 'd', 'h'
    is_right = True
    is_left = False

class Segment(object):

    def __init__(self, orth, interps=None, id=None):
        self.id = id
        self.orth = orth
        if interps is None:
            self.interps = None
        else:
            self.interps = list(interps)

    def add_interp(self, lemma=None, tag=None, nth=None):
        if self.interps is None:
            raise ValueError
        self.interps += Interp(lemma=lemma, tag=tag),

    def __repr__(self):
        return '%s(%s)' % (self.__class__.__name__, ', '.join(
            '%s=%r' % (key, value)
            for key in ('id', 'orth', 'interps')
            for value in (getattr(self, key),) if value is not None
        ))

class Interp(object):

    def __init__(self, lemma=None, tag=None):
        self.lemma = lemma
        self.tag = tag

    def __repr__(self):
        return '%s(%s)' % (self.__class__.__name__, ', '.join(
            '%s=%r' % (key, value)
            for key in ('lemma', 'tag')
            for value in (getattr(self, key),) if value is not None
        ))

# vim:ts=4 sw=4 et