# -*- encoding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2004-2006 TINY SPRL. (http://tiny.be) All Rights Reserved.
# Copyright (c) 2007-2010 Albert Cervera i Areny <albert@nan-tic.com>
# Copyright (c) 2010,2012-2013 P. Christeas <xrg@linux.gr>
# Copyright (c) 2010 OpenERP (http://www.openerp.com )
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################

from threading import Condition
import time

#.apidoc title: utils - Utility classes

class Pool(object):
    """ A pool of resources, which can be requested one at-a-time

        Since v0.3 the pool holds timestamps of *free* resources, so that
        they can easily be discarded.

        Usage with indexed resources
        ----------------------------

        If `filter_fn`, `setter_fn` and optionally `limit` are set, then
        the resource pool may resemble a dictionary, where any arbitrary
        condition on the resource can group them together.

        `filter_fn` will be used to only return a specific "kind" of res.
        upon a call to `borrow()`

        `setter_fn` will be used to set that "kind" on a new resource, after
        a call to iter_constr.next()

        `limit` may help to limit the number of available resources, 
        per "kind". However, if `limit` is used without `filter_fn()`, then
        the limit will be a Pool-wide one.
    """

    def __init__(self, iter_constr, check_fn=None, filter_fn=None, setter_fn=None, limit=False):
        """ Init the pool

            @param iter_constr is an iterable, that can construct a new
                resource in the pool. It will be called lazily, when more
                resources are needed
            @param check_fn A callable to use before borrow or after free,
                which will let discard "bad" resources. If check_fn(res)
                returns False, res will be removed from our lists.
            @param filter_fn If set, a callable that will be called like:
                `filter_fn(resource,**kwargs)` , where `kwargs` are the ones
                supplied to `borrow()` and used to select /valid/ resources
                for that `borrow()` call. See. `Usage with indexed resources`
            @param setter_fn Strongly advised to use together with `filter_fn`,
                in order to initialize new resource with our index.
                Also called like: `setter_fn(resource, **kwargs)` in borrow
            @param limit If set, a positive integer of max resources that can
                be allowed in "used" list, before call to `borrow()` will fail.
                `limit` does use the `filter_fn`, if the latter is set, to
                apply the limitation only to similar resources.
        """
        self.__free_ones = [] #: list of (resource, time) tuples
        self.__used_ones = []
        self.__lock = Condition()
        self.__iterc = iter_constr
        assert self.__iterc
        self.__check_fn = check_fn
        self._filter_fn = filter_fn
        self._setter_fn = setter_fn
        self._limit = limit

    def borrow(self, blocking=False, **kwargs):
        """Return the next free member of the pool
        """
        self.__lock.acquire()
        t2 = 0.0
        while(True):
            ret = None
            idx = len(self.__free_ones)
            while (idx > 0):
                idx -= 1
                if self._filter_fn:
                    # Wrap around try block, because we want to test with the
                    # lock acquired(), but must release on exception
                    try:
                        if not self._filter_fn(self.__free_ones[idx][0], **kwargs):
                            continue
                    except:
                        self.__lock.release()
                        raise
                ret, tstamp = self.__free_ones.pop(idx)
                if self.__check_fn is not None:
                    self.__lock.release()
                    if not self.__check_fn(ret):
                        ret = None
                    # An exception will also propagate from here,
                    # with the lock released
                    self.__lock.acquire()
                if ret is None:
                    continue # the while loop. Ret is at no list any more
                self.__used_ones.append(ret)
                self.__lock.release()
                return ret

            count = 0
            # Before constructing a new one, count the limit
            try:
                if self._limit:
                    for res in self.__used_ones:
                        if self._filter_fn and not self._filter_fn(res, **kwargs):
                            continue
                        count += 1
            except:
                self.__lock.release()
                raise

            # no free one, try to construct a new one
            try:
                self.__lock.release()
                if self._limit and (count >= self._limit):
                    raise StopIteration()

                ret = self.__iterc.next()
                if ret is not None and self._setter_fn:
                    self._setter_fn(ret, **kwargs)

                # the iterator may temporarily return None, which
                # means we should wait and retry the operation.
                self.__lock.acquire()
                if ret is not None:
                    self.__used_ones.append(ret)
                    self.__lock.release()
                    return ret
            except StopIteration:
                if not blocking:
                    raise ValueError("No free resource")
                # else pass
                self.__lock.acquire()

            idx = len(self.__free_ones) # reset counter, scan all of them after waiting
            if isinstance(blocking, (int, float)):
                twait = blocking - t2
            else:
                twait = None
            if (not twait) and not len(self.__free_ones):
                twait = 10.0 # must continue cycle at some point!
            if twait > 0.0:
                t1 = time.time()
                self.__lock.wait(twait) # As condition
                t1 = time.time() - t1
            if ((twait - t2) < 0) and not len(self.__free_ones):
                self.__lock.release()
                raise ValueError("Timed out waiting for a free resource")
            t2 += t1
            continue

        raise RuntimeError("Should never reach here")

    def free(self, res):
        self.__lock.acquire()
        try:
            self.__used_ones.remove(res)
        except ValueError:
            self.__lock.release()
            raise RuntimeError("Strange, freed pool item that was not in the list")
        if self.__check_fn is not None:
            self.__lock.release()
            if not self.__check_fn(res):
                res = None
                # not append to free ones, but issue notification
            # An exception will also propagate from here,
            # with the lock released
            self.__lock.acquire()
        if res is not None:
            self.__free_ones.append((res, time.time()))
        self.__lock.notify_all()
        self.__lock.release()

    def push_used(self, res):
        """ Register a foreign resource as a used one, in the pool.
        """
        self.__lock.acquire()
        if (res in self.__used_ones):
            self.__lock.release()
            raise RuntimeError("Resource already in pool")
        for r, t in self.__free_ones:
            if res == r:
                self.__lock.release()
                raise RuntimeError("Resource already in pool")
        self.__used_ones.append(res)
        self.__lock.release()

    def __len__(self):
        return len(self.__free_ones) + len(self.__used_ones)

    def __nonzero__(self):
        return True

    def count_free(self):
        return len(self.__free_ones)

    def clear(self):
        """ Forgets about all resources.
        Warning: if you ever use this function, you must make sure that
        the iterable will catch up and restart iteration with more resources
        """
        self.__lock.acquire()
        self.__free_ones = []
        self.__used_ones = []
        self.__lock.notify_all() # Let them retry
        self.__lock.release()

    def expire(self, age=30.0):
        """Forgets (deletes) resources that are older than `age` seconds

            The age of a resource is measured as the time this has been
            idle in the "free_ones" pool. It does not depend on the object
            creation time or so.
        """
        self.__lock.acquire()
        try:
            if self.__free_ones:
                alz = time.time() - age
                self.__free_ones = filter(lambda rt: rt[1] > alz, self.__free_ones)
        finally:
            self.__lock.release()

#eof
