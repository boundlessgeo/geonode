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

import traceback
import os
import time
import shutil
import requests
import helpers
import tempfile
import simplejson as json
import ConfigParser

from optparse import make_option

from geonode.utils import designals, resignals

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

logger = helpers.logger


class Command(BaseCommand):

    help = 'Restore the GeoNode application data'

    option_list = BaseCommand.option_list + (
        make_option(
            '-i',
            '--ignore-errors',
            action='store_true',
            dest='ignore_errors',
            default=False,
            help='Stop after any errors are encountered.'
        ),
        make_option(
            '-f',
            '--force',
            action='store_true',
            dest='force_exec',
            default=False,
            help='Forces the execution without asking for confirmation.'
        ),
        make_option(
            '--backup-file',
            dest='backup_file',
            type="string",
            help='Backup archive containing GeoNode data to restore.'
        ),
        make_option(
            '--config_file',
            dest='config_file',
            type="string",
            help='Configuration file to read extra settings from.',
            default=os.path.join(os.path.abspath(os.path.dirname(__file__)), 'settings.ini')
        ),
        make_option(
            '--clean_data_db',
            dest='clean_data_db',
            action='store_true',
            default=True,
            help='If we should drop all existing data in our data/ogc database before restoring.',
        ),
        make_option(
            '--clean_django_db',
            dest='clean_django_db',
            action='store_true',
            default=False,
            help='If we should clear most existing data from the django database before importing the fixtures.',
        )
    )

    def handle(self, **options):
        # ignore_errors = options.get('ignore_errors')
        force_exec = options.get('force_exec')
        backup_file = options.get('backup_file')
        self.clean_data_db = options.get('clean_data_db')
        self.clean_django_db = options.get('clean_django_db')
        config_file = options.get('config_file')
        config = ConfigParser.ConfigParser()
        config.read(config_file)

        self.pg_restore_cmd = config.get('database', 'pgrestore')
        self.app_names = map(str.strip, config.get('fixtures', 'apps').split(','))
        self.dump_names = map(str.strip, config.get('fixtures', 'dumps').split(','))

        if not backup_file or len(backup_file) == 0:
            raise CommandError("Backup archive '--backup-file' is mandatory")

        message = 'WARNING: The restore may overwrite ALL GeoNode data. Do you want to proceed?'
        if force_exec or helpers.confirm(prompt=message, resp=False):
            # Create Target Folder
            restore_folder = os.path.join(tempfile.gettempdir(), 'restore')
            if not os.path.exists(restore_folder):
                os.makedirs(restore_folder)

            # Extract ZIP Archive to Target Folder
            self.target_folder = helpers.unzip_file(backup_file, restore_folder)

            # Restore GeoServer Catalog
            self.url = settings.OGC_SERVER['default']['PUBLIC_LOCATION'].strip('/')
            user = settings.OGC_SERVER['default']['USER']
            passwd = settings.OGC_SERVER['default']['PASSWORD']
            self.client = requests.session()
            self.client.auth = (user, passwd)

            self.restore_geoserver_config()
            self.restore_geogig_config()
            self.restore_geoserver_data()
            self.restore_postgres()
            self.restore_django()

            shutil.rmtree(restore_folder)
            logger.info("Restore finished")

    def restore_django(self):
        # Prepare Target DB

        logger.info("Restoring django")
        django_db_obj = settings.DATABASES['default']
        db_name = django_db_obj['NAME']
        db_user = django_db_obj['USER']
        db_port = django_db_obj['PORT']
        db_host = django_db_obj['HOST']
        db_passwd = django_db_obj['PASSWORD']

        schema_name = 'public'

        if 'OPTIONS' in django_db_obj and 'options' in django_db_obj['OPTIONS']:
            search_path = django_db_obj['OPTIONS']['options'].split('=')[-1]
            schema_name = search_path.split(',')[0]

        if self.clean_django_db:
            try:
                call_command('flush', interactive=False, load_initial_data=False)
                call_command('migrate', interactive=False, load_initial_data=False)
            except:
                traceback.print_exc()

        helpers.patch_db(db_name, db_user, db_port, db_host, db_passwd, schema=schema_name)

        try:
            # Deactivate GeoNode Signals
            designals()

            # Restore Fixtures
            for dump_name in self.dump_names:
                fixture_file = os.path.join(self.target_folder, dump_name+'.json')

                try:
                    call_command('loaddata', fixture_file)
                except:
                    traceback.print_exc()
                    logger.warning("Django fixture {} can't be restored".format(dump_name))

            # Restore Media Root
            media_root = settings.MEDIA_ROOT
            media_folder = os.path.join(self.target_folder, helpers.MEDIA_ROOT)

            try:
                shutil.rmtree(media_root)
            except:
                pass

            if not os.path.exists(media_root):
                os.makedirs(media_root)

            helpers.copy_tree(media_folder, media_root)
            helpers.chmod_tree(media_root)

            # Cleanup DB
            try:
                helpers.cleanup_db(db_name, db_user, db_port, db_host, db_passwd, schema=schema_name)
            except:
                traceback.print_exc()

        finally:
            # Reactivate GeoNode Signals
            resignals()
            logger.info("Django restore complete")

    def restore_geoserver_config(self):
        backup_file = os.path.join(self.target_folder, 'geoserver_catalog.zip')
        logger.info("Restoring Geoserver configuration")

        if not os.path.exists(backup_file):
            raise ValueError('Could not find GeoServer Backup file {}'.format(backup_file))

        data = {
            'restore': {
                'archiveFile': backup_file,
                'options': {
                    'option': [
                        'BK_BEST_EFFORT=true'
                    ]
                }
            }
        }

        headers = {'Content-type': 'application/json'}
        restore_url = '{}/rest/br/restore'.format(self.url)
        resp = self.client.post(restore_url, data=json.dumps(data), headers=headers)

        if resp.status_code == 201:
            restore_obj = resp.json()
            job_id = restore_obj['restore']['execution']['id']
            job_id_url = '{restore_url}/{job_id}.json'.format(restore_url=restore_url, job_id=job_id)
            resp = self.client.get(job_id_url)

            if resp.status_code == 200:
                job_status = restore_obj['restore']['execution']['status']

                while job_status != 'COMPLETED':
                    if job_status == 'FAILED':
                        raise ValueError("Geoserver restore failed: {status} - {error}".format(
                                           status=resp.status_code, error=resp.text))

                    resp = self.client.get(job_id_url)
                    if resp.status_code == 200:
                        restore_obj = resp.json()
                        job_status = restore_obj['restore']['execution']['status']
                        time.sleep(3)
                    else:
                        raise ValueError("Geoserver restore failed: {status} - {error}".format(
                                           status=resp.status_code, error=resp.text))
                print "Geoserver configuration restore was successful"
            else:
                raise ValueError("Geoserver restore failed: {status} - {error}".format(
                                           status=resp.status_code, error=resp.text))
        else:
            raise ValueError('Failed to restore Geoserver backup: {status} - {error}'.format(
                               status=resp.status_code, error=resp.text))
        logger.info("Geoserver configuration restore is complete")

    def restore_geogig_config(self):
        backup_dir = os.path.join(self.target_folder, 'gs_data/geogig_repos')
        if os.path.exists(backup_dir):
            backup_files = [os.path.join(backup_dir, f) for f in os.listdir(backup_dir)
                            if os.path.isfile(os.path.join(backup_dir, f))]

            for f in backup_files:
                obj_url = "{base_url}/rest/resource/geogig/config/repos/{repo_id}".format(
                          base_url=self.url, repo_id=os.path.basename(f))

                headers = {'Content-type': 'application/xml'}
                resp = self.client.put(obj_url, data=open(f), headers=headers)
                if resp.status_code != 201:
                    raise ValueError('Failed to restore Geogig repo config {path}: {status} - {error}'.format(
                                       path=f, status=resp.status_code, error=resp.text))

            logger.info("Geoserver Geogig config restore complete")

    def restore_geoserver_data(self):
        # Restore GeoServer Data
        gs_backup_dir = os.path.join(self.target_folder, 'gs_data')
        json_file = os.path.join(gs_backup_dir, 'data_backup.json')
        data = None
        if os.path.isfile(json_file):
            logger.info("Restoring Geoserver data")
            with open(json_file) as f:
                data = json.load(f)

            if data is not None:
                headers = {'Content-type': 'application/xml'}
                base_url = "{}/rest/resource".format(self.url)
                for obj in data:
                    obj_url = "{base_url}{uri}".format(base_url=base_url, uri=obj['uri'])
                    obj_path = os.path.join(gs_backup_dir, obj['name'])
                    resp = self.client.put(obj_url, data=open(obj_path), headers=headers)

                    if resp.status_code != 201:
                        raise ValueError('Failed to restore Geoserver data {name}: {status} - {error}'.format(
                                           name=obj['name'], status=resp.status_code, error=resp.text))
            logger.info("Geoserver data restore complete")

    def restore_postgres(self):
        # Restore Vectorial Data from DB
        datastore = settings.OGC_SERVER['default']['DATASTORE']
        if datastore:
            ogc_db_obj = settings.DATABASES[datastore]

            ogc_db_name = ogc_db_obj['NAME']
            ogc_db_user = ogc_db_obj['USER']
            ogc_db_passwd = ogc_db_obj['PASSWORD']
            ogc_db_host = ogc_db_obj['HOST']
            ogc_db_port = ogc_db_obj['PORT']

            # schemas_to_restore = ['public']

            # if 'OPTIONS' in ogc_db_obj and 'options' in ogc_db_obj['OPTIONS']:
            #    search_path = ogc_db_obj['OPTIONS']['options'].split('=')[-1]
            #    schemas_to_restore = map(str.strip, search_path.split(','))

            dump_dir = os.path.join(self.target_folder, 'gs_data')
            included_extenstions = ['dump', 'sql']
            backup_files = [os.path.join(dump_dir, fn) for fn in os.listdir(dump_dir)
                            if any(fn.endswith(ext) for ext in included_extenstions)]

            if backup_files:
                logger.info("Restoring data/ogc database")
                helpers.restore_db(
                    ogc_db_name,
                    ogc_db_user,
                    ogc_db_passwd,
                    backup_files,
                    self.pg_restore_cmd,
                    ogc_db_port,
                    ogc_db_host,
                    self.clean_data_db
                )

                logger.info("data/ogc database restore complete")
