import unittest

from sunkenhold.game import Game
from sunkenhold.items import (Item, add_to_inventory, BACKPACK_CAP,
                              CAT_POTION, CAT_WEAPON, CAT_SCROLL,
                              display_name, is_known)
from sunkenhold.rng import RNG


def fresh(seed=3):
    g = Game(seed)
    g.new_game()
    return g


class TestInventory(unittest.TestCase):
    def test_stacking(self):
        g = fresh(41)
        start = sum(i.qty for i in g.player.inventory
                    if i.key == "potion_heal")
        for _ in range(5):
            self.assertTrue(add_to_inventory(
                g.state, Item("potion_heal", CAT_POTION, qty=1)))
        stacks = [i for i in g.player.inventory
                  if i.key == "potion_heal"]
        self.assertEqual(len(stacks), 1)
        self.assertEqual(stacks[0].qty, start + 5)

    def test_cap(self):
        g = fresh(42)
        inv = g.player.inventory
        while len(inv) < BACKPACK_CAP:
            inv.append(Item("potion_swift", CAT_POTION))
        ok = add_to_inventory(g.state, Item("potion_might", CAT_POTION))
        self.assertFalse(ok)

    def test_identification_by_use(self):
        g = fresh(43)
        it = Item("potion_might", CAT_POTION)
        g.player.inventory.append(it)
        self.assertFalse(is_known(g.state, it))
        g.act_quaff(it)
        g.run_until_player_input()
        self.assertTrue(g.state.known_items.get("potion_might", False))


class TestCurses(unittest.TestCase):
    def make_cursed_weapon(self, seed=44):
        g = fresh(seed)
        w = Item("longsword", CAT_WEAPON, cursed=True, enchant=-1)
        g.player.inventory.append(w)
        return g, w

    def test_cursed_equips_then_locks(self):
        g, w = self.make_cursed_weapon()
        g.act_equip(w)
        g.run_until_player_input()
        self.assertIs(g.player.equipment["weapon"], w)
        g.act_unequip("weapon")
        g.run_until_player_input()
        self.assertIs(g.player.equipment["weapon"], w)

    def test_remove_curse_frees(self):
        g, w = self.make_cursed_weapon()
        g.act_equip(w)
        g.run_until_player_input()
        sc = Item("scroll_uncurse", CAT_SCROLL)
        g.player.inventory.append(sc)
        g.act_read(sc)
        g.run_until_player_input()
        self.assertFalse(w.cursed)
        g.act_unequip("weapon")
        g.run_until_player_input()
        self.assertIsNone(g.player.equipment["weapon"])


class TestWands(unittest.TestCase):
    def test_charges_decrement_and_empty_fizzles(self):
        g = fresh(45)
        w = Item("wand_ember", "wand", charges=1)
        g.player.inventory.append(w)
        lv = g.current_level()
        if not lv.monsters:
            self.skipTest("no monster on this floor")
        m = lv.monsters[0]
        m.flags["asleep"] = False
        g.act_zap(w, m)
        g.run_until_player_input()
        self.assertEqual(w.charges, 0)
        hp0 = m.hp
        g.act_zap(w, m)
        g.run_until_player_input()
        self.assertEqual(m.hp, hp0)


if __name__ == "__main__":
    unittest.main()
