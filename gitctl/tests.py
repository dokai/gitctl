import unittest
import tempfile
import logging
import shutil
import mock
import copy
import os

import git
import gitctl
import gitctl.command
import gitctl.utils
import gitctl.wtf

def join(*parts):
    return os.path.realpath(os.path.abspath(os.path.join(*parts)))

class GitControlTestCase(unittest.TestCase):

    def setUp(self):
        self.path = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.path)

    def config(self, data):
        filename = os.path.join(self.path, 'gitexternals.cfg')
        open(filename, 'w').write(data)
        return filename

class CommandTestCase(unittest.TestCase):
    """Base class for gitcl command tests."""

    def setUp(self):
        # Create a temp container that will contain the test fixture. This will
        # be cleaned up after each test.
        self.container = tempfile.mkdtemp()

        # Set up a logging handler we can use in the tests
        self.output = output = []
        stream = mock.Mock()
        stream.write = lambda *args: output.append((args[0] % args[1:]).strip())
        stream.flush = lambda:None
        console = logging.StreamHandler(stream)
        formatter = logging.Formatter('%(message)s')
        console.setLevel(logging.INFO)
        console.setFormatter(formatter)
        logging.getLogger('gitctl').addHandler(console)
        logging.getLogger('gitctl').setLevel(logging.INFO)
        
        # Set up a Git repository that will mock an upstream for us
        self.upstream_path = os.path.join(self.container, 'project.git')
        os.makedirs(self.upstream_path)
        self.upstream = git.Git(self.upstream_path)
        self.upstream.init()
        
        open(os.path.join(self.upstream_path, 'foobar.txt'), 'w').write('Lorem lipsum')
        self.upstream.add('foobar.txt')
        self.upstream.commit('-m Initial commit')
        self.upstream.branch('development')
        self.upstream.branch('staging')
        self.upstream.branch('production')
        self.upstream.checkout('development')
        self.upstream.branch('-d', 'master')
        
        # Create a gitcl.cfg configuration
        open(os.path.join(self.container, 'gitctl.cfg'), 'w').write("""
[gitctl]
upstream = origin
upstream-url = %s
branches =
    development
    staging
    production
development-branch = development
staging-branch = staging
production-branch = production
commit-email = commit@non.existing.tld
commit-email-prefix = [GIT]
        """.strip() % self.container)

        # Create an externals configuration
        open(os.path.join(self.container, 'gitexternals.cfg'), 'w').write("""
[project.local]
url = %s
container = %s
type = git
treeish = development
        """.strip() % (self.upstream_path, self.container))

    def tearDown(self):
        shutil.rmtree(self.container)
        
    def clone_upstream(self, name, as_repo=False):
        """Clones the upstream repository and returns a git.Git object bound
        to the new clone.
        """
        path = os.path.join(self.container, name)
        temp = git.Git(self.container)
        temp.clone(self.upstream_path, path)
        
        clone = git.Repo(path)
        clone.git.branch('-f', '--track', 'production', 'origin/production')
        clone.git.branch('-f', '--track', 'staging', 'origin/staging')
        
        if as_repo:
            return clone
        else:
            return clone.git

class TestCommandBranch(CommandTestCase):
    """Tests for the ``branch`` command."""

    def setUp(self):
        super(self.__class__, self).setUp()
        
        self.local = self.clone_upstream('project.local', as_repo=True)
        
        # Mock some command line arguments
        self.args = mock.Mock()
        self.args.config = os.path.join(self.container, 'gitctl.cfg')
        self.args.externals = os.path.join(self.container, 'gitexternals.cfg')
        self.args.project = []
    
    def test_branch__list(self):
        self.args.list = True
        self.args.checkout = False
        
        gitctl.command.gitctl_branch(self.args)
        self.assertEquals(1, len(self.output))
        self.assertEquals('project.local .......................... development', self.output[0])
    
    def test_branch__checkout_with_dirty_working_directory(self):
        self.args.list = False
        self.args.checkout = ['development']
        
        # Make the working directory dirty.
        self.local.git.checkout('development')
        open(join(self.local.git.git_dir, 'something.py'), 'w').write('import sha\n')
        self.local.git.add('something.py')
        
        self.failUnless(self.local.is_dirty)
        gitctl.command.gitctl_branch(self.args)
        self.assertEquals(1, len(self.output))
        self.assertEquals('project.local .......................... Dirty working directory. Please commit or stash and try again.', self.output[0])
    
    def test_branch__checkout_with_same_target_branch(self):
        self.args.list = False
        self.args.checkout = ['development']
        
        self.local.git.checkout('development')
        self.assertEquals(self.local.active_branch, 'development')

        gitctl.command.gitctl_branch(self.args)
        self.assertEquals(1, len(self.output))
        self.assertEquals('project.local .......................... Already at ``development``', self.output[0])
    
    def test_branch__checkout_with_nonexisting_branch(self):
        self.args.list = False
        self.args.checkout = ['non-existing-branch']
        
        self.assertEquals(self.local.active_branch, 'development')
        gitctl.command.gitctl_branch(self.args)
        self.assertEquals(1, len(self.output))
        self.assertEquals('project.local .......................... No such branch: ``non-existing-branch``', self.output[0])
    
    def test_branch__checkout_success(self):
        self.args.list = False
        self.args.checkout = ['staging']
        
        self.local.git.checkout('development')
        self.assertEquals(self.local.active_branch, 'development')

        gitctl.command.gitctl_branch(self.args)
        self.assertEquals('staging', self.local.active_branch)
        self.assertEquals(1, len(self.output))
        self.assertEquals('project.local .......................... Checked out ``staging``', self.output[0])

