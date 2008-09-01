import unittest
import tempfile
import logging
import shutil
import mock
import copy
import os

from StringIO import StringIO

import git
import gitctl
import gitctl.command
import gitctl.utils

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
        
    def clone_upstream(self, name):
        """Clones the upstream repository and returns a git.Git object bound
        to the new clone.
        """
        path = os.path.join(self.container, name)
        temp = git.Git(self.container)
        temp.clone(self.upstream_path, path)
        
        clone = git.Git(path)
        clone.branch('-f', '--track', 'production', 'origin/production')
        clone.branch('-f', '--track', 'staging', 'origin/staging')
        
        return clone

class TestCommandUpdate(CommandTestCase):
    """Tests for the ``update`` command."""
    
    def test_update__clone(self):
        # Mock some command line arguments
        self.args = mock.Mock()
        self.args.config = os.path.join(self.container, 'gitctl.cfg')
        self.args.externals = os.path.join(self.container, 'gitexternals.cfg')
        
        local_path = join(self.container, 'project.local')
        
        self.failIf(os.path.exists(local_path))
        gitctl.command.gitctl_update(self.args)
        self.failUnless(os.path.exists(local_path))
        
        repo = git.Git(local_path)
        # Make sure that we have the local tracking branches set up correctly.
        info = ' '.join(repo.remote('show', 'origin').split())
        self.failUnless(info.startswith('* remote origin'))
        self.failUnless(info.endswith('Tracked remote branches development production staging'))
        # Make sure we have the right branch checked out.
        self.assertEquals('* development', [b.strip() for b in repo.branch().splitlines() if b.startswith('*')][0])

    def test_update__pull(self):
        # Mock some command line arguments
        self.args = mock.Mock()
        self.args.config = os.path.join(self.container, 'gitctl.cfg')
        self.args.externals = os.path.join(self.container, 'gitexternals.cfg')
        self.args.rebase = False

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
        self.assertEquals(['project.local................. Cloned and checked out ``development``',
                           'project.local................. Pulled'],
                          self.output)
        log = local.log('--pretty=oneline').splitlines()
        self.assertEquals(2, len(log))
        self.failUnless(log[0].endswith('Second commit'))
    
    def test_update__rebase(self):
        self.fail()

class TestCommandStatus(CommandTestCase):
    """Tests for the ``status`` command."""

    def setUp(self):
        super(self.__class__, self).setUp()
        
        self.local = self.clone_upstream('project.local')
        
        # Mock some command line arguments
        self.args = mock.Mock()
        self.args.config = os.path.join(self.container, 'gitctl.cfg')
        self.args.externals = os.path.join(self.container, 'gitexternals.cfg')
        self.args.no_fetch = False

    def test_status__ok(self):
        gitctl.command.gitctl_status(self.args)
        self.assertEquals(1, len(self.output))
        self.assertEquals('project.local................. OK', self.output[0])
    
    def test_status__dirty_working_directory(self):
        open(os.path.join(self.local.git_dir, 'make_wd_dirty.txt'), 'w').write('Lorem')
        self.local.add('make_wd_dirty.txt')
        
        gitctl.command.gitctl_status(self.args)
        self.assertEquals(1, len(self.output))
        self.assertEquals('project.local................. Uncommitted local changes', self.output[0])

    def test_status__out_of_sync__local_advanced(self):
        open(os.path.join(self.local.git_dir, 'new_file.txt'), 'w').write('Lorem')
        self.local.add('new_file.txt')
        self.local.commit('-m', 'Foobar')
        
        gitctl.command.gitctl_status(self.args)
        self.assertEquals(1, len(self.output))
        self.assertEquals('project.local................. Branch ``development`` out of sync with upstream', self.output[0])

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
        self.assertEquals('project.local................. Branch ``development`` out of sync with upstream', self.output[0])
        

class TestUtils(unittest.TestCase):
    """Tests for the utility functions."""

    def setUp(self):
        self.path = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.path)
    
    def test_pretty(self):
        self.assertEquals('foobar....', gitctl.utils.pretty('foobar', 10))
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

    def test_is_dirty__clean(self):
        repo = git.Git(self.path)
        repo.init()
        open(os.path.join(self.path, 'foobar.txt'), 'w').write('Lorem lipsum')
        repo.add('foobar.txt')
        repo.commit('-m "dummy"')
        
        self.failIf(gitctl.utils.is_dirty(repo))
    
    def test_is_dirty__dirty_working_directory(self):
        repo = git.Git(self.path)
        repo.init()
        open(os.path.join(self.path, 'foobar.txt'), 'w').write('Lorem lipsum')
        repo.add('foobar.txt')
        repo.commit('-m "dummy"')
        open(os.path.join(self.path, 'foobar.txt'), 'w').write('Lipsum lorem')
        
        self.failUnless(gitctl.utils.is_dirty(repo))
        
    def test_is_dirty__dirty_index(self):
        repo = git.Git(self.path)
        repo.init()
        open(os.path.join(self.path, 'foobar.txt'), 'w').write('Lorem lipsum')
        repo.add('foobar.txt')
        repo.commit('-m "dummy"')
        open(os.path.join(self.path, 'foobar.txt'), 'w').write('Lipsum lorem')
        repo.add('foobar.txt')

        self.failUnless(gitctl.utils.is_dirty(repo))

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
                            'name': 'your.project',
                            'treeish': 'master',
                            'type': 'git',
                            'url': 'git@github.com:dokai/your-project'},
                           {'container': 'src',
                            'name': 'my.project',
                            'treeish': 'development',
                            'type': 'git',
                            'url': 'git@github.com:dokai/my-project'}],
                           projects)

    def test_generate_externals(self):
        projects = [{'container': 'src',
                     'name': 'your.project',
                     'treeish': 'master',
                     'type': 'git',
                     'url': 'git@github.com:dokai/your-project'},
                    {'container': 'src',
                     'name': 'my.project',
                     'treeish': 'development',
                     'type': 'git',
                     'url': 'git@github.com:dokai/my-project'}]
        self.assertEquals("""
[your.project]
url = git@github.com:dokai/your-project
container = src
type = git
treeish = master

[my.project]
url = git@github.com:dokai/my-project
container = src
type = git
treeish = development
         """.strip(), gitctl.utils.generate_externals(projects).strip())
    
    def test_externals_roundtrip(self):
        projects = [{'container': 'src',
                     'name': 'your.project',
                     'treeish': 'master',
                     'type': 'git',
                     'url': 'git@github.com:dokai/your-project'},
                    {'container': 'src',
                     'name': 'my.project',
                     'treeish': 'development',
                     'type': 'git',
                     'url': 'git@github.com:dokai/my-project'}]

        ext = os.path.join(self.path, 'gitexternals.cfg')
        open(ext, 'w').write(gitctl.utils.generate_externals(copy.deepcopy(projects)))

        self.assertEquals(projects, gitctl.utils.parse_externals(ext))

def test_suite():
    return unittest.TestSuite([
            unittest.makeSuite(TestCommandStatus),
            unittest.makeSuite(TestCommandUpdate),
            unittest.makeSuite(TestUtils),
            ])
