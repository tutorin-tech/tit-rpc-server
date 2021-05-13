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

import json
from urllib.parse import urljoin

from tornado.httpclient import AsyncHTTPClient, HTTPError

from tutorin_tech.rpc.exceptions import CourseDoesNotExist
from tutorin_tech.rpc.settings import TIT_API_HOST


async def request_course(course_id):
    """Requests a course by its id using the TiT API. """

    http_client = AsyncHTTPClient()
    try:
        url = urljoin(TIT_API_HOST, f'/api/course/{course_id}')
        response = await http_client.fetch(url)
    except (HTTPError, ConnectionRefusedError, ) as exc:
        raise CourseDoesNotExist from exc

    raw_course = response.body.decode('utf-8')
    return json.loads(raw_course)