class TestCommandUpdate(CommandTestCase):
    """Tests for the ``update`` command."""
    
    def test_update__clone(self):
        # Mock some command line arguments
        self.args = mock.Mock()
        self.args.config = os.path.join(self.container, 'gitctl.cfg')
        self.args.externals = os.path.join(self.container, 'gitexternals.cfg')
        self.args.project = []
        
        local_path = join(self.container, 'project.local')
        
        self.failIf(os.path.exists(local_path))
        gitctl.command.gitctl_update(self.args)
        self.failUnless(os.path.exists(local_path))
        
        repo = git.Git(local_path)
        # Make sure that we have the local tracking branches set up correctly.
        info = ' '.join(repo.remote('show', 'origin').split())
        self.failUnless(info.startswith('* remote origin'))
        self.failUnless(info.endswith("Remote branches: development tracked production tracked staging tracked Local branches configured for 'git pull': development merges with remote development production merges with remote production staging merges with remote staging Local refs configured for 'git push': development pushes to development (up to date) production pushes to production (up to date) staging pushes to staging (up to date)"), info)
        # Make sure we have the right branch checked out.
        self.assertEquals('* development', [b.strip() for b in repo.branch().splitlines() if b.startswith('*')][0])

    def test_update__pull(self):
        # Mock some command line arguments
        self.args = mock.Mock()
        self.args.config = os.path.join(self.container, 'gitctl.cfg')
        self.args.externals = os.path.join(self.container, 'gitexternals.cfg')
        self.args.project = []

        local_path = join(self.container, 'project.local')
        local = git.Git(local_path)

        # Run update once to clone the project
        gitctl.command.gitctl_update(self.args)
        self.failUnless(os.path.exists(local_path))
        # Assert that is has the initial commit only
        log = local.log('--pretty=oneline').splitlines()
        self.assertEquals(1, len(log))
        self.failUnless(log[0].endswith('Initial commit'))
        
        # Create a parallel clone, commit some changes and push them upstream
        another = self.clone_upstream('another')
        open(os.path.join(another.git_dir, 'random_addition.txt'), 'w').write('Foobar')
        another.add('random_addition.txt')
        another.commit('-m', 'Second commit')
        another.push()

        # Run update again and assert we got back the changes
        gitctl.command.gitctl_update(self.args)
        self.assertEquals(['project.local .......................... Cloned and checked out ``development``',
                           'project.local .......................... Updated'],
                          self.output)
        log = local.log('--pretty=oneline').splitlines()
        self.assertEquals(2, len(log))
        self.failUnless(log[0].endswith('Second commit'))


    def test_update__fetch_checkout(self):
        # Mock some command line arguments
        self.args = mock.Mock()
        self.args.config = os.path.join(self.container, 'gitctl.cfg')
        self.args.externals = os.path.join(self.container, 'gitexternals.cfg')
        self.args.project = []
        self.args.verbose = True

        # Get the SHA1 checksum for the current head and pin the externals to it.
        sha1_first = self.upstream.rev_parse('HEAD').strip()
        open(os.path.join(self.container, 'gitexternals.cfg'), 'w').write("""
[project.local]
url = %s
container = %s
type = git
treeish = %s
                """.strip() % (self.upstream_path, self.container, sha1_first))
        
        local_path = join(self.container, 'project.local')
        local = git.Git(local_path)

        # Run update once to clone the project
        gitctl.command.gitctl_update(self.args)
        self.failUnless(os.path.exists(local_path))
        # Assert that is has the initial commit only
        log = local.log('--pretty=oneline').splitlines()
        self.assertEquals(1, len(log))
        self.failUnless(log[0].endswith('Initial commit'))
        
        # Calling update again without changes should do nothing
        gitctl.command.gitctl_update(self.args)

        # Create a parallel clone, commit some changes and push them upstream
        another = self.clone_upstream('another')
        open(os.path.join(another.git_dir, 'random_addition.txt'), 'w').write('Foobar')
        another.add('random_addition.txt')
        another.commit('-m', 'Second commit')
        another.push()

        # Get the SHA1 of the new HEAD and update the externals again.
        sha1_second = self.upstream.rev_parse('HEAD').strip()
        open(os.path.join(self.container, 'gitexternals.cfg'), 'w').write("""
[project.local]
url = %s
container = %s
type = git
treeish = %s
                """.strip() % (self.upstream_path, self.container, sha1_second))
        
        # Run update again and assert we got back the changes
        gitctl.command.gitctl_update(self.args)
        self.assertEquals(['project.local .......................... Cloned and checked out ``%s``' % sha1_first,
                           'project.local .......................... OK',
                           'project.local .......................... Checked out revision ``%s``' % sha1_second],
                          self.output)
        log = local.log('--pretty=oneline').splitlines()
        self.assertEquals(2, len(log))
        self.failUnless(log[0].endswith('Second commit'))
        self.assertEquals(sha1_second, local.rev_parse('HEAD').strip())

    
    def test_update__rebase(self):
        # Mock some command line arguments
        self.args = mock.Mock()
        self.args.config = os.path.join(self.container, 'gitctl.cfg')
        self.args.externals = os.path.join(self.container, 'gitexternals.cfg')
        self.args.project = []

        local_path = join(self.container, 'project.local')
        local = git.Git(local_path)

        # Run update once to clone the project
        gitctl.command.gitctl_update(self.args)
        self.failUnless(os.path.exists(local_path))
        # Assert that is has the initial commit only
        log = local.log('--pretty=oneline').splitlines()
        self.assertEquals(1, len(log))
        self.failUnless(log[0].endswith('Initial commit'))
        
        # Create a parallel clone, commit some changes and push them upstream
        another = self.clone_upstream('another')
        open(os.path.join(another.git_dir, 'random_addition.txt'), 'w').write('Foobar')
        another.add('random_addition.txt')
        another.commit('-m', 'Second commit')
        another.push()

        # Run update again and assert we got back the changes
        gitctl.command.gitctl_update(self.args)
        self.assertEquals(['project.local .......................... Cloned and checked out ``development``',
                           'project.local .......................... Updated'],
                          self.output)
        log = local.log('--pretty=oneline').splitlines()
        self.assertEquals(2, len(log))
        self.failUnless(log[0].endswith('Second commit'))

    def test_update__fast_forward_ok(self):
        # Mock some command line arguments
        self.args = mock.Mock()
        self.args.config = os.path.join(self.container, 'gitctl.cfg')
        self.args.externals = os.path.join(self.container, 'gitexternals.cfg')
        self.args.project = []

        local_path = join(self.container, 'project.local')
        local = git.Git(local_path)

        # Run update once to clone the project
        gitctl.command.gitctl_update(self.args)
        self.failUnless(os.path.exists(local_path))
        # Assert that is has the initial commit only
        log = local.log('--pretty=oneline').splitlines()
        self.assertEquals(1, len(log))
        self.failUnless(log[0].endswith('Initial commit'))
        
        # Create a parallel clone, commit some changes in all branches and push them
        # upstream
        another = self.clone_upstream('another')
        for i, branch in enumerate(('development', 'staging', 'production')):
            another.checkout(branch)
            open(os.path.join(another.git_dir, 'random_addition_%d.txt' % i), 'w').write('Foobar')
            another.add('random_addition_%d.txt' % i)
            another.commit('-m', 'Second commit in %s' % branch)
        another.push()

        # Record the current branch
        current_branch = git.Repo(local.git_dir).active_branch
        # Run update again and assert we got back the changes
        gitctl.command.gitctl_update(self.args)
        self.assertEquals(['project.local .......................... Cloned and checked out ``development``',
                           'project.local .......................... Updated'],
                            self.output)
                          
        # Assert that we are still in the same branch that we started in
        self.assertEquals(current_branch, git.Repo(local.git_dir).active_branch)
        # Assert that each branch was updated
        for i, branch in enumerate(('development', 'staging', 'production')):
            local.checkout(branch)
            log = local.log('--pretty=oneline').splitlines()
            self.assertEquals(2, len(log))
            self.failUnless(log[0].endswith('Second commit in %s' % branch))
    
    def test_update__fast_forward_failure(self):
        # Mock some command line arguments
        self.args = mock.Mock()
        self.args.config = os.path.join(self.container, 'gitctl.cfg')
        self.args.externals = os.path.join(self.container, 'gitexternals.cfg')
        self.args.project = []

        local_path = join(self.container, 'project.local')
        local = git.Git(local_path)

        # Run update once to clone the project
        gitctl.command.gitctl_update(self.args)
        self.failUnless(os.path.exists(local_path))
        # Assert that is has the initial commit only
        log = local.log('--pretty=oneline').splitlines()
        self.assertEquals(1, len(log))
        self.failUnless(log[0].endswith('Initial commit'))
        
        # Create a parallel clone, commit some changes in all branches and push them
        # upstream
        another = self.clone_upstream('another')
        for i, branch in enumerate(('development', 'staging', 'production')):
            another.checkout(branch)
            open(os.path.join(another.git_dir, 'random_addition_%d.txt' % i), 'w').write('Foobar')
            another.add('random_addition_%d.txt' % i)
            another.commit('-m', 'Second commit in %s' % branch)
        another.push()
        
        # Create a local change in the development branch will make a fast-forward
        # merge impossible.
        open(os.path.join(local.git_dir, 'conflicting.txt'), 'w').write('CONFLICT!')
        local.add('conflicting.txt')
        local.commit('-m', 'local change')
        
        # Record the current branch
        current_branch = git.Repo(local.git_dir).active_branch
        # Run update again and assert we got back the changes
        gitctl.command.gitctl_update(self.args)
        self.assertEquals(['project.local .......................... Cloned and checked out ``development``',
                           'project.local .......................... Fast forward merge not possible for branch ``development``. Try syncing with upstream manually (pull, push or merge).'],
                            self.output)

        # Assert that we are still in the same branch that we started in
        self.assertEquals(current_branch, git.Repo(local.git_dir).active_branch)

        # Assert that the non-conflicting branches were updated
        for i, branch in enumerate(('staging', 'production')):
            local.checkout(branch)
            log = local.log('--pretty=oneline').splitlines()
            self.assertEquals(2, len(log))
            self.failUnless(log[0].endswith('Second commit in %s' % branch))

