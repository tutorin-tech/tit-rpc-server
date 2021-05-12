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

import tornado.web
import tornado.websocket
from tornado import gen
from tornado.options import options
from tornado.websocket import WebSocketClosedError
from shirow.ioloop import IOLoop
from shirow.server import RPCServer, TOKEN_PATTERN, remote

from tutorin_tech.rpc.engine import Docker


BUF_SIZE = 65536

READY_CODE = 0


class Application(tornado.web.Application):
    def __init__(self):
        handlers = [
            (r'/rpc/token/' + TOKEN_PATTERN, TITRPCServer),
        ]

        super().__init__(handlers)


class StepIsInvalid(Exception):
    pass


class TITRPCServer(RPCServer):
    def __init__(self, application, request, **kwargs):
        super().__init__(application, request, **kwargs)

        self._engine = Docker()

        self._student_fd = self._tutor_fd = None
        self._student_pid = self._tutor_pid = None

        self._pointer = 0
        self._steps = [
            {
                'name': "intro",
                'desc': "This is the introduction.",
            },
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
        self._len = len(self._steps) - 1  # do not count the introduction

    def _fork_pty(self, username):
        pid, fd = pty.fork()
        if pid == 0:  # child
            command_line = [
                'ssh',
                '-o', 'LogLevel=quiet',
                '-o', 'StrictHostKeyChecking=no',
                '-p', '2222',
                f'{username}@127.0.0.1',
            ]
            os.execvp(command_line[0], command_line)
        else:  # parent
            return pid, fd

    def _form_response(self, **kwargs):
        response = {
            'n': self._pointer,
            'outof': self._len,
        }

        return {**response, **kwargs}

    async def destroy(self):
        await self._engine.stop()

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
            raise StepIsInvalid

        return self._form_response(step=step)

    @remote
    async def seek(self, request, step_n):
        if step_n < 1:  # do not allow switching to the introduction
            raise StepIsInvalid

        try:
            step = self._steps[step_n]
            self._pointer = step_n
        except IndexError:
            raise StepIsInvalid

        return self._form_response(step=step)

    @remote
    async def start(self, request):
        await self._engine.start()
        await gen.sleep(5)
        self._pointer = 1
        return READY_CODE

    @remote
    async def read_student_fd(self, request):
        self._student_pid, self._student_fd = self._fork_pty('student')

        def student_fd_handler(*_args, **_kwargs):
            try:
                data = os.read(self._student_fd, BUF_SIZE)
            except OSError:
                return

            try:
                request.ret_and_continue(data.decode('utf8'))
            except WebSocketClosedError:
                return

        self.io_loop.add_handler(self._student_fd, student_fd_handler, self.io_loop.READ)

    @remote
    async def read_tutor_fd(self, request):
        self._tutor_pid, self._tutor_fd = self._fork_pty('tutor')

        def tutor_fd_handler(*_args, **_kwargs):
            try:
                data = os.read(self._tutor_fd, BUF_SIZE)
            except OSError:
                return

            try:
                request.ret_and_continue(data.decode('utf8'))
            except WebSocketClosedError:
                return

        self.io_loop.add_handler(self._tutor_fd, tutor_fd_handler, self.io_loop.READ)


def main():
    options.parse_command_line()
    IOLoop().start(Application(), 8000)


if __name__ == '__main__':
    main()
