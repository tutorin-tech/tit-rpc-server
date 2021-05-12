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
import socket
from contextlib import closing

from tutorin_tech.rpc.exceptions import WaitTimeout


def allocate_port():
    """Allocates an available port. """

    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        sock.bind(('', 0))
        return sock.getsockname()[1]


async def wait_for_it(port, timeout):
    """Waits on the availability of the specified TCP port. """

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    for _ in range(timeout):
        try:
            sock.connect(('', port))
        except ConnectionRefusedError:
            await asyncio.sleep(1)
        else:
            sock.close()
            return

    raise WaitTimeout
