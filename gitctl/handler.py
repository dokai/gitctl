# -*- encoding: utf-8 -*-
"""Command handlers."""
import os
import git
import shlex
import logging
import subprocess

from ConfigParser import SafeConfigParser

LOG = logging.getLogger('gitctl')

def clean_working_dir(path):
    """Asserts that the given working has no uncommited changes."""
    return True

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
    parser = SafeConfigParser({'type' : 'git', 'treeish' : 'master'})
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
            assert clean_working_dir(project_path)
            # Perform a pull
            if args.rebase:
                cmd = 'git pull --rebase'
            else:
                cmd = 'git pull'
            run(cmd, cwd=project_path, echo=args.show_commands)
        else:
            cmd = 'git clone %s %s' % (proj['url'], project_path)
            run(cmd, echo=args.show_commands)

def gitctl_status(args):
    """Checks the status of all external projects."""
    projects = parse_externals(args.externals)
    
    for proj in projects:
        project_path = os.path.realpath(
            os.path.join(os.getcwd(), proj['container'], proj['name']))
        
        # Fetch upstream
        # TODO: Check the existence of the 'origin' remote first
        run('git fetch origin', cwd=project_path, echo=args.show_commands)
        if not clean_working_dir(project_path):
            print '%s has uncommitted changes' % proj['name']
        # TODO: Check the existence of the branches first
        for branch in ('development', 'demo', 'production'):
            cmd = 'git diff origin/primacontrol/%(b)s primacontrol/%(b)s --exit-code' % { 'b' : branch }
            retcode, _, _ = run(cmd, cwd=project_path, echo=args.show_commands)
            if retcode != 0:
                print '%s: Branch primacontrol/%s differs from upstream' % (proj['name'], branch)

def gitctl_changes(args):
    projects = parse_externals(args.externals)
    
    for proj in projects:
        project_path = os.path.realpath(
            os.path.join(os.getcwd(), proj['container'], proj['name']))
        
        assert os.path.exists(project_path)
        # TODO: Check the existence of the 'origin' remote first
        run('git fetch origin', cwd=project_path, echo=args.show_commands)
        if len(proj['treeish']) == 40:
            retcode, demo_at, _ = run('git rev-parse origin/primacontrol/demo', cwd=project_path, echo=args.show_commands) 
            if proj['treeish'] != demo_at.strip():
                print '%s: %s' % (proj['name'], demo_at.strip())
                if args.diff:
                    cmd = 'git log --stat -p %s origin/primacontrol/demo'
                    print run(cmd, cwd=project_path, echo=args.show_commands)

__all__ = ['gitctl_create', 'gitctl_fetch', 'gitctl_update', 'gitctl_status',
           'gitctl_changes',]
