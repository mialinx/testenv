# -*- coding: utf-8 -*-

from .memcached import Memcached    # noqa
from .mysql import MySQL            # noqa
from .redis import Redis            # noqa
from ..server import GenericServer  # noqa
from .tarantool import Tarantool    # noqa
from .uwsgi import Uwsgi            # noqa


Generic = GenericServer  # shortcut