class TestCommandFetch(CommandTestCase):
    """Tests for the ``fetch`` command."""

    def setUp(self):
        super(self.__class__, self).setUp()
        
        self.local = self.clone_upstream('project.local')
        
        # Mock some command line arguments
        self.args = mock.Mock()
        self.args.config = os.path.join(self.container, 'gitctl.cfg')
        self.args.externals = os.path.join(self.container, 'gitexternals.cfg')
        self.args.project = []

    def test_fetch(self):
        # Create another local clone, add a file and push to make the remote
        # ahead of self.local.
        another = self.clone_upstream('another')
        open(os.path.join(another.git_dir, 'random_addition.txt'), 'w').write('Foobar')
        another.add('random_addition.txt')
        another.commit('-m', 'Fubu')
        another.push()

        # Assert that our local tracking branch is at the same revision with the
        # remote
        self.assertEquals(self.local.rev_parse('development'),
                          self.local.rev_parse('origin/development'))
        # Fetch changes from upstream
        gitctl.command.gitctl_fetch(self.args)
        self.assertEquals('project.local .......................... Fetched', self.output[0])
        self.failIfEqual(self.local.rev_parse('development'),
                         self.local.rev_parse('origin/development'))


class TestCommandPending(CommandTestCase):
    """Tests for the ``pending`` command."""

    def setUp(self):
        super(self.__class__, self).setUp()
        
        self.local = self.clone_upstream('project.local')
        
        # Mock some command line arguments
        self.args = mock.Mock()
        self.args.config = os.path.join(self.container, 'gitctl.cfg')
        self.args.externals = os.path.join(self.container, 'gitexternals.cfg')
        self.args.show_config = False
        self.args.diff = False

    def test_pending__third_party_package(self):
        # Create a new repository to act as our second, third-party upstream.
        # This will simply contain the default 'master' branch without our
        # dev/staging/production setup.
        thirdparty_path = os.path.join(self.container, 'thirdparty.git')
        os.makedirs(thirdparty_path)
        thirdparty = git.Git(thirdparty_path)
        thirdparty.init()
        
        open(os.path.join(thirdparty_path, 'TOP_SECRET.txt'), 'w').write('Lorem lipsum')
        thirdparty.add('TOP_SECRET.txt')
        thirdparty.commit('-m Initial commit')

        # Add the configuration to our gitexternals.cfg configuration
        open(os.path.join(self.container, 'gitexternals.cfg'), 'w').write("\n\n" + """
[thirdparty.local]
url = %s
container = %s
type = git
treeish = master
        """.strip() % (thirdparty_path, self.container))

        # Create a local clone
        thirdparty.clone(thirdparty_path, join(self.container, 'thirdparty.local'))
        
        # Assert the third party repositories are skipped
        gitctl.command.gitctl_pending(self.args)
        self.assertEquals('thirdparty.local ....................... Skipping.', self.output[0])

    def test_pending__dirty_working_directory(self):
        self.args.dev = True
        
        # Create a new commit in the development branch and then modify the file
        # without committing.
        self.local.checkout('development')
        open(join(self.local.git_dir, 'something.py'), 'w').write('import sha\n')
        self.local.add('something.py')
        self.local.commit('-m', 'Important')
        open(join(self.local.git_dir, 'something.py'), 'a').write('s = sha.new()')

        # Assert that we notice that the working directory is dirty
        gitctl.command.gitctl_pending(self.args)
        self.assertEquals('project.local .......................... Uncommitted local changes.',
                          self.output[0])

    def test_pending__production_without_pinned_revision(self):
        # By default all the branches are in-sync with each other
        gitctl.command.gitctl_pending(self.args)
        self.assertEquals('project.local .......................... Treeish is not a SHA1 revision: development', self.output[0])

    def test_pending__production_advanced_over_pinned_versions(self):

        # Create a new gitexternals.cfg configuration that uses a pinned version
        pinned = self.local.rev_parse('production').strip()
        open(join(self.container, 'gitexternals.cfg'), 'w').write("""
[project.local]
url = %s
container = %s
type = git
treeish = %s
        """ % (self.upstream_path, self.container, pinned))
        
        # Commit a new change into the production branch
        self.local.checkout('production')
        open(join(self.local.git_dir, 'something.py'), 'w').write('import sha\n')
        self.local.add('something.py')
        self.local.commit('-m', 'Important')
        self.local.push()
        
        gitctl.command.gitctl_pending(self.args)
        self.failUnless(self.output[0].startswith('project.local .......................... Branch ``production`` is 1 commit(s) ahead of the pinned down version at revision'))

    def test_pending__show_config(self):
        self.args.production = True
        self.args.show_config = True

        # Create a new gitexternals.cfg configuration that uses a pinned version
        pinned = self.local.rev_parse('production').strip()
        open(join(self.container, 'gitexternals.cfg'), 'w').write("""
[project.local]
url = %s
container = %s
type = git
treeish = %s
        """ % (self.upstream_path, self.container, pinned))

        # Commit a new change into the production branch
        self.local.checkout('production')
        open(join(self.local.git_dir, 'something.py'), 'w').write('import sha\n')
        self.local.add('something.py')
        self.local.commit('-m', 'Important')
        self.local.push()
        # Get the SHA1 of the HEAD of production
        head = self.local.rev_parse('production').strip()

        gitctl.command.gitctl_pending(self.args)
        self.assertEquals(1, len(self.output))
        self.failUnless(self.output[0].strip().endswith(head))

