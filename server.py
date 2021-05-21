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

from tutorin_tech.rpc.api_client import request_course
from tutorin_tech.rpc.engine import Docker
from tutorin_tech.rpc.exceptions import CourseDoesNotExist, WaitTimeout
from tutorin_tech.rpc.util import allocate_port, wait_for_it


BUF_SIZE = 65536

READY_CODE = 0
FAILED_CODE = 1
COURSE_DOES_NOT_EXIST_CODE = 2


class Application(tornado.web.Application):
    def __init__(self):
        handlers = [
            (r'/rpc/token/' + TOKEN_PATTERN, TITRPCServer),
        ]

        super().__init__(handlers)


class LessonIsInvalid(Exception):
    pass


class TITRPCServer(RPCServer):
    def __init__(self, application, request, **kwargs):
        super().__init__(application, request, **kwargs)

        self._engine = Docker()

        self._student_fd = self._tutor_fd = None
        self._student_pid = self._tutor_pid = None

        self._ssh_port = allocate_port()

        self._course = None
        self._pointer = 0
        self._len = 0

    @property
    def _current_lesson(self):
        return self._course['lessons'][self._pointer]

    def _fork_pty(self, username):
        pid, fd = pty.fork()
        if pid == 0:  # child
            command_line = [
                'ssh',
                '-o', 'LogLevel=quiet',
                '-o', 'StrictHostKeyChecking=no',
                '-p', str(self._ssh_port),
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
    async def get_course(self, request, course_id):
        if not self._course:
            try:
                self._course = await request_course(course_id)
            except CourseDoesNotExist:
                return COURSE_DOES_NOT_EXIST_CODE

            self._len = len(self._course['lessons']) - 1  # do not count the introduction

        return self._course

    @remote
    async def next(self, request):
        self._pointer += 1

        try:
            return self._form_response(lesson=self._current_lesson)
        except IndexError:
            self._pointer -= 1
            raise LessonIsInvalid

    @remote
    async def seek(self, request, lesson_n):
        if lesson_n < 1:  # do not allow switching to the introduction
            raise LessonIsInvalid

        try:
            self._pointer = lesson_n
            return self._form_response(lesson=self._current_lesson)
        except IndexError:
            raise LessonIsInvalid

    @remote
    async def start(self, request):
        env = [f'PORT={self._ssh_port}']
        await self._engine.start(env)

        try:
            await wait_for_it(self._ssh_port, 30)
        except WaitTimeout:
            return FAILED_CODE

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

    @remote
    async def enter(self, request, data):
        try:
            os.write(self._student_fd, data.encode('utf8'))
        except (IOError, OSError):
            await self.destroy()


def main():
    options.parse_command_line()
    IOLoop().start(Application(), 8000)


if __name__ == '__main__':
    main()
