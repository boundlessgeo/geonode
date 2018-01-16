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

try:
    import json
except ImportError:
    from django.utils import simplejson as json
import os
import time
import shutil
import requests
import helpers
import ConfigParser
from lxml import html

from optparse import make_option

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from geonode.utils import designals, resignals

logger = helpers.logger


class Command(BaseCommand):
    help = 'Backup the GeoNode application data'

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
            '--backup-dir',
            dest='backup_dir',
            type="string",
            help='Destination folder where to store the backup archive. It must be writable.'
        ),
        make_option(
            '--config_file',
            dest='config_file',
            type="string",
            help='Configuration file to read extra settings from.',
            default=os.path.join(os.path.abspath(os.path.dirname(__file__)), 'settings.ini')
        )
    )

    def handle(self, **options):
        # ignore_errors = options.get('ignore_errors')
        force_exec = options.get('force_exec')
        backup_dir = options.get('backup_dir')
        config = ConfigParser.ConfigParser()
        config.read(options.get('config_file'))

        self.pg_dump_cmd = config.get('database', 'pgdump')
        gs_dump_vector_data = config.getboolean('geoserver', 'dumpvectordata')
        gs_dump_raster_data = config.getboolean('geoserver', 'dumprasterdata')

        self.app_names = map(str.strip, config.get('fixtures', 'apps').split(','))
        self.dump_names = map(str.strip, config.get('fixtures', 'dumps').split(','))

        if not backup_dir or len(backup_dir) == 0:
            raise CommandError("Destination folder '--backup-dir' is mandatory")

        message = 'Do you want to proceed with geonode backup?'

        if force_exec or helpers.confirm(prompt=message, resp=False):
            # Create Target Folder
            dir_time_suffix = helpers.get_dir_time_suffix()
            self.target_folder = os.path.join(backup_dir, dir_time_suffix)
            if not os.path.exists(self.target_folder):
                os.makedirs(self.target_folder)

            ogc_server_obj = settings.OGC_SERVER['default']
            # Create GeoServer Backup
            self.url = ogc_server_obj['LOCATION'].strip('/')
            self.geoserver_bk_file = os.path.join(
                ogc_server_obj['GEOSERVER_DATA_DIR'],
                'geoserver_catalog.zip'
            )

            self.client = requests.session()
            self.client.auth = (
                ogc_server_obj['USER'],
                ogc_server_obj['PASSWORD']
            )

            # Dump GeoServer Data
            self.backup_geoserver_config()
            if gs_dump_raster_data:
                self.backup_geoserver_data()
            self.backup_geogig_config()
            # Dump vector/postgis data
            if gs_dump_vector_data:
                self.backup_postgres()
            # Dump Fixtures
            self.backup_django_fixtures()

            # Create Final ZIP Archive
            zip_name = "{}.zip".format(dir_time_suffix)
            helpers.zip_dir(self.target_folder, os.path.join(backup_dir, zip_name))

            # Cleanup Temp Folder
            shutil.rmtree(self.target_folder)

            logger.info("Backup completed")

            return str(os.path.join(backup_dir, dir_time_suffix+'.zip'))

    def parse_html(self, string):
        tree = html.fromstring(string)
        elements = tree.xpath('//li/a')
        return [element.get('href') for element in elements if 'href' in element.keys()]

    def backup_geoserver_data(self):
        gs_data = os.path.join(self.target_folder, 'gs_data')
        if not os.path.exists(gs_data):
            os.makedirs(gs_data)

        resource_url = "{url}/rest/resource/uploads".format(url=self.url)
        resp = self.client.get(resource_url)

        if resp.status_code == 200:
            urls = self.parse_html(resp.content)
            layers = []
            # Iterate over all the subdirectories in the /uploads directory
            for upload_url in urls:
                if '/uploads' in upload_url:
                    resp = self.client.get("{url}/rest/resource/uploads{uri}".format(
                        url=self.url, uri=upload_url.split('/uploads')[-1])
                    )
                    urls = self.parse_html(resp.content)
                    has_shpae_file = ['.shp' in file_url for file_url in urls]
                    # Download all the files if there isn't a shapefile in the directory.
                    # Will backup rasters among other datasets that have been uploaded.
                    if True not in has_shpae_file:
                        for file_url in urls:
                            if not file_url.endswith('/uploads'):
                                file_url = "{url}/rest/resource/uploads{uri}".format(
                                    url=self.url, uri=file_url.split('/uploads')[-1]
                                )

                                resp = self.client.get(file_url)
                                file_name = os.path.basename(file_url)
                                output_path = os.path.join(gs_data, file_name)
                                with open(output_path, 'w') as f:
                                    f.write(resp.content)

                                layers.append(
                                    {
                                        'name': file_name,
                                        'uri': file_url.split('/resource')[-1]
                                    }
                                )
                                logger.info("backed up {url}".format(url=file_url))

            # Create a JSON file with all the files we backed up to help us restore them later
            with open(os.path.join(gs_data, 'data_backup.json'), 'w') as f:
                f.write(json.dumps(layers, indent=2))

    def backup_geoserver_config(self):
        backup_url = "{}/rest/br/backup".format(self.url)

        logger.info("Dumping GeoServer Catalog {url} into {geoserver_bk_file}".format(
                           url=self.url, geoserver_bk_file=self.geoserver_bk_file))
        data = {
            'backup': {
                'archiveFile': self.geoserver_bk_file,
                'overwrite': 'true',
                'options': {
                    'option': ['BK_BEST_EFFORT=true']
                }
            }
        }

        headers = {'Content-type': 'application/json'}
        resp = self.client.post(backup_url, data=json.dumps(data), headers=headers)

        if resp.status_code == 201:
            backup_obj = resp.json()
            job_status = backup_obj['backup']['execution']['status']
            job_id = backup_obj['backup']['execution']['id']

            while job_status != 'COMPLETED':
                if job_status == 'FAILED':
                    raise ValueError("Geoserver backup failed: {status} - {error}".format(
                                       status=resp.status_code, error=resp.text))

                job_id = backup_obj['backup']['execution']['id']
                resp = self.client.get("{url}/{job_id}.json".format(url=backup_url, job_id=job_id))

                if resp.status_code == 200:
                    backup_obj = resp.json()
                    job_status = backup_obj['backup']['execution']['status']
                    job_progress = backup_obj['backup']['execution']['progress']
                    logger.info("Runnig Geoserver Backup: {status} - {progress}".format(
                                       status=job_status, progress=job_progress))
                    time.sleep(3)
                else:
                    raise ValueError('Failed while waiting for Geoserver catalog backup: {status} - {error}'.format(
                                       status=resp.status_code, error=resp.text))

            resp = self.client.get("{url}/{job_id}.zip".format(url=backup_url, job_id=job_id))

            if resp.status_code == 200:
                gs_backup_path = os.path.join(self.target_folder, os.path.basename(self.geoserver_bk_file))
                with open(gs_backup_path, 'w') as f:
                    f.write(resp.content)
                logger.info("Exported Geoserver backup to {}".format(gs_backup_path))
            else:
                raise ValueError('Failed to download Geoserver backup: {status} - {error}'.format(
                                   status=resp.status_code, error=resp.text))
        else:
            raise ValueError('Failed to generate Geoserver backup: {status} - {error}'.format(
                               status=resp.status_code, error=resp.text))

    def backup_geogig_config(self):
        resp = self.client.get("{}/rest/resource/geogig/config/repos".format(self.url))
        geogig_backup_dir = os.path.join(self.target_folder, 'gs_data/geogig_repos')
        if resp.status_code == 200:
            if not os.path.exists(geogig_backup_dir):
                os.makedirs(geogig_backup_dir)

            urls = self.parse_html(resp.content)
            for url in urls:
                if '/repos' in url:
                    repo_url = "{base_url}/rest/resource/geogig{repo_uri}".format(
                        base_url=self.url, repo_uri=url.split('/geogig')[-1])

                    resp = self.client.get(repo_url)

                    if resp.status_code == 200:
                        with open(os.path.join(geogig_backup_dir, os.path.basename(repo_url)), 'w') as f:
                            f.write(resp.content)

            logger.info("Finished exporting Geogig repo config")

    def backup_postgres(self):
        # Dump Vectorial Data from DB
        datastore = settings.OGC_SERVER['default']['DATASTORE']
        if datastore:
            db_obj = settings.DATABASES[datastore]
            schemas_to_backup = ['public']

            if 'OPTIONS' in db_obj and 'options' in db_obj['OPTIONS']:
                search_path = db_obj['OPTIONS']['options'].split('=')[-1]
                schemas_to_backup = map(str.strip, search_path.split(','))

            gs_data_folder = os.path.join(self.target_folder, 'gs_data')
            if not os.path.exists(gs_data_folder):
                os.makedirs(gs_data_folder)

            helpers.dump_db(
                db_obj['NAME'],
                db_obj['USER'],
                db_obj['PASSWORD'],
                gs_data_folder,
                db_obj['PORT'],
                db_obj['HOST'],
                schemas_to_backup,
                self.pg_dump_cmd
            )

    def backup_django_fixtures(self):
        try:
            # Deactivate GeoNode Signals
            designals()

            # Dump Fixtures
            for app_name, dump_name in zip(self.app_names, self.dump_names):
                logger.info("dumping django fixture {}".format(app_name))
                # Point stdout at a file for dumping data to.
                output = open(os.path.join(self.target_folder, dump_name+'.json'), 'w')
                call_command('dumpdata', app_name, format='json', indent=2, natural=True, stdout=output)
                output.close()

            # Store Media Root
            media_root = settings.MEDIA_ROOT
            media_folder = os.path.join(self.target_folder, helpers.MEDIA_ROOT)
            if not os.path.exists(media_folder):
                os.makedirs(media_folder)

            helpers.copy_tree(media_root, media_folder)
        finally:
            # Reactivate GeoNode Signals
            resignals()
