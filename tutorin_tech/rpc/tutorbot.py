# Copyright 2021 Denis Gavrilyuk. All Rights Reserved.
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
# limitations under the License

import asyncio
import os

from .exceptions import EndOfScriptException


class Tutorbot:
    def __init__(self, script):
        self._script = script

        self._row_pointer = 0
        self._col_pointer = 0

        self._pause = False

    def _cleanup(self):
        self._row_pointer = 0
        self._col_pointer = 0

    @property
    def _row(self):
        try:
            return self._script[self._row_pointer]
        except IndexError:
            self._cleanup()
            raise EndOfScriptException

    @property
    def _char(self):
        try:
            char = self._row[self._col_pointer]
            self._col_pointer += 1
        except IndexError:
            char = '\n'
            self._row_pointer += 1
            self._col_pointer = 0

        return char

    @property
    def _has_next_row(self):
        return self._row_pointer < len(self._script)

    @property
    def _timeout(self):
        timeout = 0.2
        if self._col_pointer == len(self._row):
            timeout = 1

        return timeout

    async def show_me_how(self, fd):
        self._pause = False

        while True:
            if self._pause:
                break  # Pause script execution

            try:
                os.write(fd, self._char.encode('utf-8'))

                if self._has_next_row:
                    await asyncio.sleep(self._timeout)
            except (IOError, OSError, ):
                break

    def pause(self):
        self._pause = True
