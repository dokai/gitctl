# -*- coding: utf-8 -*-
"""Command handlers."""
import os
import sys
import git
import logging

import gitctl.notification
import gitctl.utils
import gitctl.wtf

LOG = logging.getLogger('gitctl')
LOG_SUMMARY = logging.getLogger('gitctl.summary')

UPDATE_SUMMARY_TMPL = """Update finished

Processed %(total)s project(s) of which 
 - %(updated)s were updated
 - %(cloned)s were cloned (new project)
 - %(dirty)s had dirty checkouts
 - %(failed)s failed to update cleanly
"""

def gitctl_create(args):
    """Handles the 'gitctl create' command"""
    project_path = os.path.realpath(os.path.join(os.getcwd(), args.project[0]))
    project_name = os.path.basename(project_path)
    config = gitctl.utils.parse_config(args.config)
    
    if not os.path.exists(project_path):
        LOG.critical('Project path %s does not exist!', project_path)
        sys.exit(1)
    
    project_url = '%s:%s.git' % (config['upstream-url'], project_name)

    # Make sure that the remote repository does not exist already.
    retcode = gitctl.utils.run('ssh %s test ! -d %s.git' % (config['upstream-url'], project_name))
    if retcode != 0:
        LOG.error('Remote repository ``%s`` already exists. Aborting.', project_url)
        sys.exit(1)
    
    # Set up the remote bare repository
    initialize_remote = """\
    ssh %(upstream)s
    "mkdir -p %(project)s.git && 
     cd %(project)s.git && 
     git --bare init && 
     echo %(project)s > description && 
     echo '. /usr/share/doc/git-core/contrib/hooks/post-receive-email' > hooks/post-receive &&
     chmod a+x hooks/post-receive && 
     git config hooks.mailinglist %(commit_email)s && 
     git config hooks.emailprefix \\"%(commit_email_prefix)s \\" &&
     git config hooks.emaildiff true"
    """ % { 'upstream' : config['upstream-url'],
            'project' : project_name,
            'commit_email' : config['commit-email'],
            'commit_email_prefix' : config['commit-email-prefix'] }
    
    gitctl.utils.run(' '.join([l.strip() for l in initialize_remote.splitlines()]))
    LOG.info('Created new remote repository: %s', project_url)
    
    # Initialize the local directory.
    repository = git.Git(project_path)
    repository.init()

    # Create the initial commit
    repository.add('.')
    repository.commit('-m', args.message)
    
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
    
    # Fix the HEAD ref in the upstream repo so cloning does not give an error
    gitctl.utils.run('ssh %(upstream)s "echo ref: refs/heads/%(devbranch)s > %(project)s.git/HEAD"' % {
        'upstream' : config['upstream-url'],
        'devbranch' : config['development-branch'],
        'project' : project_name,
        })
    
    LOG.info('Checked out development branch ``%s``', config['development-branch'])

def gitctl_fetch(args):
    """Fetches all projects."""
    projects = gitctl.utils.parse_externals(args.externals)
    config = gitctl.utils.parse_config(args.config)
    
    for proj in gitctl.utils.selected_projects(args, projects):
        repository = git.Git(gitctl.utils.project_path(proj))
        repository.fetch(config['upstream'])
        LOG.info('%s Fetched', gitctl.utils.pretty(proj['name']))

def gitctl_branch(args):
    """Operates on the project branches."""
    projects = gitctl.utils.parse_externals(args.externals)
    config = gitctl.utils.parse_config(args.config)
    
    for proj in gitctl.utils.selected_projects(args, projects):
        repository = git.Repo(gitctl.utils.project_path(proj))
        if not args.checkout and args.list:
            LOG.info('%s %s' % (gitctl.utils.pretty(proj['name']),
                                repository.active_branch))
        
        if args.checkout:
            branch = args.checkout[0]
            if repository.is_dirty:
                LOG.info('%s Dirty working directory. Please commit or stash and try again.' % gitctl.utils.pretty(proj['name']))
            else:
                branches = set([b.name for b in repository.branches])
                if branch not in branches:
                    LOG.warning('%s No such branch: ``%s``' % (gitctl.utils.pretty(proj['name']), branch))
                elif branch == repository.active_branch and args.verbose:
                    LOG.info('%s Already at ``%s``' % (gitctl.utils.pretty(proj['name']), branch))
                else:
                    repository.git.checkout(branch)
                    LOG.info('%s Checked out ``%s``' % (gitctl.utils.pretty(proj['name']), branch))

