import unittest
import tempfile
import shutil
import copy
import os

import git
import gitctl
import gitctl.command
import gitctl.utils


class GitControlTestCase(unittest.TestCase):

    def setUp(self):
        self.path = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.path)

    def config(self, data):
        filename = os.path.join(self.path, 'gitexternals.cfg')
        open(filename, 'w').write(data)
        return filename

class TestCommandCreate(unittest.TestCase):
    """Tests for the ``create`` command."""

class TestCommandStatus(unittest.TestCase):
    """Tests for the ``status`` command."""

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
            unittest.makeSuite(TestUtils),
            ])
