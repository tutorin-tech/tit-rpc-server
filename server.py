#!/usr/bin/env python3
# Copyright 2021 Evgeny Golyshev. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import pty
import signal

import tornado.web
import tornado.websocket
from tornado.options import options

from shirow.ioloop import IOLoop
from shirow.server import RPCServer, TOKEN_PATTERN, remote


BUF_SIZE = 65536


class Application(tornado.web.Application):
    def __init__(self):
        handlers = [
            (r'/rpc/token/' + TOKEN_PATTERN, TITRPCServer),
        ]

        super().__init__(handlers)


class StepIsOutOfRange(Exception):
    pass


class TITRPCServer(RPCServer):
    def __init__(self, application, request, **kwargs):
        super().__init__(application, request, **kwargs)

        self._student_fd = self._tutor_fd = None
        self._student_pid = self._tutor_pid = None

        self._pointer = 0
        self._steps = [
            {
                'name': "'cat' command",
                'desc': "This section describes how to use the 'cat' command.",
            },
            {
                'name': "'ls' command",
                'desc': "This section describes how to use the 'ls' command.",
            },
            {
                'name': "'ps' command",
                'desc': "This section describes how to use the 'ps' command.",
            },
        ]
        self._len = len(self._steps)

    def _fork_pty(self):
        pid, fd = pty.fork()
        if pid == 0:  # child
            command_line = ['echo', 'Hello, World!', ]
            os.execvp(command_line[0], command_line)
        else:  # parent
            return pid, fd

    def destroy(self):
        """TODO: implement. """

    @remote
    async def back(self, request):
        if self._pointer:
            self._pointer -= 1

        step = self._steps[self._pointer]

        return {
            'n': self._pointer + 1,
            'outof': self._len,
            'step': step,
        }

    @remote
    async def list_steps(self, request):
        return self._steps

    @remote
    async def next(self, request):
        self._pointer += 1

        try:
            step = self._steps[self._pointer]
        except IndexError:
            self._pointer -= 1
            raise StepIsOutOfRange

        return {
            'n': self._pointer + 1,
            'outof': self._len,
            'step': step,
        }

    @remote
    async def seek(self, request, step_n):
        try:
            step = self._steps[step_n - 1]
            self._pointer = step_n - 1
        except IndexError:
            raise StepIsOutOfRange

        return {
            'n': self._pointer + 1,
            'outof': self._len,
            'step': step,
        }

    @remote
    async def read_student_fd(self, request):
        self._student_pid, self._student_fd = self._fork_pty()

        def student_fd_handler(*_args, **_kwargs):
            try:
                data = os.read(self._student_fd, BUF_SIZE)
            except OSError:
                return

            request.ret_and_continue(data.decode('utf8'))

        self.io_loop.add_handler(self._student_fd, student_fd_handler, self.io_loop.READ)

    @remote
    async def read_tutor_fd(self, request):
        self._tutor_pid, self._tutor_fd = self._fork_pty()

        def tutor_fd_handler(*_args, **_kwargs):
            try:
                data = os.read(self._tutor_fd, BUF_SIZE)
            except OSError:
                return

            request.ret_and_continue(data.decode('utf8'))

        self.io_loop.add_handler(self._tutor_fd, tutor_fd_handler, self.io_loop.READ)


def main():
    options.parse_command_line()
    IOLoop().start(Application(), 8000)


if __name__ == '__main__':
    main()
