# -*- encoding: utf-8 -*-
"""Command handlers."""
import os
import git
import shlex
import logging
import subprocess

from ConfigParser import SafeConfigParser

LOG = logging.getLogger('gitctl')

def clean_working_dir(repository):
    """Returns True if the given repository has no uncommited changes."""
    return len(repository.git.diff().strip()) == 0 and \
           len(repository.git.diff('--cached').strip()) == 0

def run(command, cwd=None, echo=False):
    """Executes the given command."""
    if hasattr(command, 'startswith'):
        # Split the command into tokens, honoring any quoted parts
        lexer = shlex.shlex(command)
        lexer.whitespace_split = True
        command = list(lexer)
    if echo:
        if cwd is not None:
            print '> %s [%s]' % (' '.join(command), cwd)
        else:
            print '>', ' '.join(command)

    pipe = subprocess.Popen(command, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    retcode = pipe.wait()
    
    return retcode, pipe.stdin.read(), pipe.stderr.read()
    # return subprocess.call(command,
    #                        cwd=cwd,
    #                        stdout=open(os.devnull, 'w'),
    #                        stderr=subprocess.STDOUT)


def parse_config(config):
    """Parses the gitctl config file."""

def parse_externals(config):
    """Parses the gitctl externals configuration."""
    parser = SafeConfigParser({'type' : 'git'})
    if len(parser.read(config)) == 0:
        raise ValueError('Invalid config file: %s' % config)

    projects = []
    for sec in parser.sections():
        if not parser.has_option(sec, 'url'):
            raise ValueError('Section %s is missing the url option %s' % sec)
       
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

def generate_external_config(name, url, path, treeish=None, repo_type='git'):
    """Returns a configuration section for the externals config."""
    section = """
    [%(name)s]
    url = %(url)s
    type = %(repo_type)s
    treeish = %(treeish)s
    dir = %(path)s    
    """ % {'name' : name,
           'url' : url,
           'repo_type' : repo_type,
           'path' : path,
           'treeish' : treeish}
    return '\n'.join([line.strip() for line in section.splitlines()])

def gitctl_create(args):
    """Handles the 'gitctl create' command"""
    project_path = os.path.realpath(os.path.join(os.getcwd(), args.project[0]))
    project_name = os.path.basename(project_path)
    config = parse_config(args.config)
    
    if not os.path.exists(project_path):
        raise RuntimeError('Project path does not exist!')
    
    # TODO: Assert that project does not exist at git.hexagonit.fi
    # TODO: Read the git upstream hostname and names of initial branches from
    #       the configuration file. Also the commit message address.
    
    # Set up the remote bare repository
    initialize_remote = (
        'ssh', 'git@git.hexagonit.fi',
        'mkdir -p %(project)s.git && '
        'cd %(project)s.git && '
        'git --bare init && '
        'echo %(project)s > description && '
        'echo \'. /usr/share/doc/git-core/contrib/hooks/post-receive-email\' > hooks/post-receive && '
        'chmod a+x hooks/post-receive && '
        'git config hooks.mailinglist commit@hexagonit.fi && '
        'git config hooks.emailprefix "[GIT] "' % { 'project' : project_name },
        )
    run(initialize_remote, echo=args.show_commands)
    
    initialize_local = (
        # Initialize the local repository and create the first commit
        'git init',
        'git add .',
        'git commit -m "gitctl: project initialization"',
        # Create the local branches
        'git branch primacontrol/development',
        'git branch primacontrol/demo',
        'git branch primacontrol/production',
        # Push initial version to upstream
        'git remote add origin git@git.hexagonit.fi:%s.git' % project_name,
        'git push origin primacontrol/development',
        'git push origin primacontrol/demo',
        'git push origin primacontrol/production',
        'git fetch',
        # Set up the local branches to track the remote ones
        'git branch -f --track primacontrol/production origin/primacontrol/production',
        'git branch -f --track primacontrol/demo origin/primacontrol/demo',
        'git branch -f --track primacontrol/development origin/primacontrol/development',
        # Check out development branch and get rid of master
        'git checkout primacontrol/development',
        'git branch -d master',
        )
    for cmd in initialize_local:
        run(cmd, cwd=project_path, echo=args.show_commands)

def gitctl_fetch(args):
    projects = parse_externals(args.externals)
    
    for proj in projects:
        project_path = os.path.realpath(
            os.path.join(os.getcwd(), proj['container'], proj['name']))
        assert os.path.exists(project_path)
        run('git fetch', cwd=project_path, echo=args.show_commands)

def gitctl_update(args):
    """Updates the external projects.
    
    If the project already exists locally, it will be pulled (or rebased).
    Otherwise it will cloned.
    """
    projects = parse_externals(args.externals)
    
    for proj in projects:
        project_path = os.path.realpath(
            os.path.join(os.getcwd(), proj['container'], proj['name']))

        if os.path.exists(project_path):
            repository = git.Repo(project_path)
            assert clean_working_dir(repository)

            if args.rebase:
                repository.git.pull('--rebase')
            else:
                repository.git.pull()
        else:
            # GitPython only operates on existing repositories, so we need to perform the
            # clone operation manually.
            cmd = 'git clone %s %s' % (proj['url'], project_path)
            run(cmd, echo=args.show_commands)

def gitctl_status(args):
    """Checks the status of all external projects."""
    projects = parse_externals(args.externals)
    
    for proj in projects:
        project_path = os.path.realpath(
            os.path.join(os.getcwd(), proj['container'], proj['name']))
        
        repository = git.Repo(project_path)
        # Fetch upstream
        repository.git.fetch('origin')

        if not clean_working_dir(repository):
            print '%s has uncommitted changes' % proj['name']
            
        remote_branches = set([name.strip()
                               for name
                               in repository.git.branch('-r').splitlines()])
        
        # TODO: Refactor the remote/local mapping into a configuration file.
        for remote, local in [('origin/primacontrol/development', 'primacontrol/development'),
                              ('origin/primacontrol/demo', 'primacontrol/demo'),
                              ('origin/primacontrol/production', 'primacontrol/production')]:
            if remote in remote_branches:
                if len(repository.diff(remote, local).strip()) > 0:
                    print '%s: Branch %s differs from upstream' % (proj['name'], local)

def gitctl_changes(args):
    projects = parse_externals(args.externals)
    
    for proj in projects:
        project_path = os.path.realpath(
            os.path.join(os.getcwd(), proj['container'], proj['name']))
        
        assert os.path.exists(project_path)
        repository = git.Repo(project_path)
        
        remote_branches = set([name.strip()
                               for name
                               in repository.git.branch('-r').splitlines()])
        
        if 'origin/primacontrol/demo' not in remote_branches:
            print 'Skipping', proj['name']
            continue
        
        # Fetch from upstream so that we compare against the latest version
        repository.git.fetch('origin')
        # Get actual versions of both objects
        pinned_at = repository.git.rev_parse(proj['treeish'])
        demo_at = repository.git.rev_parse('origin/primacontrol/demo')
        
        if pinned_at != demo_at:
            # The demo branch has advanced.
            print '%s: %s' % (proj['name'], demo_at)
            if args.diff:
                print repository.git.log('--stat', '--summary', '-p', pinned_at, demo_at)
        else:
            print proj['name'], 'is up-to-date'

__all__ = ['gitctl_create', 'gitctl_fetch', 'gitctl_update', 'gitctl_status',
           'gitctl_changes',]
