"""
The Fabric file.
"""

import os
import copy

CONFIGURATION_DIR = 'configuration'
ARCHIVES_DIR = 'archives'
SOURCES_DIR = 'sources'
BUILD_DIR = 'build'
REPOSITORY_DIR = 'repository'

REPOSITORIES = {
    'freelan-buildtools' : {
        'tag': '1.2',
        'depends': [],
    },
    'libcryptoplus' : {
        'tag': '2.0',
        'depends': [
            'freelan-buildtools',
        ],
    },
    'libkfather': {
        'tag': '1.0',
        'depends': [
            'freelan-buildtools',
        ],
    },
}

def get_ordered_repositories():
    """
    Get a list of the repositories ordered by dependencies.

    The less dependent repositories go first.
    """

    result = []
    repositories = dict((repository, copy.deepcopy(attributes.get('depends', []))) for repository, attributes in REPOSITORIES.items())

    while repositories:
        extracted = [repository for repository, depends in repositories.items() if not depends]

        if not extracted:
            raise RuntimeError('Cyclic dependency')

        for x in extracted:
            del repositories[x]

        result.extend(extracted)

        for depends in repositories.values():
            depends[:] = [depend for depend in depends if depend not in extracted]

    print result
    return result

def get_options():
    """
    Get a dictionary of all the sensible paths.
    """

    paths_aliases = {
        'configuration_path': CONFIGURATION_DIR,
        'archives_path': ARCHIVES_DIR,
        'sources_path': SOURCES_DIR,
        'build_path': BUILD_DIR,
        'repository_path': REPOSITORY_DIR,
    }

    def get_dir_path(_dir):
        return os.path.abspath(os.path.join(os.path.dirname(env.real_fabfile), _dir))

    return dict(map(lambda x: (x[0], get_dir_path(x[1])), paths_aliases.items()))

def copy_file(source, target):
    """
    Copy a file from source to target, replacing content with options if needed.
    """

    options = get_options()

    target = os.path.expanduser(target)

    for option, value in options.items():
        source = source.replace('%%%s%%' % option, value)
        target = target.replace('%%%s%%' % option, value)

    print('Copying %s to %s ...' % (source, target))

    with open(source) as original_file:
        content = original_file.read()

    for option, value in options.items():
        content = content.replace('%%%s%%' % option, value)

    with open(target, 'w') as target_file:
        target_file.write(content)

# Below are the fabric commands

from fabric.api import *

def archives():
    """
    Make archives of the git repositories.
    """

    options = get_options()

    archives_path = options['archives_path']

    local('mkdir -p %s' % archives_path)

    for repository, attributes in REPOSITORIES.items():
        repository_path = os.path.abspath(os.path.join(os.path.dirname(env.real_fabfile), '..', '..', repository))

        tag = attributes.get('tag')

        if tag:
            with lcd(repository_path):
                local('git archive %(tag)s | gzip > %(output_dir)s/%(repository)s_%(tag)s.orig.tar.gz' % {
                    'repository': repository,
                    'tag': tag,
                    'output_dir': archives_path,
                })

def sources(override=False):
    """
    Generate the source packages.
    """

    options = get_options()

    sources_path = options['sources_path']
    vcs_uri_pattern = 'git@github.com:freelan-developers/%(repository)s.debian.git'

    local('mkdir -p %s' % sources_path)

    for repository in REPOSITORIES:

        vcs_uri = vcs_uri_pattern % {
            'repository': repository,
        }

        with lcd(sources_path):
            if override:
                local('rm -rf %s.debian' % repository)

            local('[ -d %(repository)s.debian ] || git clone %(uri)s' % {
                'uri': vcs_uri,
                'repository': repository,
            })

def configure():
    """
    Copy and fill the configuration files were appropriate.
    """

    copy_file('%configuration_path%/gbp.conf', '~/.gbp.conf')
    copy_file('%configuration_path%/pbuilderrc', '~/.pbuilderrc')

def cowbuilder(override=False):
    """
    Create the cowbuilder environment.
    """

    if override:
        local('rm -rf /var/cache/pbuilder/base.cow')

    local('[ -d /var/cache/pbuilder/base.cow ] && sudo cowbuilder --update --config ~/.pbuilderrc || sudo cowbuilder --create --config ~/.pbuilderrc ')
