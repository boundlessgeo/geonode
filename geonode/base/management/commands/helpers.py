# -*- coding: utf-8 -*-
#########################################################################
#
# Copyright (C) 2016 OSGeo
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
#########################################################################

from __future__ import with_statement
from contextlib import closing
from zipfile import ZipFile, ZIP_DEFLATED

import traceback
import psycopg2
import ConfigParser
import os
import sys
import time
import shutil
import logging

import json

MEDIA_ROOT = 'uploaded'
STATIC_ROOT = 'static_root'
STATICFILES_DIRS = 'static_dirs'
TEMPLATE_DIRS = 'template_dirs'
LOCALE_PATHS = 'locale_dirs'
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(name)-15s %(levelname)-8s %(lineno)d %(message)s',
    datefmt='%m-%d-%Y %H:%M:%S',
    filename="/var/log/geonode_restore.log",
    filemode='a'
)

console_logger = logging.StreamHandler()
console_logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(name)-10s: %(levelname)-8s %(message)s')
console_logger.setFormatter(formatter)
logging.getLogger('').addHandler(console_logger)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logger = logging.getLogger('logger')

config = ConfigParser.ConfigParser()
config.read(os.path.join(os.path.abspath(os.path.dirname(__file__)), 'settings.ini'))

migrations = config.get('fixtures', 'migrations').split(',')
manglers = config.get('fixtures', 'manglers').split(',')

sys.path.append(os.path.join(os.path.dirname(__file__), "lib"))


def get_db_conn(db_name, db_user, db_port, db_host, db_passwd):
    """Get db conn (GeoNode)"""
    db_host = db_host if db_host is not None else 'localhost'
    db_port = db_port if db_port is not None else 5432
    conn = psycopg2.connect(
        "dbname='%s' user='%s' port='%s' host='%s' password='%s'" % (db_name, db_user, db_port, db_host, db_passwd)
    )
    return conn


def patch_db(db_name, db_user, db_port, db_host, db_passwd, schema='public'):
    """Apply patch to GeoNode DB"""
    conn = get_db_conn(db_name, db_user, db_port, db_host, db_passwd)
    curs = conn.cursor()

    try:
        curs.execute("ALTER TABLE {}.base_contactrole ALTER COLUMN resource_id DROP NOT NULL".format(schema))
        curs.execute("ALTER TABLE {}.base_link ALTER COLUMN resource_id DROP NOT NULL".format(schema))
    except Exception:
        try:
            conn.rollback()
        except:
            pass

        traceback.print_exc()

    conn.commit()


def cleanup_db(db_name, db_user, db_port, db_host, db_passwd, schema='public'):
    """Remove spurious records from GeoNode DB"""
    conn = get_db_conn(db_name, db_user, db_port, db_host, db_passwd)
    curs = conn.cursor()

    try:
        curs.execute("DELETE FROM {}.base_contactrole WHERE resource_id is NULL;".format(schema))
        curs.execute("DELETE FROM {}.base_link WHERE resource_id is NULL;".format(schema))
    except Exception:
        try:
            conn.rollback()
        except:
            pass

        traceback.print_exc()

    conn.commit()


def dump_db(db_name, db_user, db_passwd, target_folder, db_port=5432,
            db_host='localhost', db_schemas=['public'], pg_dump_cmd='pg_dump'):
    """Dump Full DB into target folder"""
    conn = get_db_conn(db_name, db_user, db_port, db_host, db_passwd)
    curs = conn.cursor()

    for schema in db_schemas:
        try:
            # Limiting tables by owner is probably not the right thing.
            # Dumping the entire schema would probably be easier/safer
            curs.execute("""SELECT tablename from pg_tables where tableowner = '{db_user}'
                               and schemaname = '{schema}'""".format(db_user=db_user, schema=schema))
            tables = curs.fetchall()

            curs.execute("""select viewname from pg_views where schemaname = '{schema}'
                               and viewowner = '{db_user}'""".format(db_user=db_user, schema=schema))
            views = curs.fetchall()

            curs.execute("""select sequence_name from information_schema.sequences where
                               sequence_schema = '{schema}'""".format(schema=schema))
            sequences = curs.fetchall()
        except Exception:
            try:
                conn.rollback()
            except:
                pass

            traceback.print_exc()

        conn.commit()

        base_cmd = "PGPASSWORD='{passwd}' {pg_dump} -h {host} -p {port} -U {user} -Fc -b -d {db_name}".format(
                           passwd=db_passwd, pg_dump=pg_dump_cmd, host=db_host,
                           port=db_port, user=db_user, db_name=db_name)

        tables_cmd = ["-t {schema}.'\"{table}\"'".format(table=t[0], schema=schema) for t in tables]
        if views:
            views_cmd = ["-t {schema}.'\"{view}\"'".format(view=v[0], schema=schema) for v in views]
            [tables_cmd.append(v) for v in views_cmd]
        if sequences:
            sequences_cmd = ["-t {schema}.'\"{sequence}\"'".format(sequence=s[0], schema=schema) for s in sequences]
            [tables_cmd.append(s) for s in sequences_cmd]

        print "Dumping GeoServer vector data from postgres"
        backup_path = os.path.join(target_folder, "postgres_backup_{}.dump".format(schema))
        os.system("{base_cmd}  {backup_tables} -f {backup_path}".format(
                           base_cmd=base_cmd, backup_tables=" ".join(tables_cmd), backup_path=backup_path))


