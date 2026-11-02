import tempfile
from pathlib import Path
import unittest
from brain import connect, sync, search, context, graph


class BrainTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.vault = self.root / 'vault'
        self.vault.mkdir()
        self.db = connect(self.root / 'test.sqlite', self.vault)

    def tearDown(self):
        self.db.close()
        self.temp.cleanup()

    def test_update_delete_and_citations(self):
        note = self.vault / 'Project.md'
        note.write_text('alpha evidence', encoding='utf-8')
        sync(self.db, self.vault)
        self.assertIn('[Project.md:L1]', context(search(self.db, 'alpha')))
        note.write_text('beta evidence', encoding='utf-8')
        sync(self.db, self.vault)
        self.assertEqual(search(self.db, 'alpha'), [])
        self.assertEqual(len(search(self.db, 'beta')), 1)
        note.unlink()
        self.assertEqual(sync(self.db, self.vault)['deleted_files'], 1)
        self.assertEqual(search(self.db, 'beta'), [])

    def test_hidden_external_and_graph(self):
        (self.vault / '.private').mkdir()
        (self.vault / '.private' / 'secret.md').write_text('secret')
        outside = self.root / 'outside.md'
        outside.write_text('secret')
        (self.vault / 'external.md').symlink_to(outside)
        (self.vault / 'A.md').write_text('[[B]] [[Missing]]')
        (self.vault / 'B.md').write_text('public')
        sync(self.db, self.vault)
        self.assertEqual(search(self.db, 'secret'), [])
        self.assertEqual(graph(self.db)['edges'], [{'source': 'A.md', 'target': 'B.md'}])

    def test_query_budget_and_vault_identity(self):
        (self.vault / 'A.md').write_text('alpha ' * 1000)
        sync(self.db, self.vault)
        self.assertTrue(search(self.db, '"alpha" OR ('))
        self.assertLessEqual(len(context(search(self.db, 'alpha'), 500)), 500)
        other = self.root / 'other'
        other.mkdir()
        with self.assertRaises(ValueError):
            connect(self.root / 'test.sqlite', other)


if __name__ == '__main__':
    unittest.main()