class TestCommandStatus(CommandTestCase):
    """Tests for the ``status`` command."""

    def setUp(self):
        super(self.__class__, self).setUp()
        
        self.local = self.clone_upstream('project.local')
        
        # Mock some command line arguments
        self.args = mock.Mock()
        self.args.config = os.path.join(self.container, 'gitctl.cfg')
        self.args.externals = os.path.join(self.container, 'gitexternals.cfg')
        self.args.project = []
        self.args.no_fetch = False

    def test_status__ok(self):
        gitctl.command.gitctl_status(self.args)
        self.assertEquals(1, len(self.output))
        self.assertEquals('project.local .......................... OK', self.output[0])
    
    def test_status__dirty_working_directory(self):
        open(os.path.join(self.local.git_dir, 'make_wd_dirty.txt'), 'w').write('Lorem')
        self.local.add('make_wd_dirty.txt')
        
        gitctl.command.gitctl_status(self.args)
        self.assertEquals(1, len(self.output))
        self.assertEquals('project.local .......................... Uncommitted local changes', self.output[0])

    def test_status__out_of_sync__local_advanced(self):
        open(os.path.join(self.local.git_dir, 'new_file.txt'), 'w').write('Lorem')
        self.local.add('new_file.txt')
        self.local.commit('-m', 'Foobar')
        
        gitctl.command.gitctl_status(self.args)
        self.assertEquals(1, len(self.output))
        self.assertEquals('project.local .......................... Branch ``development`` out of sync with upstream', self.output[0])

    def test_status__out_of_sync__remote_advanced(self):
        # Create another local clone, add a file and push to make the remote
        # ahead of self.local.
        another = self.clone_upstream('another')
        open(os.path.join(another.git_dir, 'random_addition.txt'), 'w').write('Foobar')
        another.add('random_addition.txt')
        another.commit('-m', 'Fubu')
        another.push()
        
        gitctl.command.gitctl_status(self.args)
        self.assertEquals(1, len(self.output))
        self.assertEquals('project.local .......................... Branch ``development`` out of sync with upstream', self.output[0])
        

