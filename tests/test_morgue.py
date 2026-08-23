import os
import tempfile
import unittest

from sunkenhold import morgue


class TestMorgue(unittest.TestCase):
    def setUp(self):
        fd, self.path = tempfile.mkstemp(prefix="sh_morgue_",
                                         suffix=".jsonl")
        os.close(fd)
        os.remove(self.path)

    def test_append_load_scores(self):
        morgue.append_record(self.path, {"score": 10, "seed": 1,
                                         "won": False, "depth": 2})
        morgue.append_record(self.path, {"score": 400, "seed": 2,
                                         "won": True, "depth": 12})
        recs = morgue.load_records(self.path)
        self.assertEqual(len(recs), 2)
        top = morgue.top_scores(self.path, 1)
        self.assertEqual(top[0]["score"], 400)

    def test_corrupt_lines_tolerated(self):
        with open(self.path, "w", encoding="utf-8") as f:
            f.write('{"score": 5, "won": false, "depth": 1}\n')
            f.write("GARBAGE LINE\n")
            f.write("\n")
            f.write('{"score": 7}\n')
        recs = morgue.load_records(self.path)
        self.assertEqual(len(recs), 2)


if __name__ == "__main__":
    unittest.main()
