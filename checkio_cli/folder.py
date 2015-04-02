import os

from checkio_cli import config


def get_file_content(file_path):
    fh = open(file_path)
    try:
        return fh.read()
    finally:
        fh.close()


class Folder(object):
    def __init__(self, slug):
        self.u_slug = slug
        self.f_slug = slug.replace('-', '_')

    def image_name(self):
        return 'checkio/' + self.u_slug

    def mission_folder(self):
        return os.path.join(config.MISSIONS_FOLDER, self.f_slug)

    def mission_config_path(self):
        return os.path.join(config.MISSIONS_FOLDER, '.' + self.f_slug)

    def compiled_folder_path(self):
        return os.path.join(config.COMPILED_FOLDER, self.f_slug)

    def verification_folder_path(self):
        return os.path.join(self.compiled_folder_path(), 'verification')

    def referee_requirements(self):
        return os.path.join(self.verification_folder_path(), 'requirements.txt')

    def interface_cli_folder_path(self):
        return os.path.join(self.compiled_folder_path(), 'interfaces', 'checkio_cli')

    def interface_cli_requirements(self):
        return os.path.join(self.interface_cli_folder_path(), 'requirements.txt')

    def referee_folder_path(self):
        return os.path.join(self.verification_folder_path(), 'src')

    def native_env_folder_path(self):
        return os.path.join(config.NATIVE_ENV_FOLDER, self.f_slug)

    def native_env_bin(self, call):
        return os.path.join(self.native_env_folder_path(), 'bin', call)

    def mission_config_read(self):
        return get_file_content(self.mission_config_path())

    def mission_config_write(self, data):
        fh = open(self.mission_config_path(), 'w')
        fh.write(data['source_type'] + '\n' + data['source_url'])
        fh.close()

    def mission_config(self):
        raw_data = self.mission_config_read().split()
        return {
            'source_type': raw_data[0],
            'source_url': raw_data[1]
        }

    def init_file_path(self, interpreter):
        return os.path.join(self.compiled_folder_path(), 'initial', interpreter)

    def initial_code(self, interpreter):
        return get_file_content(self.init_file_path(interpreter))

    def solution_path(self):
        extension = config.INTERPRETERS[config.ACTIVE_INTERPRETER]['extension']
        return os.path.join(config.SOLUTIONS_FOLDER, self.f_slug + '.' + extension)

    def solution_code(self):
        return get_file_content(self.solution_path())
