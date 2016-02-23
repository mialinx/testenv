# -*- coding: utf-8 -*-

from .mysql import MySQL
from .tarantool import Tarantool
from .uwsgi import Uwsgi
from .memcached import Memcached
from .redis import Redis
from ..server import GenericServer

Generic = GenericServer # shortcut
