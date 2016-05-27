# -*- coding: utf-8 -*-

import contextlib
import os
import os.path

from .. import server, utils


class Tarantool(server.Server):

    tarantool_bin = 'tarantool'
    start_timeout = 50

    default_config = {
        'background': True,
        'log_level': 5,
        'slab_alloc_arena': 0.03,
        'snapshot_period': 3 * 3600,
        'snapshot_count': 2,
    }

    def init(self, **kwargs):
        super(Tarantool, self).init(**kwargs)
        self.tarantool_bin = kwargs.get('tarantool_bin', self.tarantool_bin)
        self.configfile = os.path.join(self.basedir, 'tarantool.lua')
        self.pidfile = os.path.join(self.basedir, 'tarantool.pid')
        self.config = utils.merge(
            self.default_config,
            {
                'pid_file': self.pidfile,
                'logger': os.path.join(self.basedir, 'tarantool.log'),
                'work_dir': self.basedir,
            },
            kwargs['config'],
        )
        assert 'lua_script' in kwargs,  "tarantool server requires <lua_script> option"
        self.lua_script = self.confpath(kwargs['lua_script'])
        # assert os.path.exists(self.lua_script),
        if 'lua_path' in kwargs:
            self.lua_path = self.confpath(kwargs['lua_path'])
        else:
            lua_script_dir = os.path.dirname(os.path.abspath(self.lua_script))
            self.lua_path = os.path.join(lua_script_dir, '?.lua')
        self.listen = self.config.pop('listen', None)
        assert self.listen is not None, "listen option missed"
        self.address = self.listen.split(':')
        self.command = [ self.tarantool_bin, self.configfile ]

    def prepare(self):
        super(Tarantool, self).prepare()
        cfg = ''
        cfg += "package.path = '{0};' .. package.path\n".format(self.lua_path)
        cfg += "box.cfg({\n"
        for k, v in self.config.iteritems():
            cfg += k + ' = '
            if type(v) in (int, float):
                cfg += str(v)
            elif type(v) == bool:
                cfg += str(v).lower()
            else:
                cfg += '"' + str(v).replace('"', '\\"') + '"'
            cfg += ',\n'
        cfg += "})\n"
        cfg += "dofile('{0}')\n".format(self.lua_script)
        cfg += 'box.cfg({ listen = "' + str(self.listen) + '" })\n'
        with contextlib.closing(open(self.configfile, "w")) as fh:
            fh.write(cfg)

    def is_ready(self):
        res = utils.wait_for_socket(self.address, maxtime=0)
        return res
