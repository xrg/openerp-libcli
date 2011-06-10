# -*- encoding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2004-2006 TINY SPRL. (http://tiny.be) All Rights Reserved.
# Copyright (c) 2007-2010 Albert Cervera i Areny <albert@nan-tic.com>
# Copyright (c) 2010 P. Christeas <p_christ@hol.gr>
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

class Pool(object):
    """ A pool of resources, which can be requested one at-a-time
    """
    
    def __init__(self, iter_constr, check_fn=None):
        """ Init the pool
            @param iter_constr is an iterable, that can construct a new
                resource in the pool. It will be called lazily, when more
                resources are needed
            @param check_fn  A callable to use before borrow or after free,
                which will let discard "bad" resources. If check_fn(res)
                returns False, res will be removed from our lists.
        """
        self.__free_ones = []
        self.__used_ones = []
        self.__lock = Condition()
        self.__iterc = iter_constr
        assert self.__iterc
        self.__check_fn = check_fn
        
    def borrow(self, blocking=False):
        """Return the next free member of the pool
        """
        self.__lock.acquire()
        t2 = 0.0
        while(True):
            ret = None
            if len(self.__free_ones):
                ret = self.__free_ones.pop()
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
            
            # no free one, try to construct a new one
            try:
                self.__lock.release()
                ret = self.__iterc.next()
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
            self.__free_ones.append(res)
        self.__lock.notify_all()
        self.__lock.release()

    def push_used(self, res):
        """ Register a foreign resource as a used one, in the pool.
        """
        self.__lock.acquire()
        if (res in self.__used_ones) or (res in self.__free_ones):
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
