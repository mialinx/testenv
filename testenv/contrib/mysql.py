# -*- coding: utf-8 -*-

import os
import os.path
import subprocess
import shutil

from .. import server, utils

class MySQL(server.Server):

    mysqld_bin           = 'mysqld'
    mysql_install_db_bin = 'mysql_install_db'
    mysqladmin_bin       = 'mysqladmin'
    mysql_bin            = 'mysql'

    default_config = {
        'client': {},
        'mysqld': {
            'tmpdir'              : '/tmp',
            'lc-messages-dir'     : '/usr/share/mysql',
            'skip-external-locking' : '1',

            'key_buffer_size'     : '2M',
            'max_allowed_packet'  : '2M',
            'thread_stack'        : '192K',
            'thread_cache_size'   : '4',
            'myisam-recover'      : '0',
            'max_connections'     : '100',
            'table_cache'         : '64',
            'thread_concurrency'  : '10',

            'query_cache_limit'   : '256K',
            'query_cache_size'    : '4M',

            'general_log'         : '1',
            'slow_query_log'      : '1',
            'long_query_time'     : '1',
            'log-queries-not-using-indexes' : '1',
        },
        'innodb': {
            'innodb_buffer_pool_size'   : '8M',
            'innodb_read_io_threads'    : '2',
            'innodb_write_io_threads'   : '2',
            'innodb_io_capacity'        : '300',
            'innodb_log_file_size'      : '16M',
            'innodb_flush_log_at_trx_commit':  '2',
        }
    }


    def init(self, **kwargs):
        # main configuration
        assert 'config' in kwargs and type(kwargs['config']) == dict, \
            "mysql server requires <config> section"
        self.configfile = os.path.join(self.basedir, 'my.cnf')
        self.datadir = os.path.join(self.basedir, 'db')
        self.config = utils.merge(
            self.default_config,
            kwargs['config'],
            {
                'mysqld': {
                    'user':                 utils.user,
                    'datadir':              self.datadir,
                    'general_log_file':     os.path.join(self.basedir, 'mysql.log'),
                    'log_error':            os.path.join(self.basedir, 'error.log'),
                    'slow_query_log_file':  os.path.join(self.basedir, 'slow.log'),
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


    def prepare(self):
        super(MySQL, self).prepare()
        os.makedirs(self.datadir)
        utils.write_ini(self.configfile, self.config)

        # copy main file to avoid apparmor protection
        old_bin = utils.find_binary(self.mysqld_bin)
        if old_bin is None:
            raise Exception("failed to find mysqld binary: " + self.mysqld_bin)
        new_bin = os.path.join(self.basedir, 'mysqld')
        shutil.copyfile(old_bin, new_bin)
        shutil.copymode(old_bin, new_bin)
        self.mysqld_bin = new_bin

        p = subprocess.Popen([self.mysql_install_db_bin, '--defaults-file=' + self.configfile],
                stdout=open("/dev/null", "w"), env = {'MYSQLD_BOOTSTRAP': self.mysqld_bin })
        utils.wait_for_proc(p, name=self.mysql_install_db_bin)

        self.command = [ self.mysqld_bin, '--defaults-file=' + self.configfile ]


    def fill(self):
        subprocess.check_call([self.mysqladmin_bin, '--defaults-file=' + self.configfile, '-u', 'root', 'password', 'root'])

        sql = ''
        for db in self.databases:
            sql += "CREATE DATABASE `{name}` DEFAULT CHARACTER SET 'utf8';\n".format(**db)
        for u in self.users:
            sql += "CREATE USER '{name}'@'localhost' IDENTIFIED BY '{pass}';\n".format(**u)
            sql += "GRANT ALL PRIVILEGES ON {grant}.* TO '{name}'@'localhost';\n".format(**u)
            sql += "FLUSH PRIVILEGES;\n"
        p = subprocess.Popen([self.mysql_bin, '--defaults-file=' + self.configfile,
                    '--user=root', '--password=root'], stdin=subprocess.PIPE)
        p.communicate(sql)
        utils.wait_for_proc(p, name=self.mysql_bin)

        for db in self.databases:
            if 'scheme' not in db:
                continue
            if not isinstance(db['scheme'], list):
                db['scheme'] = [ db['scheme'], ]
            for scheme in db['scheme']:
                scheme = self.confpath(scheme)
                p = subprocess.Popen([self.mysql_bin, '--defaults-file=' + self.configfile,
                            '--user=root', '--password=root', db['name']], stdin=open(scheme, 'r'))
                utils.wait_for_proc(p, name=self.mysql_bin)

