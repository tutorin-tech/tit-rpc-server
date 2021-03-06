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
# limitations under the License

import uuid

import aiodocker


class Docker:
    def __init__(self):
        self._client = aiodocker.Docker()
        self._container = None
        self._name = f'tit-{uuid.uuid4()}'

    async def start(self, env):
        config = {
            'Image': 'tutorin.tech/student-tutor-ubuntu',
            'HostConfig': {
                'NetworkMode': 'host',
                'StorageOpt': {
                    'size': '150M',
                },
                # Limits a container to 128M of the memory.
                'Memory': 134217728,
                'MemorySwap': 134217728,
                # Limits a container to 25% of the CPU resources.
                'CpuPeriod': 100000,
                'CpuQuota': 25000,
            },
            'Env': env,
        }
        self._container = await self._client.containers.create(config=config, name=self._name)
        await self._container.start()

    async def stop(self):
        try:
            await self._container.stop()
            await self._container.delete(force=True)
        except AttributeError:
            pass  # an attempt to stop a container which isn't running yet

        await self._client.close()

