import os
import sys
import git
import re
import shutil
import logging
from distutils.dir_util import copy_tree

from checkio_docker.parser import MissionFilesCompiler
from checkio_docker.client import DockerClient
from checkio_cli.folder import Folder
from checkio_cli.config import settings

RE_REPO_BRANCH = re.compile('(.+?)\@([\w\-\_]+)$')


class GetterException(Exception):
    pass

if "that typo is not yet fixed in the whole codebase":
    GetterExeption = GetterException


class TemplateWasntFound(GetterException):
    def __init__(self, template, folders):
        self.template = template
        self.folders = folders

    def __str__(self):
        folders = ','.join(map(repr, self.folders))
        return "Template {!r} wasn't found in folder(s) {}".format(self.template, folders)


class MissionFolderExistsAlready(GetterException):
    def __init__(self, folder):
        self.folder = folder

    def __str__(self):
        return 'Mission folder {!r} exists already'.format(self.folder)


def remove_folder(folder):
    import contextlib, shutil
    with contextlib.suppress(FileNotFoundError):
        shutil.rmtree(folder)


def make_mission_from_template(mission, template, force_remove=False):
    for template_folder in settings.TEMPLATES_FOLDERS:
        template_full_path = os.path.join(template_folder, template)
        if os.path.exists(template_full_path):
            break
    else:
        raise TemplateWasntFound(template, settings.TEMPLATES_FOLDERS)

    folder = Folder(mission)
    mission_folder = folder.mission_folder()
    if force_remove:
        shutil.rmtree(mission_folder)
    elif os.path.exists(mission_folder):
        raise MissionFolderExistsAlready(mission_folder)

    os.mkdir(mission_folder)

    copy_tree(os.path.join(template_full_path, 'source'), mission_folder)

    namespace = {}
    exec(open(os.path.join(template_full_path, 'run.py')).read(), namespace)
    namespace['run'](mission)

    folder.mission_config_write(dict(type='local', url=mission_folder))


def mission_git_init(mission, original_url):
    folder = Folder(mission)
    mission_folder = folder.mission_folder()
    logging.info('Init git repository for folder %s', mission_folder)
    repo = git.Repo.init(mission_folder)
    for root, dirs, files in os.walk(mission_folder):
        if root.endswith('.git') or '/.git/' in root:
            continue

        for file_name in files:
            abs_file_name = os.path.join(root, file_name)
            logging.debug('Add file to local git repository %s', abs_file_name)
            repo.index.add([abs_file_name])

    repo.index.commit("initial commit")
    origin = repo.create_remote('origin', original_url)
    origin.push(repo.refs)
    origin.fetch()
    repo.create_head('master', origin.refs.master).set_tracking_branch(origin.refs.master)
    folder.mission_config_write(dict(type='git', url=original_url))


def mission_git_getter(url, slug):
    # TODO: checkout into mission folder
    # compile it
    # build docker
    # prepare cli interface
    folder = Folder(slug)
    destination_path = folder.mission_folder()

    logging.info('Getting a new mission through the git...')
    logging.info('from %s to %s', url, destination_path)

    if os.path.exists(destination_path):
        answer = input('Folder {} exists already.'
                           ' Do you want to overwite it? [y]/n :'.format(destination_path))
        if not answer or answer.lower().startswith('y'):
            shutil.rmtree(destination_path)
        else:
            return

    try:
        checkout_url, branch = re.search(RE_REPO_BRANCH, url).groups()
    except AttributeError:
        checkout_url, branch = url, 'master'

    logging.debug('URL info: checkioout url:%s branch:%s', url, branch)

    git.Repo.clone_from(checkout_url, destination_path, branch=branch)

    folder.mission_config_write(dict(type='git', url=url))
    print('Prepare mission {} from {}'.format(slug, url))


def logging_sys(command):
    logging.debug('Sys: %s', command)
    os.system(command)


def rebuild_native(slug):
    folder = Folder(slug)
    logging.info('Building virtualenv in %s', folder.native_env_folder_path())
    remove_folder(folder.native_env_folder_path())

    logging_sys("virtualenv --system-site-packages -p python3 " + folder.native_env_folder_path())
    for requirements in folder.referee_requirements(), folder.interface_cli_requirements():
        logging_sys("{pip3} install -r {requirements}".format(
            pip3=folder.native_env_bin('pip3'), requirements=requirements))


def rebuild_mission(slug):
    folder = Folder(slug)
    docker = DockerClient()
    verification_folder_path = folder.container_verification_folder_path()
    logging.info("Build docker image %s from %s", folder.image_name(), verification_folder_path)
    remove_folder(verification_folder_path)

    copy_tree(folder.verification_folder_path(), verification_folder_path)
    docker.build(name_image=folder.image_name(), path=verification_folder_path)


def recompile_mission(slug):
    folder = Folder(slug)
    compiled_path = folder.compiled_folder_path()
    logging.info("Relink folder to %s", compiled_path)
    remove_folder(compiled_path)

    mission_source = MissionFilesCompiler(compiled_path)
    mission_source.compile(source_path=folder.mission_folder(), use_link=True)