def gitctl_update(args):
    """Updates the external projects.
    
    If the project already exists locally, it will be pulled (or rebased).
    Otherwise it will cloned.
    """
    config = gitctl.utils.parse_config(args.config)
    projects = gitctl.utils.parse_externals(args.externals)

    summary = {'total' : 0}

    for proj in gitctl.utils.selected_projects(args, projects):
        summary['total'] += 1
        path = gitctl.utils.project_path(proj)
        if os.path.exists(path):
            repository = git.Repo(path)
            try:
                repository.git.fetch()
            except git.errors.GitCommandError, x:
                LOG.error('%s ERROR %s', gitctl.utils.pretty(proj['name']), x)
            
            if repository.is_dirty:
                LOG.info('%s Dirty working directory. Please commit or stash and try again.', gitctl.utils.pretty(proj['name']))
                summary.setdefault('dirty', set()).add(proj['name'])
                continue

            ok = True
            updated = False

            if gitctl.utils.is_sha1(proj['treeish']):
                # We're dealing with an explicit version pin.
                pinned_at = repository.git.rev_parse('HEAD').strip()
                treeish = proj['treeish']
                # Simply do a hard reset to the requested revision
                repository.git.reset('--hard', treeish)
            else:
                # We're dealing with a dynamic branch pointer
                pinned_at = None
                treeish = repository.active_branch

                remote_branches = set(repository.git.branch('-r').split())
                local_branches = set(repository.git.branch().split())

                for remote, local in config['branches']:
                    if remote in remote_branches and local in local_branches:
                        if repository.git.rev_parse(remote) == repository.git.rev_parse(local):
                            # Skip branches that have not changed.
                            continue

                        # Switch to the branch to avoid implicit merge commits
                        repository.git.checkout(local)

                        # Use a remote:local refspec to pull the given branch. We omit the + from the
                        # refspec to attempt a fast-forward merge.
                        status, stdout, stderr = repository.git.pull(
                            config['upstream'],
                            '%s:%s' % (local, local),
                            with_exceptions=False,
                            with_extended_output=True)

                        if status != 0:
                            ok = False
                            if 'non fast forward' in stderr.lower():
                                # Fast-forward merge was not possible, we'll
                                # bail out for now. We could attempt a normal 'git pull' operation but that
                                # might leave multiple branch in an inconsistent state at the same time.
                                LOG.warning('%s Fast forward merge not possible for branch ``%s``. Try syncing with upstream manually (pull, push or merge).', gitctl.utils.pretty(proj['name']), local)
                                summary.setdefault('failed', set()).add(proj['name'])
                            else:
                                # Some other kind of error.
                                LOG.critical('%s Update failure: %s', gitctl.utils.pretty(proj['name']), stderr)
                                summary.setdefault('failed', set()).add(proj['name'])
                        else:
                            updated = True

                repository.git.checkout(treeish)

            if ok:
                if gitctl.utils.is_sha1(treeish) and pinned_at is not None:
                    # If we're using pinned down revisions we only report changes when the
                    # explicit revision was changed, even if the branches were updated.
                    if pinned_at == proj['treeish']:
                        if args.verbose:
                            LOG.info('%s OK', gitctl.utils.pretty(proj['name']))
                    else:
                        LOG.info('%s Checked out revision ``%s``', gitctl.utils.pretty(proj['name']), treeish)
                        summary.setdefault('updated', set()).add(proj['name'])
                elif updated:
                    LOG.info('%s Updated', gitctl.utils.pretty(proj['name']))
                    summary.setdefault('updated', set()).add(proj['name'])
                elif args.verbose:
                    LOG.info('%s OK', gitctl.utils.pretty(proj['name']))

        else:
            # Clone the repository
            temp = git.Git('/tmp')
            temp.clone('--no-checkout', '--origin', config['upstream'],  proj['url'], path)

            # Set up the local tracking branches
            repository = git.Git(path)
            remote_branches = set(repository.branch('-r').split())
            local_branches = set(repository.branch().split())
            for remote, local in config['branches']:
                if remote in remote_branches and local not in local_branches:
                    repository.branch('-f', '--track', local, remote)
            # Check out the given treeish
            repository.checkout(proj['treeish'])
            LOG.info('%s Cloned and checked out ``%s``', gitctl.utils.pretty(proj['name']), proj['treeish'])
            summary.setdefault('cloned', set()).add(proj['name'])

    LOG_SUMMARY.info(UPDATE_SUMMARY_TMPL % {
        'total' : summary['total'],
        'updated' : len(summary.get('updated', [])),
        'cloned' : len(summary.get('cloned', [])),
        'failed' : len(summary.get('failed', [])),
        'dirty' : len(summary.get('dirty', [])),
     })

