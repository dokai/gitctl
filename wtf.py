import git
import re


RE_CONFIG_REMOTE_URL = re.compile(r'^remote\.([^.]+)\.url (.+)$')
RE_CONFIG_REMOTE_BRANCH = re.compile(r'branch\.([^.]*)\.remote (.+)')
RE_CONFIG_REMOTE_MERGE = re.compile(r'branch\.([^.]*)\.merge (?:(?:refs/)?heads/)?(.+)')

RE_REF_LOCAL_BRANCH = re.compile(r'^heads/(.+)$')
RE_REF_REMOTE_BRANCH = re.compile(r'^remotes/([^/]+)/(.+)$')

def remotes(repository):
    """Returns a dictionary of remote URLs keyed by the remote name."""
    urls = {}
    for line in repository.git.config('--get-regexp', '^remote.*.url', with_exceptions=False).splitlines():
        match = RE_CONFIG_REMOTE_URL.search(line.strip())
        if match is not None:
            urls[match.group(1)] = match.group(2)
    
    return urls

def followed_branches(repository):
    """Returns a dictionary..."""
    result = {}
    remote_urls = remotes(repository)
    for line in repository.git.config('--get-regexp', '^branch.', with_exceptions=False).splitlines():
        remote_match = RE_CONFIG_REMOTE_BRANCH.search(line.strip())
        
        if remote_match is not None:
            result.setdefault(remote_match.group(1), {}).update(
                remote=remote_match.group(2),
                remote_url=remote_urls[remote_match.group(2)])
        else:
            merge_match = RE_CONFIG_REMOTE_MERGE.search(line.strip())
            if merge_match is not None:
                result.setdefault(merge_match.group(1), {}).update(
                    remote_mergepoint=merge_match.group(2))

    return result

def all_branches(repository):
    # A mapping of remote names to remote URLs
    remote_urls = {}
    for line in repository.git.config('--get-regexp', '^remote.*.url', with_exceptions=False).splitlines():
        match = RE_CONFIG_REMOTE_URL.search(line.strip())
        if match is not None:
            remote_urls[match.group(1)] = match.group(2)

    branches = {}
    # A mapping of branches that are tracked
    for line in repository.git.config('--get-regexp', '^branch.', with_exceptions=False).splitlines():
        remote_match = RE_CONFIG_REMOTE_BRANCH.search(line.strip())
        
        if remote_match is not None:
            branches.setdefault(remote_match.group(1), {}).update(
                remote=remote_match.group(2),
                remote_url=remote_urls[remote_match.group(2)])
        else:
            merge_match = RE_CONFIG_REMOTE_MERGE.search(line.strip())
            if merge_match is not None:
                branches.setdefault(merge_match.group(1), {}).update(
                    remote_mergepoint=merge_match.group(2))

    # Add the rest of the branches
    for line in repository.git.show_ref(with_exceptions=False).splitlines():
        sha1, ref = [a.strip() for a in line.strip().split(' refs/')][:2]

        local_branch_match = RE_REF_LOCAL_BRANCH.search(ref)
        if local_branch_match is not None:
            name = local_branch_match.group(1)
            if name == 'HEAD':
                continue
            branches.setdefault(name, {}).update(name=name, local_branch=ref)
        else:
            remote_branch_match = RE_REF_REMOTE_BRANCH.search(ref)
            if remote_branch_match is not None:
                remote, name = remote_branch_match.group(1), remote_branch_match.group(2)
                if name == 'HEAD':
                    continue
                branch = name
                if name in branches and branches[name]['remote'] == remote:
                    pass
                else:
                    name = '%s/%s' % (remote, branch)
                
                branches.setdefault(name, {}).update(
                    name=name,
                    remote=remote,
                    remote_branch='%s/%s' % (remote, branch),
                    remote_url=remote_urls[remote])

    # Add the remote branch information
    for name, branch in branches.iteritems():
        if 'remote' in branch and 'remote_mergepoint' in branch:
            branch['remote_branch'] = '%s/%s' % (branch['remote'], branch['remote_mergepoint'])
    
    return branches

def commits_between(repository, from_, to, verbose=False):
    """Returns a list of commits in ``to`` that are not in ``from_``.
    
    If the return value is an empty list ``to`` has been merged to ``from_``.
    """
    if verbose:
        format = r'--pretty=format:- %s [%h] (%ae; %ar)'
    else:
        format = r'--pretty=format:- %s [%h]'
    
    return [line.strip()
            for line
            in repository.git.log(format, '%s..%s' % (from_, to)).splitlines()
            if line.strip()]

def show_commits(commits, prefix="    ", limit=5):
    if limit is None:
        limit = len(commits)
    for commit in commits[:limit]:
        print '%s%s' % (prefix, commit)
    if len(commits) > limit:
        print '%s... and %s more' % (prefix, len(commits) - limit)

