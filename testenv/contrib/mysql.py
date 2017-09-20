# -*- coding: utf-8 -*-

import os
import os.path
import re
import shutil
import subprocess
from distutils.version import LooseVersion

from .. import server, utils


class MySQL(server.Server):

    mysqld_bin           = 'mysqld'
    mysql_install_db_bin = 'mysql_install_db'
    mysqladmin_bin       = 'mysqladmin'
    mysql_bin            = 'mysql'

    default_config = {
        'client': {},
        'mysqld': {
            'tmpdir': '/tmp',
            'lc-messages-dir': '/usr/share/mysql',
            'skip-external-locking': '1',

            'key_buffer_size': '2M',
            'max_allowed_packet': '2M',
            'thread_stack': '192K',
            'thread_cache_size': '4',
            'max_connections': '100',

            'query_cache_limit': '256K',
            'query_cache_size': '4M',

            'general_log': '1',
            'slow_query_log': '1',
            'long_query_time': '1',
            'log-queries-not-using-indexes': '1',
        },
        'innodb': {
            'innodb_buffer_pool_size': '8M',
            'innodb_read_io_threads': '2',
            'innodb_write_io_threads': '2',
            'innodb_io_capacity': '300',
            'innodb_log_file_size': '16M',
            'innodb_flush_log_at_trx_commit': '2',
        }
    }

    def init(self, **kwargs):
        # main configuration
        assert 'config' in kwargs and type(kwargs['config']) == dict, \
            "mysql server requires <config> section"
        self.configfile = os.path.join(self.basedir, 'my.cnf')
        self.config = utils.merge(
            self.default_config,
            kwargs['config'],
            {
                'mysqld': {
                    'user':                 utils.user,
                    'datadir':              os.path.join(self.basedir, 'data'),
                    'general_log_file':     os.path.join(self.basedir, 'mysql.log'),
                    'log_error':            os.path.join(self.basedir, 'error.log'),
                    'slow_query_log_file':  os.path.join(self.basedir, 'slow.log'),
                    'init-file':            os.path.join(self.basedir, 'init.sql'),
                }
            }
        )

        # socket may be needed to us and other servers / scripts
        # so we need to honor user settings of mysqld.socket if exist
        if not self.config['mysqld']['socket']:
            self.config['mysqld']['socket'] = os.path.join(self.basedir, 'mysql.sock')
        self.config['client']['socket'] = self.config['mysqld']['socket']
        self.config['client']['port'] = self.config['mysqld']['port']
        self.address = self.config['mysqld']['socket']

        # binaries and scripts
        self.mysqld_bin           = kwargs.get('mysqld_bin', self.mysqld_bin)
        self.mysql_install_db_bin = kwargs.get('mysql_install_db_bin', self.mysql_install_db_bin)
        self.mysqladmin_bin       = kwargs.get('mysqladmin_bin', self.mysqladmin_bin)
        self.mysql_bin            = kwargs.get('mysql_bin', self.mysql_bin)

        # users and schemas
        self.databases = kwargs.get('databases', [])
        assert type(self.databases) == list, "<database> section should be a list"
        self.users = kwargs.get('users', [])
        assert type(self.users) == list, "<users> section should be a list"
        self.scheme2users = {}

    def prepare(self):
        super(MySQL, self).prepare()
        os.makedirs(self.config['mysqld']['datadir'])
        utils.write_ini(self.configfile, self.config)

        with open(os.path.join(self.basedir, 'init.sql'), "w") as fh:
            sql = ''
            for db in self.databases:
                sql += "CREATE DATABASE `{name}` DEFAULT CHARACTER SET 'utf8';\n".format(**db)
            for u in self.users:
                self.scheme2users[u['grant']] = [u['name'], u['pass']]
                sql += "CREATE USER '{name}'@'localhost' IDENTIFIED BY '{pass}';\n".format(**u)
                sql += "GRANT ALL PRIVILEGES ON {grant}.* TO '{name}'@'localhost';\n".format(**u)
                sql += "FLUSH PRIVILEGES;\n"
            fh.write(sql)

        version = subprocess.check_output([self.mysqld_bin, '--version'])
        match = re.search(r'\d+\.\d+\.\d+', version)
        if match and LooseVersion(match.group(0)) >= LooseVersion('5.7.6'):
            p = subprocess.Popen([self.mysqld_bin, '--defaults-file=' + self.configfile, '--initialize'])
            utils.wait_for_proc(p, name=self.mysqld_bin)
        else:
            p = subprocess.Popen([self.mysql_install_db_bin, '--defaults-file=' + self.configfile])
            utils.wait_for_proc(p, name=self.mysql_install_db_bin)

        self.command = [ self.mysqld_bin, '--defaults-file=' + self.configfile ]

    def fill(self):
        for db in self.databases:
            if 'scheme' not in db:
                continue
            if not isinstance(db['scheme'], list):
                db['scheme'] = [ db['scheme'], ]
            for scheme in db['scheme']:
                user, password = self.scheme2users.get(db['name']) or ['', '']
                scheme = self.confpath(scheme)
                p = subprocess.Popen([self.mysql_bin, '--defaults-file=' + self.configfile,
                        '--user=' + user, '--password=' + password, db['name']], stdin=open(scheme, 'r'))
                utils.wait_for_proc(p, name=self.mysql_bin)