def gitctl_path(args):
    """Give the path to project directory."""
    config = gitctl.utils.parse_config(args.config)
    projects = gitctl.utils.parse_externals(args.externals)

    paths = []
    for proj in gitctl.utils.selected_projects(args, projects):
        project_path = gitctl.utils.project_path(proj, relative=args.relative)
        print project_path
        paths.append(project_path)
    return paths

def gitctl_sh(args):
    """Execute shell command in the projects' directories."""
    config = gitctl.utils.parse_config(args.config)
    projects = gitctl.utils.parse_externals(args.externals)
    result = 0

    for proj in gitctl.utils.selected_projects(args, projects):
        project_path = gitctl.utils.project_path(proj)
        subresult = os.system("cd %s; PROJECT='%s'; %s" % (project_path, proj['name'], args.command))
        if subresult != 0:
            LOG.error('%s Error while doing %s', proj["name"], args.command)
        result += subresult

    return result

def gitctl_status(args):
    """Checks the status of all external projects."""
    config = gitctl.utils.parse_config(args.config)
    projects = gitctl.utils.parse_externals(args.externals)
    
    # By default do not show commits
    commit_limit = 0
    if args.commits:
        commit_limit = None
        if args.limit > 0:
            commit_limit = args.limit

    for proj in gitctl.utils.selected_projects(args, projects):
        repository = git.Repo(gitctl.utils.project_path(proj))
        if not args.no_fetch:
            # Fetch upstream
            repository.git.fetch(config['upstream'])

        output = []
        branches = gitctl.wtf.branch_structure(repository)
        for branch_name in config['development-branch'], config['staging-branch'], config['production-branch']:
            if branch_name in branches:
                output.extend(gitctl.wtf.show_branch(repository, branches[branch_name], branches, verbose=args.verbose, commit_limit=commit_limit))

        if repository.is_dirty:
            output.append('[!] Working directory has uncommitted changes')

        if len(repository.git.diff_index('--cached', 'HEAD').strip()) > 0:
            output.append('[!] Working directory has added but uncommitted files')
        
        if len(output) > 0:
            LOG.info('')
            LOG.info('-' * len(proj['name']))
            LOG.info(proj['name'])
            LOG.info('-' * len(proj['name']))
            LOG.info('\n'.join(output))

def gitctl_pending(args):
    """Checks for pending changes between two consecutive states in our
    workflow.
    """
    config = gitctl.utils.parse_config(args.config)
    projects = gitctl.utils.parse_externals(args.externals)

    for proj in gitctl.utils.selected_projects(args, projects):
        project_path = gitctl.utils.project_path(proj)
        repository = git.Repo(project_path)
        
        local_branches = set(repository.git.branch().split())
        remote_branches = set(repository.git.branch('-r').split())
        
        def assert_branch(branch, quiet=False):
            if branch in local_branches:
                return True
            else:
                if not quiet:
                    LOG.warning('%s Branch %s does not exist', gitctl.utils.pretty(proj['name']), branch)
                return False
                
        
        if not assert_branch(config['production-branch'], quiet=True):
            # This looks to be a package that does not share our common repository layout
            # which is possible with 3rd party packages etc. We can safely ignore it.
            if not args.show_config and args.verbose:
                LOG.info('%s Skipping.', gitctl.utils.pretty(proj['name']))
            continue

        # Check for dirty working directory
        if repository.is_dirty:
            LOG.info('%s Uncommitted local changes.', gitctl.utils.pretty(proj['name']))
            continue
        
        # Update the remotes
        if not args.no_fetch:
            repository.git.fetch(config['upstream'])

        if not gitctl.utils.is_sha1(proj['treeish']):
            LOG.warning('%s Treeish is not a SHA1 revision: %s', gitctl.utils.pretty(proj['name']), proj['treeish'])
            continue
    
        from_ = repository.git.rev_parse(proj['treeish'])
        to = repository.git.rev_parse('%s/%s' % (config['upstream'], config['production-branch']))
        
        if from_ != to:
            # The comparison branch has advanced.
            if args.show_config:
                # Update the treeish to the latest version in the comparison branch.
                proj['treeish'] = to
            else:
                commits = len(repository.git.log('--pretty=oneline', '%s..%s' % (from_, to)).splitlines())
                LOG.info('%s Branch ``%s`` is %s commit(s) ahead at revision %s',
                         gitctl.utils.pretty(proj['name']), config['production-branch'], commits, to)
        else:
            if args.verbose and not args.show_config:
                LOG.info('%s OK', gitctl.utils.pretty(proj['name']))
        
    if args.show_config:
        LOG.info(gitctl.utils.generate_externals(projects))

__all__ = ['gitctl_create', 'gitctl_fetch', 'gitctl_update', 'gitctl_path', 'gitctl_sh',  'gitctl_status',
           'gitctl_pending', 'gitctl_branch']