def ahead_behind(ahead, behind):
    return '; '.join(filter(None, (
        len(ahead) > 0 and '%s commit(s) ahead' % len(ahead) or None,
        len(behind) > 0 and '%s commit(s) behind' % len(behind) or None)))

def show_branch(repository, branch_info, all_branches, verbose=True, with_commits=True):
    have_both = 'local_branch' in branch_info and 'remote_branch' in branch_info
    push_commits = tuple()
    pull_commits = tuple()
    local_remote_out_of_sync = False
    print 
    print branch_info['name']
    print '-' * len(branch_info['name'])

    if have_both:
        push_commits = commits_between(repository, branch_info['remote_branch'], branch_info['local_branch'])
        pull_commits = commits_between(repository, branch_info['local_branch'], branch_info['remote_branch'])
        local_remote_out_of_sync = len(push_commits) > 0 and len(pull_commits) > 0
    
    if 'local_branch' in branch_info:
        #print 'Local branch:', branch_info['local_branch']
    
        if have_both:
            if len(push_commits) == 0:
                if verbose:
                    print '%s in sync with remote' % branch_info['local_branch']
            else:
                action = local_remote_out_of_sync and 'push after rebase / merge' or 'push'
                print '%s NOT in sync with remote (needs %s)' % (branch_info['local_branch'], action)
                if with_commits:
                    show_commits(push_commits)
    
    if 'remote_branch' in branch_info:
        #print 'Remote branch: %s (%s)' % (branch_info['remote_branch'], branch_info['remote_url'])
        
        if have_both:
            name = '%(remote_branch)s (%(remote_url)s)' % branch_info
            if len(pull_commits) == 0:
                if verbose:
                    print '%s in sync with local' % name
            else:
                action = len(push_commits) == 0 and 'merge' or 'rebase / merge'
                print '%s NOT in sync with local (needs %s)' % (name, action)
                if with_commits:
                    show_commits(pull_commits)

    is_feature_branch = lambda b: b not in ('primacontrol/development', 'primacontrol/demo', 'primacontrol/production')
    feature_branches = [b for b in all_branches if is_feature_branch(b)]
    main_branches = [b for b in all_branches if not is_feature_branch(b)]

    if len(main_branches) > 0:
        print 'Main branches:'
        for branch_name in sorted(main_branches):
            if branch_name == branch_info['name']:
                continue
            branch = all_branches[branch_name]
            local_only = 'remote_branch' not in branch
            ahead = commits_between(repository, branch_name, branch_info.get('local_branch', branch_info.get('remote_branch')))
            if len(ahead) == 0:
                print '  [x] merged into %s' % branch_name
            else:
                print '  [!] NOT merged into %s (%s commit(s) ahead)' % (branch_name, len(ahead))
                if with_commits:
                    show_commits(ahead)

    if len(feature_branches) > 0 and branch_info['name'] == 'primacontrol/development':
        print 'Feature branches:'
        for branch_name in feature_branches:
            branch = all_branches[branch_name]
            local_only = 'remote_branch' not in branch
            remote_only = 'local_branch' not in branch
            # For remote_only branch we'll compute wrt the remote branch head,
            # otherwise we'll use the local branch head.
            head = remote_only and branch['remote_branch'] or branch['local_branch']
            
            remote_ahead = 'remote_branch' in branch_info and commits_between(repository, branch_info['remote_branch'], head) or []
            local_ahead = 'local_branch' in branch_info and commits_between(repository, branch_info['local_branch'], head) or []
            
            if len(local_ahead) == len(remote_ahead) == 0:
                if verbose:
                    print '  Feature branch %s is merged into %s and pushed upstream.' % (branch['name'], branch_info['name'])
            elif len(local_ahead) == 0:
                print '  Feature branch %s merged into %s only locally and waiting to be pushed' % (branch['name'], branch_info['name'])
            else:
                behind = commits_between(repository, head, branch.get('local_branch', branch.get('remote_branch')))
                ahead = remote_only and remote_ahead or local_ahead
                print '  Feature branch %s is NOT merged into %s. %s.' % (branch['name'], branch_info['name'], ahead_behind(ahead, behind))
                if with_commits:
                    show_commits(ahead)

    
    if local_remote_out_of_sync:
        print 'Local and remote branches have diverged. A merge will occur unless you rebase.'
        
def repository_status(repository):
    branches = all_branches(repository)
    for branch in ('primacontrol/development', 'primacontrol/demo', 'primacontrol/production'):
        show_branch(repository, branches[branch], branches)

if __name__ == '__main__':
    #pprint(remotes(git.Repo('.')))
    #pprint(followed_branches(git.Repo('.')))
    #repository_status(git.Repo('/Users/dokai/Software/Development/primacontrol.buildout'))
    repository_status(git.Repo('/Users/dokai/Software/Development/primacontrol.buildout/products/PrimaControlSite'))