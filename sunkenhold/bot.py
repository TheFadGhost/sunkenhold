"""Heuristic headless agent that plays through the same public actions."""
from . import combat, content as C, items as I
from . import progression as PROG
from .engine import POISON as POISON_MARK, BURNING as BURN_MARK


HARD_FOES = {"brute", "poolwatcher", "weaver", "warden", "skitterking"}


class Bot:
    """Greedy but cautious delver used by the simulation harness."""

    def __init__(self, game, rng, mode="greedy"):
        self.g = game
        self.rng = rng
        self.mode = mode
        self.fleeing = 0
        self.avoid = {}
        self.chase = None
        self.ignore_forever = set()

    def _ignored(self):
        return set(self.avoid) | self.ignore_forever

    def _rush_step(self):
        g = self.g
        p = g.player
        lv = g.current_level()
        if p.hp * 100 < p.max_hp * 60:
            pots = [i for i in p.inventory
                    if i.category == I.CAT_POTION]
            known_heal = [i for i in pots if g.state.known_items.get(i.key)
                          and C.POTIONS[i.key]["effect"] == "heal"]
            pick = None
            if known_heal:
                pick = known_heal[0]
            elif pots and p.hp * 100 < p.max_hp * 20:
                pick = pots[0]
            if pick:
                g.act_quaff(pick)
                self.flush()
                return True
        if POISON_MARK in p.statuses or BURN_MARK in p.statuses:
            cure = [i for i in p.inventory
                    if i.category == I.CAT_POTION
                    and g.state.known_items.get(i.key)
                    and C.POTIONS[i.key]["effect"] == "cure"]
            if cure:
                g.act_quaff(cure[0])
                self.flush()
                return True
        here = lv.items.get(p.pos, [])
        if here and here[0].category != I.CAT_SALVAGE \
                and len(getattr(p, "inventory", [])) < I.BACKPACK_CAP:
            g.act_pickup()
            self.flush()
            return True
        dest = lv.up if g.has_artefact() or (lv.down is None) else lv.down
        adj = [m for m in g.enemies_visible()
               if max(abs(m.x - p.x), abs(m.y - p.y)) <= 1]
        if len(adj) >= 2 and p.hp * 100 < p.max_hp * 55:
            self.fleeing = 4
        if self.fleeing > 0:
            self.fleeing -= 1
            nxt = self.flee_dir()
            if nxt:
                g.act_move(nxt[0] - p.x, nxt[1] - p.y)
                self.flush()
                return True
        if p.pos == tuple(dest):
            if g.has_artefact() or lv.down is None or g.depth == 1:
                g.act_ascend()
            else:
                g.act_descend()
            self.flush()
            return True
        from .pathing import path_to
        steps = path_to(lv, p.pos, tuple(dest))
        if not steps:
            nxt = g.explore_next(ignore_ids=self._ignored())
            if nxt is None:
                g.act_wait()
                self.flush()
                return True
            steps = [nxt]
        nxt = steps[0]
        g.act_move(nxt[0] - p.x, nxt[1] - p.y)
        self.flush()
        return True

    def choose_levelup(self):
        prefs = ["prowess", "ferocity", "vitality", "guard", "ironblood",
                 "swiftness", "farsight", "trait_regen", "trait_hunter",
                 "trait_stoic"]
        choices = PROG.roll_levelup_choices(self.g.rng)
        for want in prefs:
            if want in choices:
                PROG.apply_levelup(self.g, want)
                self.g.player.flags["pending_levelups"] -= 1
                return

    def _potions(self):
        inv = getattr(self.g.player, "inventory", [])
        return [i for i in inv if i.category == I.CAT_POTION]

    def _quaff_best(self):
        p = self.g.player
        pots = self._potions()
        heal_known = [i for i in pots if self.g.state.known_items.get(i.key)
                      and C.POTIONS[i.key]["effect"] == "heal"]
        if heal_known:
            self.g.act_quaff(heal_known[0])
            self.flush()
            return True
        unknown = [i for i in pots if not self.g.state.known_items.get(i.key)]
        if unknown and p.hp * 100 < p.max_hp * 30:
            self.g.act_quaff(unknown[0])
            self.flush()
            return True
        return False

    def flush(self):
        g = self.g
        if g.pending:
            g.run_until_player_input()
        while g.player.alive and not g.victory \
                and g.player.flags.get("pending_levelups", 0) > 0:
            self.choose_levelup()

    def _try_ranged(self, foe):
        g = self.g
        p = g.player
        bow = p.equipment.get("weapon")
        if bow is None or bow.category != I.CAT_RANGED:
            bows = [i for i in p.inventory if i.category == I.CAT_RANGED]
            has_arrows = I.total_arrows(g.state) > 0
            dist = max(abs(foe.x - p.x), abs(foe.y - p.y))
            hard = foe.species in HARD_FOES or \
                C.SPECIES[foe.species].ranged_dmg is not None
            if bows and has_arrows and (hard or dist >= 3):
                g.act_equip(bows[0])
                self.flush()
                return True
            return False
        if I.total_arrows(g.state) == 0:
            return False
        dist = max(abs(foe.x - p.x), abs(foe.y - p.y))
        if dist <= 2:
            return False
        g.act_fire(foe)
        self.flush()
        return True

    def combat_step(self, foes):
        g = self.g
        p = g.player
        for k in list(self.avoid):
            self.avoid[k] -= 1
            if self.avoid[k] <= 0:
                del self.avoid[k]
        foes = [m for m in foes if m.id not in self._ignored()]
        if not foes:
            return False
        foes.sort(key=lambda m: abs(m.x - p.x) + abs(m.y - p.y))
        near = foes[0]
        if near.species in HARD_FOES \
                and not (abs(near.x - p.x) <= 1 and abs(near.y - p.y) <= 1):
            if self._try_ranged(near):
                return True
            wands = [i for i in p.inventory
                     if i.category == I.CAT_WAND and i.charges > 0
                     and i.key != "wand_tunnel"]
            if wands:
                from .fov import bresenham_los as _bl
                if _bl(g.current_level(), p.x, p.y, near.x, near.y):
                    g.act_zap(wands[0], near)
                    self.flush()
                    return True
            self.ignore_forever.add(near.id)
            self.chase = None
            if p.hp * 100 < p.max_hp * 70:
                self.fleeing = 8
            return False
        dist = abs(near.x - p.x) + abs(near.y - p.y)
        if self.chase and self.chase[0] == near.id:
            _, best, stale = self.chase
            if dist < best:
                best, stale = dist, 0
            else:
                stale += 1
            self.chase = (near.id, best, stale)
            if stale > 6 and p.hp * 100 < p.max_hp * 60:
                self.ignore_forever.add(near.id)
                self.avoid.pop(near.id, None)
                self.chase = None
                g.add_message("You disengage.", "neutral")
                return False
        else:
            self.chase = (near.id, dist, 0)
        hp_frac = p.hp / p.max_hp
        if hp_frac < 0.4 and self._quaff_best():
            return True
        if self.fleeing > 0:
            self.fleeing -= 1
            nxt = self.flee_dir()
            if nxt:
                g.act_move(nxt[0] - p.x, nxt[1] - p.y)
                self.flush()
                return True
        weak = near.hp <= 6 or C.SPECIES[near.species].xp <= 8
        if hp_frac < 0.22 and not weak:
            self.fleeing = 5
            nxt = self.flee_dir()
            if nxt:
                g.act_move(nxt[0] - p.x, nxt[1] - p.y)
                self.flush()
                return True
        if self._try_ranged(near):
            return True
        from .pathing import path_to
        lv = g.current_level()
        steps = path_to(lv, p.pos, (near.x, near.y))
        if steps and len(steps) > 1:
            nxt = steps[0]
            g.act_move(nxt[0] - p.x, nxt[1] - p.y)
            self.flush()
            return True
        if steps and len(steps) == 1:
            dx = (near.x > p.x) - (near.x < p.x)
            dy = (near.y > p.y) - (near.y < p.y)
            g.act_move(dx, dy)
            self.flush()
            return True
        self.avoid[near.id] = 40
        self.chase = None
        return False

    def flee_dir(self):
        from .pathing import step_away
        g = self.g
        occ = {(g.player.x, g.player.y)}
        return step_away(g.current_level(), g.player.x, g.player.y,
                         g.dmap, occ)

    def manage_gear(self):
        g = self.g
        p = g.player
        cur_w = p.equipment.get("weapon")
        if cur_w is not None and cur_w.category == I.CAT_RANGED \
                and I.total_arrows(g.state) > 0 \
                and [m for m in g.enemies_visible()
                     if not m.flags.get("asleep")]:
            return False
        cur_score = -99
        if cur_w and cur_w.category == I.CAT_WEAPON:
            w = C.WEAPONS[cur_w.key]
            cur_score = _dice_avg(w["dmg"]) + w["acc_mod"] * 0.3 \
                + cur_w.enchant
        best_i = None
        best_s = cur_score
        for it in list(p.inventory):
            if it.category == I.CAT_WEAPON:
                w = C.WEAPONS[it.key]
                s = _dice_avg(w["dmg"]) + w["acc_mod"] * 0.3 + it.enchant
                if s > best_s + 0.01 and not it.cursed:
                    best_s, best_i = s, it
        if best_i is not None:
            g.act_equip(best_i)
            self.flush()
            return True
        cur_a = p.equipment.get("armour")
        ca = C.ARMOURS[cur_a.key]["absorb"] + cur_a.enchant if cur_a else -1
        cur_s = p.equipment.get("shield")
        cs = C.ARMOURS[cur_s.key]["absorb"] + cur_s.enchant if cur_s else -1
        for it in list(p.inventory):
            if it.category == I.CAT_ARMOUR:
                a = C.ARMOURS[it.key]
                slot = a["slot"]
                held = p.equipment.get(slot)
                hs = C.ARMOURS[held.key]["absorb"] + held.enchant \
                    if held else -1
                mine = a["absorb"] + it.enchant
                if not it.cursed and mine > hs + 0:
                    g.act_equip(it)
                    self.flush()
                    return True
        return False

    def descend_ok(self):
        p = self.g.player
        pots = len(self._potions())
        return p.hp * 100 >= p.max_hp * 65 or \
            (pots >= 2 and p.hp * 100 >= p.max_hp * 50)

    def _beeline(self, dest):
        """Sprint toward dest; fight only what stands in the way."""
        g = self.g
        p = g.player
        from .pathing import path_to
        lv = g.current_level()
        if p.pos == tuple(dest):
            return False
        steps = path_to(lv, p.pos, tuple(dest))
        if not steps:
            return False
        nxt = steps[0]
        dx, dy = nxt[0] - p.x, nxt[1] - p.y
        g.act_move(dx, dy)
        self.flush()
        return True

    def _find_heart(self):
        lv = self.g.current_level()
        for pos, items in lv.items.items():
            for it in items:
                if it.category == I.CAT_ARTEFACT:
                    return pos
        return None

    def _endgame(self):
        g = self.g
        p = g.player
        lv = g.current_level()
        adj = [m for m in g.enemies_visible()
               if max(abs(m.x - p.x), abs(m.y - p.y)) <= 1]
        if adj and p.hp * 100 > p.max_hp * 25:
            return self.combat_step(adj)
        heal_frac = 0.7 if g.has_artefact() else 0.55
        if p.hp * 100 < p.max_hp * heal_frac:
            pots = [i for i in p.inventory if i.category == I.CAT_POTION]
            known = [i for i in pots if g.state.known_items.get(i.key)
                     and C.POTIONS[i.key]["effect"] == "heal"]
            pick = (known or ([pots[0]] if pots else [None]))[0]
            if pick is not None:
                g.act_quaff(pick)
                self.flush()
                return True
        if p.hp * 100 < p.max_hp * 98 and not g.pathing_threats():
            g.start_rest()
            g.run_until_player_input()
            return True
        if g.has_artefact():
            return self._beeline(lv.up)
        if self._find_heart() is not None:
            return self._beeline(self._find_heart())
        all_ids = {m.id for m in g.enemies_visible()}
        nxt = g.explore_next(ignore_ids=all_ids)
        if nxt is not None:
            g.act_move(nxt[0] - p.x, nxt[1] - p.y)
            self.flush()
            return True
        return False

    def step(self):
        """One player action. Returns False when the run is over."""
        g = self.g
        p = g.player
        if not p.alive or g.victory:
            return False
        lv = g.current_level()
        if g.depth != getattr(self, "_last_depth", None):
            self._last_depth = g.depth
            self._head_stairs = False
            self._floor_enter_t = g.state.turn
        if self.mode == "rush":
            return self._rush_step()
        p = g.player
        if g.depth == 12 or g.has_artefact():
            if self.manage_gear():
                return True
            if self._endgame():
                return True
        if self.make_room():
            return True

        for sc in list(p.inventory):
            if sc.category != I.CAT_SCROLL:
                continue
            if not g.state.known_items.get(sc.key):
                continue
            eff = C.SCROLLS[sc.key]["effect"]
            if eff == "enchant_weapon" and p.equipment.get("weapon"):
                g.act_read(sc)
                self.flush()
                return True
            if eff == "enchant_armour" and (p.equipment.get("armour")
                                            or p.equipment.get("shield")):
                g.act_read(sc)
                self.flush()
                return True
            if eff == "magic_mapping" and g.depth >= 3:
                g.act_read(sc)
                self.flush()
                return True

        here = lv.items.get(p.pos, [])
        if here and here[0].category != I.CAT_SALVAGE:
            g.act_pickup()
            self.flush()
            return True
        if POISON_MARK in p.statuses or BURN_MARK in p.statuses:
            pots = [i for i in p.inventory
                    if i.category == I.CAT_POTION]
            cure = [i for i in pots
                    if g.state.known_items.get(i.key)
                    and C.POTIONS[i.key]["effect"] == "cure"]
            if cure:
                g.act_quaff(cure[0])
                self.flush()
                return True
            unknown = [i for i in pots
                       if not g.state.known_items.get(i.key)]
            if p.hp * 100 < p.max_hp * 75 and unknown:
                g.act_quaff(unknown[0])
                self.flush()
                return True
            if BURN_MARK in p.statuses:
                water = self._nearest_water()
                if water:
                    from .pathing import path_to
                    steps = path_to(lv, p.pos, water)
                    if steps:
                        nxt = steps[0]
                        g.act_move(nxt[0] - p.x, nxt[1] - p.y)
                        self.flush()
                        return True

        foes = g.enemies_visible()
        adj_any = [m for m in foes
                   if max(abs(m.x - p.x), abs(m.y - p.y)) <= 1
                   and not m.flags.get("asleep", False)]
        if adj_any:
            target = min(adj_any, key=lambda m: m.hp)
            g.act_move(target.x - p.x, target.y - p.y)
            self.flush()
            return True
        awake_foes = [m for m in foes if not m.flags.get("asleep")]
        if awake_foes:
            if self.combat_step(awake_foes):
                return True
        if p.hp * 100 < p.max_hp * 85:
            pots = [i for i in p.inventory
                    if i.category == I.CAT_POTION]
            heal_known = [i for i in pots
                          if g.state.known_items.get(i.key)
                          and C.POTIONS[i.key]["effect"] == "heal"]
            unknown = [i for i in pots
                       if not g.state.known_items.get(i.key)]
            pick = None
            if p.hp * 100 < p.max_hp * 55:
                pick = (heal_known or unknown or [None])[0]
            elif p.hp * 100 < p.max_hp * 70 and heal_known \
                    and not g.pathing_threats():
                pick = heal_known[0]
            if pick is not None:
                g.act_quaff(pick)
                self.flush()
                return True
            if g.pathing_threats():
                if p.hp * 100 < p.max_hp * 55 and self._door_retreat():
                    return True
            elif self._rest_burst():
                return True

        carrying = g.has_artefact()
        target_stairs = lv.up if carrying else lv.down
        if not carrying and target_stairs and p.pos == tuple(target_stairs) \
                and self.descend_ok():
            g.act_descend()
            self.flush()
            return True
        if carrying and p.pos == tuple(lv.up):
            g.act_ascend()
            self.flush()
            return True
        if not carrying and lv.down is None and p.pos == tuple(lv.up):
            g.act_ascend()
            self.flush()
            return True

        explore_nxt = g.explore_next(ignore_ids=self._ignored())
        go_stairs = getattr(self, "_head_stairs", False)
        if not carrying and target_stairs is not None:
            if not go_stairs:
                down_seen = lv.seen[target_stairs[1] * lv.w
                                    + target_stairs[0]]
                long_hall = (g.state.turn
                             - getattr(self, "_floor_enter_t", 0)) > 2500
                if down_seen or self._stairs_close(target_stairs) \
                        or explore_nxt is None or long_hall:
                    go_stairs = True
                elif p.hp * 100 >= p.max_hp * 75 and \
                        self._stairs_seen_any(lv):
                    go_stairs = True
            if go_stairs:
                self._head_stairs = True
        dest = target_stairs if (not carrying and target_stairs is not None
                                 and go_stairs) else None
        if dest is not None and p.pos != tuple(dest):
            from .pathing import path_to
            steps = path_to(lv, p.pos, tuple(dest))
            if steps:
                nxt = steps[0]
                g.act_move(nxt[0] - p.x, nxt[1] - p.y)
                self.flush()
                return True
        if go_stairs and dest is not None:
            nxt = g.explore_next(ignore_ids=self._ignored())
            self._head_stairs = False
            if nxt is None:
                g.act_wait()
                self.flush()
                return True
        nxt = explore_nxt
        if nxt is not None:
            self._guard_dither(p.pos, nxt)
            g.act_move(nxt[0] - p.x, nxt[1] - p.y)
            self.flush()
            return True
        if not carrying and lv.down and p.pos != tuple(lv.down):
            from .pathing import path_to
            steps = path_to(lv, p.pos, lv.down)
            if steps:
                nxt = steps[0]
                g.act_move(nxt[0] - p.x, nxt[1] - p.y)
                self.flush()
                return True
        g.act_wait()
        self.flush()
        return True

    def _stairs_close(self, s):
        p = self.g.player
        return abs(s[0] - p.x) + abs(s[1] - p.y) <= 12

    def _stairs_seen_any(self, lv):
        s = lv.down
        return bool(s and lv.seen[s[1] * lv.w + s[0]])

    def make_room(self):
        """If the pack is full and something worth taking is here, drop junk."""
        g = self.g
        p = g.player
        inv = getattr(p, "inventory", [])
        here = g.current_level().items.get(p.pos, [])
        wants = [i for i in here if i.category != I.CAT_SALVAGE]
        if not wants or len(inv) < I.BACKPACK_CAP:
            return False
        victim = min(inv, key=lambda it: self._value(it))
        g.act_drop(victim)
        self.flush()
        return True

    def _value(self, it):
        g = self.g
        known = g.state.known_items.get(it.key, False)
        c = it.category
        if c == I.CAT_POTION:
            e = C.POTIONS[it.key]["effect"]
            base = {"heal": 9, "greater_heal": 10, "cure": 7}.get(e, 2)
            return base if known else 4
        if c == I.CAT_SCROLL:
            e = C.SCROLLS[it.key]["effect"]
            base = {"magic_mapping": 6, "remove_curse": 5,
                    "enchant_weapon": 5, "teleport": 4}.get(e, 3)
            return base if known else 3
        if c == I.CAT_WAND:
            return 3 + it.charges * (1 if known else 0.2)
        if c == I.CAT_WEAPON:
            w = C.WEAPONS[it.key]
            cur = g.player.equipment.get("weapon")
            cs = -1
            if cur and cur.category == I.CAT_WEAPON:
                cw = C.WEAPONS[cur.key]
                cs = _dice_avg(cw["dmg"]) + cw["acc_mod"] * 0.3 + cur.enchant
            s = _dice_avg(w["dmg"]) + w["acc_mod"] * 0.3 + it.enchant
            return 11 + s - cs if not it.cursed else 0
        if c == I.CAT_ARMOUR:
            a = C.ARMOURS[it.key]
            slot = a["slot"]
            held = g.player.equipment.get(slot)
            hs = -1
            if held and held.category == I.CAT_ARMOUR:
                ha = C.ARMOURS[held.key]
                hs = ha["absorb"] + held.enchant
            return 11 + a["absorb"] + it.enchant - hs \
                if a["slot"] in ("armour", "shield") and not it.cursed else 0
        if c == I.CAT_RANGED:
            has_arrows = any(i.category == I.CAT_AMMO
                             for i in g.player.inventory)
            bow = g.player.equipment.get("weapon")
            better = bow is None or bow.category != I.CAT_RANGED
            return 8 if has_arrows and better else 1
        if c == I.CAT_AMMO:
            bow = g.player.equipment.get("weapon")
            return 5 if bow and bow.category == I.CAT_RANGED else 1
        if c == I.CAT_CHARM:
            return 4 if not it.cursed else 0
        return 1

    def _guard_dither(self, pos, nxt):
        """Track recent (from,to) steps; when a transition repeats, force an
        alternate step so explore cannot ping-pong between two pockets."""
        from collections import deque
        if not hasattr(self, "_recent"):
            self._recent = deque(maxlen=8)
        key = (tuple(pos), tuple(nxt))
        if self._recent.count(key) >= 2:
            lv = self.g.current_level()
            tried = [k[1] for k in list(self._recent)[-4:]]
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    if dx == 0 and dy == 0:
                        continue
                    a = (pos[0] + dx, pos[1] + dy)
                    if lv.walkable(*a) and a not in tried:
                        self._recent.clear()
                        nxt = a
                        return
        self._recent.append(key)

    def _nearest_water(self):
        lv = self.g.current_level()
        best, bd = None, 1 << 30
        p = self.g.player
        for idx in range(lv.w * lv.h):
            if lv.tiles[idx] == 7 and lv.seen[idx]:
                x, y = idx % lv.w, idx // lv.w
                d = abs(x - p.x) + abs(y - p.y)
                if d < bd:
                    bd = d
                    best = (x, y)
        return best if bd <= 20 else None

    def _door_retreat(self):
        """Shut an adjacent open door between us and trouble, then rest."""
        g = self.g
        p = g.player
        lv = g.current_level()
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                x, y = p.x + dx, p.y + dy
                if lv.in_bounds(x, y) and lv.tile(x, y) == 3 \
                        and lv.monster_at(x, y) is None:
                    g.act_close(dx, dy)
                    self.flush()
                    return True
        return False

    def _rest_burst(self):
        g = self.g
        p = g.player
        if p.hp * 100 >= p.max_hp * 85:
            return False
        if p.hp * 100 < p.max_hp * 55 and g.enemies_visible():
            if self._door_retreat():
                return True
        for _ in range(12):
            before = p.hp
            g.start_rest()
            g.run_until_player_input()
            if not g.player.alive:
                break
            if p.hp < before:
                break
            if g.threats_visible():
                break
            if p.hp >= p.max_hp:
                break
        return True


def _dice_avg(spec):
    import re
    m = re.fullmatch(r"(\d+)d(\d+)", spec)
    n, d = int(m.group(1)), int(m.group(2))
    return n * (d + 1) / 2

