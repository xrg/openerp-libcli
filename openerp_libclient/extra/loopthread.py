# -*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright 2011 P. Christeas
#    Author (blame me): P. Christeas <xrg@hellug.gr>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################


#.apidoc title: Utility looping thread

import threading

class LoopThread(threading.Thread):
    """ A thread that performs a periodic task.

        It will call its target() or self.loop_once(), then wait, then call
        again.
        By default, it will be a `deamon` thread, meaning that will not
        block the application from exiting. Otherwise, standard `Thread`
        methods apply.
    """

    def __init__(self, period, group=None, target=None, name=None, args=(), kwargs={}):
        """Initialize the thread,

            @param period seconds to wait between calls of the loop function

        """
        assert isinstance(period, (int, float)), period
        if target:
            self.__target_fn = target
            self.__fn_args = args
            self.__fn_kwargs = kwargs
        else:
            self.__target_fn = self.loop_once
            self.__fn_args = ()
            self.__fn_kwargs = {}

        self.__period = period

        threading.Thread.__init__(self, group=group, name=name)
        self.daemon = True
        self._must_stop = False
        self.__cond = threading.Condition()

    def loop_once(self):
        """ Perform one iteration
        """
        raise NotImplementedError

    def run(self):
        """ Performs the continuous loop of the algorighm
        
            Do *not* override this!
        """

        while not self._must_stop:
            self.__target_fn(*self.__fn_args, **self.__fn_kwargs)

            if self._must_stop:
                break

            self.__cond.acquire()
            self.__cond.wait(self.__period)
            self.__cond.release()

    def stop(self):
        """ Immediately stop the loop.

            If this thread is processing the target function, it will finish
            first, and then break the loop
        """
        self.__cond.acquire()
        self._must_stop = True
        self.__cond.notify_all()
        self.__cond.release()

    def trigger(self):
        """ Stop waiting and trigger an immediate run of the target()
        """
        self.__cond.acquire()
        self.__cond.notify_all()
        self.__cond.release()

#eof
