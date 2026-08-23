import unittest

from sunkenhold.themes import THEMES, get_theme, T
from sunkenhold.items import glyph_for, Item, CAT_POTION, CAT_WEAPON
from sunkenhold.content import SPECIES

TOKENS = [n for n in dir(T) if not n.startswith("_")]


class TestThemes(unittest.TestCase):
    def test_every_theme_defines_every_token(self):
        for name, table in THEMES.items():
            for tok in TOKENS:
                self.assertIn(tok, table,
                              f"theme {name} missing token {tok}")
                fg16, fg256 = table[tok]
                self.assertTrue(0 <= fg16 <= 15)
                self.assertTrue(0 <= fg256 <= 255)

    def test_get_theme_fallback(self):
        self.assertIs(get_theme("nonexistent"), get_theme("classic"))


class TestGlyphs(unittest.TestCase):
    def test_monster_letters_unique(self):
        letters = [s.letter for s in SPECIES.values()]
        self.assertEqual(len(letters), len(set(letters)))

    def test_item_category_glyphs_distinct_from_monsters(self):
        item_glyphs = {glyph_for(Item(k, cat)) for k, cat in [
            ("potion_heal", CAT_POTION), ("shortsword", CAT_WEAPON)]}
        for g in item_glyphs:
            self.assertNotIn(g, set(letters := [s.letter.upper()
                                                for s in SPECIES.values()]))


if __name__ == "__main__":
    unittest.main()
