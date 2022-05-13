# -*- coding: utf-8 -*-
#
# "TheVirtualBrain - Widgets" package
#
# (c) 2022-2023, TVB Widgets Team
#
import os
import json

from jupyter_server.base.handlers import APIHandler
from jupyter_server.utils import url_path_join
import tornado
from tornado.web import MissingArgumentError

from tvbextunicore.exceptions import SitesDownException, FileNotExistsException, JobRunningException
from tvbextunicore.unicore_wrapper.unicore_wrapper import UnicoreWrapper
from tvbextunicore.logger.builder import get_logger
from tvbextunicore.utils import download_file, build_response, DownloadStatus

LOGGER = get_logger(__name__)


class SitesHandler(APIHandler):
    @tornado.web.authenticated
    def get(self):
        LOGGER.info(f"Retrieving sites...")
        message = ''
        try:
            sites = UnicoreWrapper().get_sites()
        except SitesDownException as e:
            sites = list()
            message = e.message
        self.finish(json.dumps({'sites': sites, 'message': message}))


class JobsHandler(APIHandler):
    # The following decorator should be present on all verb methods (head, get, post,
    # patch, put, delete, options) to ensure only authorized user can request the
    # Jupyter server
    @tornado.web.authenticated
    def get(self):
        """
        Retrieve all jobs for current user, launched at site given as POST param.
        """
        try:
            site = self.get_argument("site")
            page = int(self.get_argument("page", "0")) - 1
            LOGGER.info(f"Retrieving jobs (page {page}) for site {site}...")
        except MissingArgumentError:
            site = 'DAINT-CSCS'
            LOGGER.warn(f"No site has been found in query params, defaulting to {site}...")

        all_jobs, message = UnicoreWrapper().get_jobs(site, page)

        self.finish(json.dumps({'jobs': [job.to_json() for job in all_jobs], 'message': message}))

    @tornado.web.authenticated
    def post(self):
        """
        Cancel the job corresponding to the id sent as post param.
        """
        post_params = self.get_json_body()
        job_url = post_params["resource_url"]

        LOGGER.info(f"Cancelling job at URL: {job_url}")
        is_canceled, job = UnicoreWrapper().cancel_job(job_url)

        if not is_canceled:
            resp = {'message': 'Job could not be cancelled!'}
        else:
            resp = {'job': job.to_json(), 'message': ''}

        self.finish(json.dumps(resp))


class JobOutputHandler(APIHandler):
    @tornado.web.authenticated
    def get(self):
        try:
            job_url = self.get_argument("job_url")
            output = UnicoreWrapper().get_job_output(f'{job_url}')
            self.finish(json.dumps(output))
        except MissingArgumentError:
            self.set_status(400)
            self.finish(json.dumps({'message': 'Can\'t access job outputs: No job url provided!'}))


class DownloadHandler(APIHandler):
    @tornado.web.authenticated
    def get(self, job_url, file):
        try:
            response = UnicoreWrapper().download_file(job_url, file)
        except FileNotExistsException as e:
            response = {'success': False, 'message': e.message}

        self.finish(json.dumps(response))


class DriveHandler(APIHandler):

    @tornado.web.authenticated
    def post(self, *args):
        post_params = self.get_json_body()
        try:
            path = post_params['path']
            file = post_params['file']
            job_url = post_params['job_url']
            job_id = post_params['job_id']
        except KeyError as e:
            LOGGER.error(e)
            self.set_status(400, 'Request body missing required params!')
            self.finish()
            return
        LOGGER.info(f'Downloading file from unicore to file created in {path}')
        if path.strip() and not os.path.exists(path):
            response = build_response(DownloadStatus.ERROR, f'Path: {path} does not exist!')
            self.finish(response)
            return
        unicore_wrapper = UnicoreWrapper()
        file_path = os.path.join(path, file) + f'_{job_id}'
        response = download_file(file_path, file, unicore_wrapper, job_url)
        self.finish(response)


def setup_handlers(web_app):
    host_pattern = ".*$"

    base_url = web_app.settings["base_url"]
    sites_pattern = url_path_join(base_url, "tvbextunicore", "sites")
    jobs_pattern = url_path_join(base_url, "tvbextunicore", "jobs")
    output_pattern = url_path_join(base_url, "tvbextunicore", "job_output")
    drive_pattern = url_path_join(base_url, "tvbextunicore", r"drive/([^/]+)?/([^/]+)?")
    handlers = [
        (jobs_pattern, JobsHandler),
        (sites_pattern, SitesHandler),
        (output_pattern, JobOutputHandler),
        (drive_pattern, DriveHandler)
    ]
    web_app.add_handlers(host_pattern, handlers)