def restore_db(db_name, db_user, db_passwd, backup_files, pg_restore_cmd,
               db_port=5432, db_host='localhost', clean=True):
    """Restore Full DB into target folder"""
    for f in backup_files:
        print "Restoring GeoServer vector data : {}".format(f)
        base_cmd = "PGPASSWORD='{passwd}' {pg_restore} -h {host} -p {port} -U {user} -Fc -d {db_name}".format(
                           passwd=db_passwd, pg_restore=pg_restore_cmd, host=db_host,
                           port=db_port, user=db_user, db_name=db_name)
        if clean:
            base_cmd += ' -c'

        os.system("{base_cmd} {backup_file}".format(base_cmd=base_cmd, backup_file=f))


def load_fixture(apps, fixture_file, mangler=None, basepk=-1, owner="admin", datastore='', siteurl=''):

    fixture = open(fixture_file, 'rb')

    if mangler:
        objects = json.load(fixture, cls=mangler,
                            **{"basepk": basepk, "owner": owner, "datastore": datastore, "siteurl": siteurl})
    else:
        objects = json.load(fixture)

    fixture.close()

    return objects


def get_dir_time_suffix():
    """Returns the name of a folder with the 'now' time as suffix"""
    dirfmt = "%4d-%02d-%02d_%02d%02d%02d"
    now = time.localtime()[0:6]
    dirname = dirfmt % now

    return dirname


def zip_dir(basedir, archivename):
    assert os.path.isdir(basedir)
    with closing(ZipFile(archivename, "w", ZIP_DEFLATED)) as z:
        for root, dirs, files in os.walk(basedir):
            # NOTE: ignore empty directories
            for fn in files:
                absfn = os.path.join(root, fn)
                zfn = absfn[len(basedir)+len(os.sep):]  # XXX: relative path
                if absfn != archivename:
                    z.write(absfn, zfn)


def copy_tree(src, dst, symlinks=False, ignore=None):
    for item in os.listdir(src):
        s = os.path.join(src, item)
        d = os.path.join(dst, item)
        if os.path.isdir(s):
            # shutil.rmtree(d)
            if os.path.exists(d):
                os.remove(d)
            shutil.copytree(s, d, symlinks, ignore)
        else:
            shutil.copy2(s, d)


def unzip_file(zip_file, dst):
    target_folder = os.path.join(dst, os.path.splitext(os.path.basename(zip_file))[0])
    if not os.path.exists(target_folder):
        os.makedirs(target_folder)

    with ZipFile(zip_file, "r") as z:
        z.extractall(target_folder)

    return target_folder


def chmod_tree(dst, permissions=0o777):
    for dirpath, dirnames, filenames in os.walk(dst):
        for filename in filenames:
            path = os.path.join(dirpath, filename)
            os.chmod(path, permissions)

        for dirname in dirnames:
            path = os.path.join(dirpath, dirname)
            os.chmod(path, permissions)


def confirm(prompt=None, resp=False):
    """prompts for yes or no response from the user. Returns True for yes and
    False for no.

    'resp' should be set to the default value assumed by the caller when
    user simply types ENTER.

    >>> confirm(prompt='Create Directory?', resp=True)
    Create Directory? [y]|n:
    True
    >>> confirm(prompt='Create Directory?', resp=False)
    Create Directory? [n]|y:
    False
    >>> confirm(prompt='Create Directory?', resp=False)
    Create Directory? [n]|y: y
    True
    """

    if prompt is None:
        prompt = 'Confirm'

    if resp:
        prompt = '%s [%s]|%s: ' % (prompt, 'y', 'n')
    else:
        prompt = '%s [%s]|%s: ' % (prompt, 'n', 'y')

    while True:
        ans = raw_input(prompt)
        if not ans:
            return resp
        if ans not in ['y', 'Y', 'n', 'N']:
            print 'please enter y or n.'
            continue
        if ans == 'y' or ans == 'Y':
            return True
        if ans == 'n' or ans == 'N':
            return False


def load_class(name):

    components = name.split('.')
    mod = __import__(components[0])

    for comp in components[1:]:
        mod = getattr(mod, comp)

    return mod
