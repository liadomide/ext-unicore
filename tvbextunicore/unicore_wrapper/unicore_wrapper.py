# -*- coding: utf-8 -*-
#
# "TheVirtualBrain - Widgets" package
#
# (c) 2022-2023, TVB Widgets Team
#

import os

import pyunicore.client as unicore_client
from requests.exceptions import ConnectionError

from tvbextunicore.exceptions import TVBExtUnicoreException, ClientAuthException,\
    SitesDownException, FileNotExistsException, JobRunningException
from tvbextunicore.logger.builder import get_logger
from tvbextunicore.unicore_wrapper.job_dto import JobDTO

LOGGER = get_logger(__name__)


class UnicoreWrapper(object):

    def __init__(self):
        token = self.__retrieve_token()
        self.transport = self.__build_transport(token)

    def __retrieve_token(self):
        try:
            from clb_nb_utils import oauth as clb_oauth
            token = clb_oauth.get_token()
        except (ModuleNotFoundError, ConnectionError) as e:
            LOGGER.warning(f"Could not connect to EBRAINS to retrieve an auth token: {e}")
            LOGGER.info("Will try to use the auth token defined by environment variable CLB_AUTH...")

            token = os.environ.get('CLB_AUTH')
            if token is None:
                LOGGER.error("No auth token defined as environment variable CLB_AUTH! Please define one!")
                raise TVBExtUnicoreException("Cannot connect to EBRAINS HPC without an auth token! Either run this on "
                                             "Collab, or define the CLB_AUTH environment variable!")

            LOGGER.info("Successfully retrieved the auth token from environment variable CLB_AUTH!")
        return token

    def __build_transport(self, token):
        # type: (str) -> unicore_client.Transport
        transport = unicore_client.Transport(token, oidc=True)
        return transport

    def __build_client(self, site):
        # type: (dict) -> unicore_client.Client
        sites = self.get_sites()
        site_url = sites.get(site)

        if site_url is None:
            raise AttributeError(f"Requested HPC site: {site}, does not exist!")

        try:
            client = unicore_client.Client(self.transport, site_url)
        except Exception as e:
            LOGGER.warning(f"Could not connect to client: {e}")
            raise ClientAuthException(e)

        return client

    def get_sites(self):
        # type: () -> list
        """
        Retrieve all sites available via Unicore.
        """
        try:
            all_sites = unicore_client.get_sites(self.transport)
            return all_sites
        except Exception as e:
            LOGGER.warning(f"Cannot retrieve sites: {e}")
            raise SitesDownException('Sites are not available at the moment!')

    def get_jobs(self, site, page=0):
        # type: (str, int) -> (list, str)
        """
        Retrieve the jobs started by the current user at the selected site and return them in a list.
        """
        jobs_per_page = 10
        jobs_offset = page * jobs_per_page

        jobs_list = list()

        try:
            client = self.__build_client(site)
        except ClientAuthException:
            return jobs_list, f"You do not have access to {site}"
        except SitesDownException as e:
            return jobs_list, e.message

        all_jobs = client.get_jobs(offset=jobs_offset, num=jobs_per_page)

        for job in all_jobs:
            jobs_list.append(JobDTO.from_unicore_job(job))

        return jobs_list, ""

    def cancel_job(self, job_url):
        # type: (str) -> (bool, JobDTO)
        """
        Abort HPC job accessible at the given URL.
        """
        if job_url is None:
            LOGGER.error("Cannot abort job as URL has not been provided!")
            return False, None

        job = self.get_job(job_url)
        if job.is_running():
            job.abort()
            LOGGER.info(f"Aborted job {job.job_id} from URL: {job_url}")
        else:
            LOGGER.info(f"Job {job.job_id} already finished, no need to abort, URL: {job_url}")

        job = unicore_client.Job(self.transport, job_url)
        return True, JobDTO.from_unicore_job(job)

    def get_job(self, job_url):
        # type: (str) -> unicore_client.Job
        """
        Get an unicore job from a job url and return the instantiated Job object
        """
        return unicore_client.Job(self.transport, job_url)

    def get_job_output(self, job_url):
        # type: (str) -> dict
        """
        Get the output files for an unicore job url
        returns: {<file_name>:{'is_file': bool}}
        """
        job = self.get_job(job_url)
        outputs = dict()
        files = job.working_dir.listdir()
        for k, v in files.items():
            outputs[k] = {'is_file': v.isfile()}
        return outputs

    def download_file(self, job_url, file_name, file=None):
        # type: (str, str) -> str
        """
        helper method to download a file from a job output
        """
        if file is None:
            file = file_name
        job = self.get_job(job_url)
        if job.is_running():
            raise JobRunningException(f'Can\'t download file {file_name}. Job {job_url} is still running!')
        wd = job.working_dir.listdir()
        if not wd.get(file_name, False):
            raise FileNotExistsException(f'{file_name} doesn\'t exist as output of {job_url}!')

        wd[file_name].download(file)
        return 'Downloaded successfully!'

    def stream_file(self, job_url, file, offset=0, size=-1):
        # type: (str, str, int, int) -> stream
        """
        method to download a file as an octet stream
        """
        job = self.get_job(job_url)
        if job.is_running():
            raise FileNotExistsException(f'Can\'t access {file}. Job still running.')

        wd = job.working_dir.listdir()
        if not wd.get(file, False):
            raise FileNotExistsException(f'{file} doesn\'t exist as output of {job_url}!')

        return wd[file].raw(offset=offset, size=size)
