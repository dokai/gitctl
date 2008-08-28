# -*- encoding: utf-8 -*-
"""Command handlers."""
import os
import sys
import git
import shlex
import logging
import subprocess

from StringIO import StringIO
from ConfigParser import SafeConfigParser

logging.basicConfig(level=logging.INFO, format='%(message)s')
LOG = logging.getLogger()

def project_path(proj, relative=False):
    """Returns the absolute project path unless relative=True, when a path
    relative to the current directory will be returned.
    """
    path = os.path.realpath(
        os.path.abspath(os.path.join(proj['container'], proj['name'])))
    if relative:
        prefix_len = len(os.path.commonprefix(os.path.realpath(os.getcwd()), path)) + 1
        path = path[prefix_len:]
    return path

def clean_working_dir(repository):
    """Returns True if the given repository has no uncommited changes."""
    g = isinstance(repository, git.Git) and repository or repository.git
    return len(g.diff().strip()) == 0 and \
           len(g.diff('--cached').strip()) == 0

def run(command, cwd=None):
    """Executes the given command."""
    if hasattr(command, 'startswith'):
        # Split the command into tokens, honoring any quoted parts
        lexer = shlex.shlex(command)
        lexer.whitespace_split = True
        command = list(lexer)

    pipe = subprocess.Popen(command, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    retcode = pipe.wait()
    
    return retcode, pipe.stdout.read(), pipe.stderr.read()

def parse_config(config):
    """Parses the gitctl config file."""
    parser = SafeConfigParser({'upstream' : 'origin'})
    if len(parser.read([config, os.path.expanduser('~/.gitctl.cfg')])) == 0:
        raise ValueError('Invalid config file: %s' % config)
    
    if not parser.has_section('gitctl'):
        raise ValueError('The [gitctl] section is missing')
    
    upstream = parser.get('gitctl', 'upstream')
    return {'upstream' : upstream,
            'upstream-url' : parser.get('gitctl', 'upstream-url'),
            'commit-email' : parser.get('gitctl', 'commit-email'),
            'commit-email-prefix' : parser.get('gitctl', 'commit-email-prefix'),
            'branches' : [('%s/%s' % (upstream, branch), branch)
                          for branch
                          in parser.get('gitctl', 'branches').split()],
            'staging-branch' : '%s/%s' % (upstream, parser.get('gitctl', 'staging-branch')),
            'development-branch' : parser.get('gitctl', 'development-branch'),
            }

def parse_externals(config):
    """Parses the gitctl externals configuration."""
    parser = SafeConfigParser({'type' : 'git'})
    if len(parser.read(config)) == 0:
        LOG.critical('Invalid externals configuration: %s', config)
        sys.exit(1)

    projects = []
    for sec in parser.sections():
        if not parser.has_option(sec, 'url'):
            LOG.critical('Section %s is missing the ``url`` option in the externals configuration', sec)
            sys.exit(1)
       
        proj = {
           'name' : sec.strip(),
           'url' : parser.get(sec, 'url').strip(),
           'type' : parser.get(sec, 'type').strip() }
        
        if parser.has_option(sec, 'container'):
            proj['container'] = parser.get(sec, 'container').strip()

        if proj['type'] not in ('git', 'git-svn'):
            raise ValueError('Invalid type: %s. Supported types are "git" and "git-svn".' % proj['type'])

        if proj['type'] == 'git':
            proj['treeish'] = parser.get(sec, 'treeish').strip()
        elif proj['type'] == 'git-svn':
            for opt in 'svn-trunk', 'svn-tags', 'svn-branches':
                if parser.has_option(sec, opt):
                    proj[opt] = parser.get(sec, opt).strip()
            if parser.has_option(sec, 'svn-clone-options'):
                proj['svn-clone-options'] = parser.get(sec, 'svn-clone-options').split()

        projects.append(proj)
    
    return projects

def generate_externals(projects):
    """Generates an externals configuration file."""
    config = SafeConfigParser()
    for project in projects:
        section = project.pop('name')
        config.add_section(section)
        for k, v in project.iteritems():
            config.set(section, k, v)
    buf = StringIO()
    config.write(buf)
    return buf.getvalue()
    
def gitctl_create(args):
    """Handles the 'gitctl create' command"""
    project_path = os.path.realpath(os.path.join(os.getcwd(), args.project[0]))
    project_name = os.path.basename(project_path)
    config = parse_config(args.config)
    
    if not os.path.exists(project_path):
        LOG.critical('Project path does not exist!', project_path)
        sys.exit(1)
    
    # TODO: Assert that project does not exist at git.hexagonit.fi
    project_url = '%s:%s.git' % (config['upstream-url'], project_name)
    
    # Set up the remote bare repository
    initialize_remote = (
        'ssh', config['upstream-url'],
        'mkdir -p %(project)s.git && '
        'cd %(project)s.git && '
        'git --bare init && '
        'echo %(project)s > description && '
        'echo \'. /usr/share/doc/git-core/contrib/hooks/post-receive-email\' > hooks/post-receive && '
        'chmod a+x hooks/post-receive && '
        'git config hooks.mailinglist %(commit_email)s && '
        'git config hooks.emailprefix "%(commit_email_prefix)s "' % {
            'project' : project_name,
            'commit_email' : config['commit-email'],
            'commit_email_prefix' : config['commit-email-prefix'] },
        )
    run(initialize_remote)
    LOG.info('Created new remote repository: %s', project_url)
    
    # Initialize the local directory.
    repository = git.Git(project_path)
    repository.init()

    # Create the initial commit
    repository.add('.')
    repository.commit('-m', 'gitctl: project initialization')
    
    # Create local branches
    for remote, local in config['branches']:
        repository.branch(local)

    # Push the initial structure to upstream
    repository.remote('add', config['upstream'], project_url)
    for remote, local in config['branches']:
        repository.push(config['upstream'], local)
    repository.fetch(config['upstream'])
    
    LOG.info('Created new local repository: %s', project_path)
    
    # Set up the local branches to track the remote ones
    for remote, local in config['branches']:
        repository.branch('-f', '--track', local, remote)
        LOG.info('Branch ``%s`` is tracking ``%s``', local, remote)
        
    # Checkout the development branch 
    repository.checkout(config['development-branch'])
    # Get rid of the default master branch
    repository.branch('-d', 'master')
    
    LOG.info('Checked out development branch ``%s``', config['development-branch'])

def gitctl_fetch(args):
    """Fetches all projects."""
    projects = parse_externals(args.externals)
    config = parse_config(args.config)
    
    LOG.info('Fetching projects..')
    for proj in projects:
        repository = git.Git(project_path(proj))
        repository.fetch(config['upstream'])
        LOG.info(proj['name'])

def gitctl_update(args):
    """Updates the external projects.
    
    If the project already exists locally, it will be pulled (or rebased).
    Otherwise it will cloned.
    """
    projects = parse_externals(args.externals)
    config = parse_config(args.config)
    
    LOG.info('Updating projects..')
    for proj in projects:
        path = project_path(proj)
        if os.path.exists(path):
            repository = git.Git(path)
            if not clean_working_dir(repository):
                print proj['name'], 'has local changes. Please commit or stash them and try again.'
                continue

            LOG.info('Pulling %s', proj['name'])
            if args.rebase:
                repository.pull('--rebase')
            else:
                repository.pull()
        else:
            LOG.info('Cloning %s', proj['name'])
            # Clone the repository
            temp = git.Git('/tmp')
            temp.clone(proj['url'], path)

            # Set up the local tracking branches
            repository = git.Git(path)
            remote_branches = set([name.strip()
                                   for name
                                   in repository.branch('-r').splitlines()])
            for remote, local in config['branches']:
                if remote in remote_branches:
                    repository.branch('--track', local, remote)
            # Check out the given treeish
            repository.checkout(proj['treeish'])
            # Get rid of the local master branch
            #repository.branch('-d', 'master')

def gitctl_status(args):
    """Checks the status of all external projects."""
    config = parse_config(args.config)
    projects = parse_externals(args.externals)

    LOG.info('Checking status..')
    for proj in projects:
        repository = git.Repo(project_path(proj))
        if not args.no_fetch:
            # Fetch upstream
            repository.git.fetch(config['upstream'])

        if not clean_working_dir(repository):
            LOG.info('%s .. uncommitted changes. Skipping.', proj['name'])
            continue
            
        remote_branches = set([name.strip()
                               for name
                               in repository.git.branch('-r').splitlines()])
        
        uptodate = True
        for remote, local in config['branches']:
            if remote in remote_branches:
                if len(repository.diff(remote, local).strip()) > 0:
                    LOG.info('%s .. branch ``%s`` out of sync with upstream', proj['name'], local)
                    uptodate = False
        if uptodate:
            LOG.info('%s .. OK', proj['name'])

def gitctl_changes(args):
    """Checks for changes between the stating branch and the currently pinned
    versions in the externals configuration.
    
    It makes most sense when executed in the production buildout when the
    reported differences are the ones most likely pending to be pushed into
    production.
    """
    projects = parse_externals(args.externals)
    config = parse_config(args.config)

    LOG.info('Comparing changes to pinned down versions..')
    for proj in projects:
        repository = git.Git(project_path(proj))
        
        remote_branches = set([name.strip()
                               for name
                               in repository.branch('-r').splitlines()])
        
        if config['staging-branch'] not in remote_branches:
            # This looks to be a package that does not share our common repository layout
            # which is possible with 3rd party packages etc. We can safely ignore it.
            if not args.show_config:
                LOG.info('%s .. skipping.', proj['name'])
            continue
        
        # Fetch from upstream so that we compare against the latest version
        repository.fetch(config['upstream'])
        # Get actual versions of both objects
        pinned_at = repository.rev_parse(proj['treeish'])
        demo_at = repository.rev_parse(config['staging-branch'])
        
        if pinned_at != demo_at:
            # The demo branch has advanced.
            if args.show_config:
                # Update the treeish to the latest version in the demo branch.
                proj['treeish'] = demo_at
            else:
                LOG.info('%s .. latest staged revision at %s', proj['name'], demo_at)
                if args.diff:
                    print repository.log('--stat', '--summary', '-p', pinned_at, demo_at)
        else:
            if not args.show_config:
                LOG.info('%s .. OK', proj['name'])
        
    if args.show_config:
        print generate_externals(projects)

__all__ = ['gitctl_create', 'gitctl_fetch', 'gitctl_update', 'gitctl_status',
           'gitctl_changes',]