class TestUtils(unittest.TestCase):
    """Tests for the utility functions."""

    def setUp(self):
        self.path = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.path)
    
    def test_pretty(self):
        self.assertEquals('foobar ...', gitctl.utils.pretty('foobar', 10))
        self.assertEquals('barfoo              ', gitctl.utils.pretty('barfoo', 20, ' '))

    def test_project_path__absolute(self):
        proj1 = {'container' : 'foo', 'name' : 'bar' }
        proj2 = {'container' : '/foo/bar', 'name' : 'froobnoz' }
        self.assertEquals(os.path.join(os.getcwd(), 'foo/bar'), gitctl.utils.project_path(proj1, relative=False))
        self.assertEquals('/foo/bar/froobnoz', gitctl.utils.project_path(proj2, relative=False))

    def test_project_path__relative(self):
        proj1 = {'container' : 'foo', 'name' : 'bar' }
        proj2 = {'container' : os.path.join(os.getcwd(), 'foo', 'bar'),
                 'name' : 'froobnoz' }

        self.assertEquals('foo/bar', gitctl.utils.project_path(proj1, relative=True))
        self.assertEquals('foo/bar/froobnoz', gitctl.utils.project_path(proj2, relative=True))

    def test_is_sha1_too_short(self):
        self.failIf(gitctl.utils.is_sha1('123456790abcdef'))

    def test_is_sha1_too_long(self):
        self.failIf(gitctl.utils.is_sha1('123456790abcdef123456790abcdef123456790abcdef123456790abcdef'))

    def test_is_sha1_valid(self):
        self.failUnless(gitctl.utils.is_sha1('1234567890abcdef1234567890abcdef12345678'))

    def test_is_sha1_invalid(self):
        self.failIf(gitctl.utils.is_sha1('12345678ghijkl1234567890abcdef12345678'))

    def test_parse_config__invalid_file(self):
        self.assertRaises(ValueError, lambda: gitctl.utils.parse_config(['/non/existing/path']))
    
    def test_parse_config__missing_section(self):
        config = os.path.join(self.path, 'foo.cfg')
        open(config, 'w').write("[invalid]")
        self.assertRaises(ValueError, lambda: gitctl.utils.parse_config([config]))
    
    def test_parse_config(self):
        config = os.path.join(self.path, 'gitctl.cfg')
        open(config, 'w').write("""
[gitctl]
upstream = upstream
upstream-url = git@github.com:dokai
branches =
    development
    staging
    production
    experimental
development-branch = development
staging-branch = staging
production-branch = production
commit-email = commit@non.existing.tld
commit-email-prefix = [GIT]
        """.strip())
        conf = gitctl.utils.parse_config([config])
        self.assertEquals('upstream', conf['upstream'])
        self.assertEquals('git@github.com:dokai', conf['upstream-url'])
        self.assertEquals([('upstream/development', 'development'),
                           ('upstream/staging', 'staging'),
                           ('upstream/production', 'production'),
                           ('upstream/experimental', 'experimental')],
                           conf['branches'])
        self.assertEquals('development', conf['development-branch'])
        self.assertEquals('staging', conf['staging-branch'])
        self.assertEquals('production', conf['production-branch'])
        self.assertEquals('commit@non.existing.tld', conf['commit-email'])
        self.assertEquals('[GIT]', conf['commit-email-prefix'])


    def test_parse_externals(self):
        ext = os.path.join(self.path, 'gitexternals.cfg')
        open(ext, 'w').write("""
[my.project]
url = git@github.com:dokai/my-project
container = src
type = git
treeish = development

[your.project]
url = git@github.com:dokai/your-project
container = src
type = git
treeish = master
        """.strip())
        projects = gitctl.utils.parse_externals(ext)
        self.assertEquals([{'container': 'src',
                            'name': 'my.project',
                            'treeish': 'development',
                            'type': 'git',
                            'url': 'git@github.com:dokai/my-project'},
                           {'container': 'src',
                            'name': 'your.project',
                            'treeish': 'master',
                            'type': 'git',
                            'url': 'git@github.com:dokai/your-project'}],
                           projects)

    def test_generate_externals(self):
        projects = [{'container': 'src',
                     'name': 'my.project',
                     'treeish': 'development',
                     'type': 'git',
                     'url': 'git@github.com:dokai/my-project'},
                    {'container': 'src',
                     'name': 'your.project',
                     'treeish': 'master',
                     'type': 'git',
                     'url': 'git@github.com:dokai/your-project'}]
        self.assertEquals("""
[my.project]
url = git@github.com:dokai/my-project
type = git
container = src
treeish = development

[your.project]
url = git@github.com:dokai/your-project
type = git
container = src
treeish = master
         """.strip(), gitctl.utils.generate_externals(projects).strip())
    
    def test_externals_roundtrip(self):
        projects = [{'container': 'src',
                     'name': 'my.project',
                     'treeish': 'development',
                     'type': 'git',
                     'url': 'git@github.com:dokai/my-project'},
                     {'container': 'src',
                     'name': 'your.project',
                     'treeish': 'master',
                     'type': 'git',
                     'url': 'git@github.com:dokai/your-project'}]

        ext = os.path.join(self.path, 'gitexternals.cfg')
        open(ext, 'w').write(gitctl.utils.generate_externals(copy.deepcopy(projects)))

        self.assertEquals(projects, gitctl.utils.parse_externals(ext))

