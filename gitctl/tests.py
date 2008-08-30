import unittest
import tempfile
import shutil
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


def test_suite():
    return unittest.TestSuite([
            unittest.makeSuite(TestUtils),
            ])