class TestWTF(unittest.TestCase):
    """Test for the wtf helpers."""
    
    def setUp(self):
        self.paths = []
    
    def tearDown(self):
        for path in self.paths:
            shutil.rmtree(path)

    def tmpdir(self):
        self.paths.append(tempfile.mkdtemp())
        return self.paths[-1]
    
    def test_branch_structure(self):
        # Remote repository that will be cloned
        remote_repo_path = self.tmpdir()
        remote_repo = git.Git(remote_repo_path)
        remote_repo.init()
        open(join(remote_repo_path, 'foobar.py'), 'w').write('import sha')
        remote_repo.add('foobar.py')
        remote_repo.commit('-m', 'first commit')
        remote_repo.checkout('-b', 'mybranch1')
        open(join(remote_repo_path, 'bar.py'), 'w').write('import md5')
        remote_repo.add('bar.py')
        remote_repo.commit('-m', 'bar')
        remote_repo.checkout('master')
        remote_repo.checkout('-b', 'mybranch2')
        open(join(remote_repo_path, 'foo.py'), 'w').write('import md5')
        remote_repo.add('foo.py')
        remote_repo.commit('-m', 'foo')
        remote_repo.checkout('master')

        # Local repository 
        repo_path = self.tmpdir()
        remote_repo.clone(remote_repo_path, repo_path)
        repo = git.Git(repo_path)
        # Create local tracking branches
        repo.checkout('--track', '-b', 'local_mybranch1', 'origin/mybranch1')
        repo.checkout('--track', '-b', 'local_mybranch2', 'origin/mybranch2')
        # Create local feature branches
        repo.checkout('-b', 'feature1', 'master')
        repo.checkout('-b', 'feature2', 'master')
        
        structure = gitctl.wtf.branch_structure(git.Repo(repo_path))
        self.assertEquals(structure, {
            'feature1': {
                'local_branch': 'heads/feature1',
                'name': 'feature1'},
            'feature2': {
                'local_branch': 'heads/feature2',
                'name': 'feature2'},
            'local_mybranch1': {
                'local_branch': 'heads/local_mybranch1',
                'name': 'local_mybranch1',
                'remote': 'origin',
                'remote_branch': 'origin/mybranch1',
                'remote_mergepoint': 'mybranch1',
                'remote_url': remote_repo_path},
            'local_mybranch2': {
                'local_branch': 'heads/local_mybranch2',
                'name': 'local_mybranch2',
                'remote': 'origin',
                'remote_branch': 'origin/mybranch2',
                'remote_mergepoint': 'mybranch2',
                'remote_url': remote_repo_path},
            'master': {
                'local_branch': 'heads/master',
                'name': 'master',
                'remote': 'origin',
                'remote_branch': 'origin/master',
                'remote_mergepoint': 'master',
                'remote_url': remote_repo_path},
            'origin/mybranch1': {
                'name': 'origin/mybranch1',
                'remote': 'origin',
                'remote_branch': 'origin/mybranch1',
                'remote_url': remote_repo_path},
            'origin/mybranch2': {
                'name': 'origin/mybranch2',
                'remote': 'origin',
                'remote_branch': 'origin/mybranch2',
                'remote_url': remote_repo_path}})

    
    def test_commits_between(self):
        repo_path = self.tmpdir()
        repo = git.Git(repo_path)
        repo.init()
        
        open(join(repo_path, 'foobar.py'), 'w').write('import sha')
        repo.add('foobar.py')
        repo.commit('-m', 'first commit')

        open(join(repo_path, 'foobar.py'), 'w').write('import md5')
        repo.add('foobar.py')
        repo.commit('-m', 'second commit')

        open(join(repo_path, 'foobar.py'), 'w').write('import sha')
        repo.add('foobar.py')
        repo.commit('-m', 'third commit')
        
        commits = gitctl.wtf.commits_between(git.Repo(repo_path), 'HEAD^^', 'HEAD')
        self.assertEquals(2, len(commits))
        self.failUnless('third commit' in commits[0])
        self.failUnless('second commit' in commits[1])
    
    def test_show_commits__no_limit(self):
        commits = 'commit1 commit2 commit3 commit4'.split()
        self.assertEquals(gitctl.wtf.show_commits(commits, limit=None),
            ['    commit1', '    commit2', '    commit3', '    commit4'])
    
    def test_show_commits__custom_prefix(self):
        commits = 'commit1 commit2 commit3 commit4'.split()
        self.assertEquals(gitctl.wtf.show_commits(commits, prefix='> ', limit=None),
            ['> commit1', '> commit2', '> commit3', '> commit4'])
    
    def test_show_commits__limit_less_than_commits(self):
        commits = 'commit1 commit2 commit3 commit4'.split()
        self.assertEquals(gitctl.wtf.show_commits(commits, limit=2),
            ['    commit1', '    commit2', '    ... and 2 more'])
    
    def test_show_commits__limit_greater_than_commits(self):
        commits = 'commit1 commit2 commit3 commit4'.split()
        self.assertEquals(gitctl.wtf.show_commits(commits, limit=10),
            ['    commit1', '    commit2', '    commit3', '    commit4'])
    
    def test_ahead_behind__both(self):
        self.assertEquals(gitctl.wtf.ahead_behind(range(3), range(4)),
            '3 commit(s) ahead; 4 commit(s) behind')

    def test_ahead_behind__ahead_only(self):
        self.assertEquals(gitctl.wtf.ahead_behind(range(3), []), '3 commit(s) ahead')

    def test_ahead_behind__behind_only(self):
        self.assertEquals(gitctl.wtf.ahead_behind([], range(3)), '3 commit(s) behind')

    def test_ahead_behind__neither(self):
        self.assertEquals(gitctl.wtf.ahead_behind([], []), '')
    
    def test_show_branch(self):
        pass

def test_suite():
    return unittest.TestSuite([
            #unittest.makeSuite(TestCommandStatus),
            unittest.makeSuite(TestCommandPending),
            unittest.makeSuite(TestCommandFetch),
            unittest.makeSuite(TestCommandUpdate),
            unittest.makeSuite(TestCommandBranch),
            unittest.makeSuite(TestUtils),
            unittest.makeSuite(TestWTF),
            ])
