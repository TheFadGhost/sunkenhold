"""Game orchestration: scheduler, player actions, world rules, run lifecycle."""
from collections import deque

from . import ai as AI
from . import combat, content as C, items as I, pathing
from . import progression as PROG
from .engine import (NORMAL_COST, POISON, BURNING, STUN, SLOW, CONFUSED,
                     Actor, GameState, RNG, apply_status, move_cost,
                     tick_status, clear_movement_blockers)
from .fov import bresenham_los, compute_fov_glow
from .items import Item, CAT_ARTEFACT, CAT_AMMO, CAT_SALVAGE
from .mapgen import generate_level, populate, make_monster

MOVE_COST_BUMP = 25


class DeathOfRun(Exception):
    pass


class Game:
    def __init__(self, seed, wizard=False):
        self.state = GameState(seed, RNG(seed))
        self.rng = self.state.rng
        self.wizard = wizard
        self.pending = deque()
        self.visible = set()
        self.dmap = {}
        self.death_cause = None
        self.victory = False
        self._next_id = 1
        self.autosave_fn = None
        self.delete_save_fn = None
        self.interrupt_reason = None

    def alloc_id(self):
        i = self._next_id
        self._next_id += 1
        return i

    @classmethod
    def from_state(cls, state_dict, wizard=False):
        g = cls(state_dict["seed"], wizard=wizard)
        g.state = GameState.from_dict(state_dict, I.Item.from_dict)
        g.rng = g.state.rng
        max_id = g.state.player.id
        for lv in g.state.levels.values():
            for m in lv.monsters:
                max_id = max(max_id, m.id)
        g._next_id = max_id + 1
        return g

    @property
    def player(self):
        return self.state.player

    @property
    def seed(self):
        return self.state.seed

    @property
    def stats(self):
        return self.state.stats

    @property
    def depth(self):
        return self.state.depth

    def add_message(self, text, kind="neutral"):
        self.state.add_message(text, kind)

    def current_level(self):
        return self.state.current_level()

    def new_game(self):
        s = self.state
        s.appearances = I.assign_appearances(self.rng)
        p = PROG.make_player(self.alloc_id)
        s.player = p
        self.ensure_level(1)
        p.x, p.y = self.current_level().up
        sword = Item("shortsword", I.CAT_WEAPON)
        tunic = Item("rag_tunic", I.CAT_ARMOUR)
        p.equipment["weapon"] = sword
        p.equipment["armour"] = tunic
        I.add_to_inventory(s, Item("potion_heal", I.CAT_POTION, qty=4))
        I.add_to_inventory(s, Item("shortbow", I.CAT_RANGED))
        I.add_to_inventory(s, Item("arrows", I.CAT_AMMO, qty=12))
        s.known_items["potion_heal"] = True
        s.add_message("You know healing draughts by their coppery smell.",
                      "info")
        s.stats["deepest"] = 1
        self.refresh_vision()
        s.add_message("You descend into Sunkenhold, seeking the Tideglass "
                      "Heart.", "info")
        s.add_message("Move with arrows or hjklyubn. ? shows help.", "neutral")

    def ensure_level(self, depth):
        if depth in self.state.levels:
            return
        lv_seed = _level_seed(self.seed, depth)
        lv, gen_rng = generate_level(depth, lv_seed, artefact=(depth == 12))
        self.state.levels[depth] = lv
        saved_rng, self.rng = self.rng, gen_rng
        populate(lv, gen_rng, lv.up, self.alloc_id)
        self.rng = saved_rng
        self.refresh_dmap()

    # ---------------- perception ----------------

    def refresh_dmap(self):
        if self.player is None:
            return
        key = (self.player.x, self.player.y, self.state.depth)
        if getattr(self, "_dmap_key", None) == key:
            return
        self._dmap_key = key
        self.dmap = pathing.dijkstra_map(
            self.current_level(), [(self.player.x, self.player.y)])

    def glow_tiles(self):
        lv = self.current_level()
        gt = getattr(lv, "glow_tiles", None)
        if gt is None:
            lv.glow_tiles = [
                (x % lv.w, x // lv.w)
                for x in range(lv.w * lv.h) if lv.tiles[x] in (8, 9)]
            gt = lv.glow_tiles
        return gt

    def refresh_vision(self):
        lv = self.current_level()
        vis = compute_fov_glow(lv, self.player.x, self.player.y,
                               self.eff_sight(), self.glow_tiles())
        self.visible = vis
        for x, y in vis:
            lv.seen[y * lv.w + x] = 1
        for m in lv.monsters:
            if m.alive and m.pos in vis:
                PROG.update_memory(self.state, m.species, "seen")
        self._tutorial_check()

    def _tutorial_check(self):
        t = getattr(self.state, "tutorial", None)
        if t is None or "moved" not in t:
            return
        if "item_hint" not in t:
            for pos, its in self.current_level().items.items():
                if pos in self.visible and its:
                    t.add("item_hint")
                    self.state.add_message(
                        "Stand on an item and press g to take it.", "info")
                    break
        if "enemy_hint" not in t and self.enemies_visible():
            t.add("enemy_hint")
            self.state.add_message(
                "Walk into a foe to strike it. x examines, ? shows help.",
                "info")
        lv = self.current_level()
        if "stairs_hint" not in t and lv.down and lv.down in self.visible:
            t.add("stairs_hint")
            self.state.add_message(
                "Stairs down are marked >. Stand on them and press >.",
                "info")

    def enemies_visible(self):
        lv = self.current_level()
        return [m for m in lv.monsters
                if m.alive and m.pos in self.visible]

    def threats_visible(self):
        """Awake monsters in sight, plus anything adjacent (sleeping foes
        included — stepping next to one wakes it)."""
        p = self.player
        out = []
        for m in self.enemies_visible():
            if not m.flags.get("asleep", False) \
                    or max(abs(m.x - p.x), abs(m.y - p.y)) <= 1:
                out.append(m)
        return out

    def pathing_threats(self):
        """Threats that should interrupt auto-movement: adjacent anything,
        or an awake monster genuinely close (closing in). Distant shooters
        do not get to pin the player in place forever."""
        p = self.player
        out = []
        for m in self.enemies_visible():
            d = max(abs(m.x - p.x), abs(m.y - p.y))
            if d <= 1:
                out.append(m)
            elif not m.flags.get("asleep", False) and d <= 5:
                out.append(m)
        return out

    # ---------------- scheduler ----------------

    def run_until_player_input(self):
        """Advance the world until the player owes an input decision.
        Every actor gains energy each pass; actors spend it on actions (fast
        actors act more often, leftover energy carries over). When the player
        must choose an action, the remaining actors of THIS pass still act."""
        guard = 0
        while self.player.alive and not self.victory:
            guard += 1
            if guard > 100000:
                raise RuntimeError("scheduler failed to reach player turn")
            lv = self.current_level()
            order = [self.player] + sorted(
                [m for m in lv.monsters if m.alive], key=lambda m: m.id)
            acted = False
            for a in order:
                if not a.alive:
                    continue
                a.energy += _eff_speed(a)
                spends = 0
                while a.energy >= NORMAL_COST and a.alive and spends < 8:
                    if a.kind == "player":
                        if not self.pending:
                            break
                        fn = self.pending.popleft()
                        cost = fn()
                        a.energy -= max(1, cost)
                        self.after_player_action(cost)
                        acted = True
                    else:
                        cost = AI.monster_turn(self, a)
                        a.energy -= max(1, cost)
                        self.after_monster_action(a, cost)
                        acted = True
                    spends += 1
                if not self.player.alive or self.victory:
                    return
            if not acted:
                return
            if self.player.energy >= NORMAL_COST and not self.pending:
                return

    def after_player_action(self, cost):
        s = self.state
        s.turn += 1
        p = self.player
        if p.alive:
            p.calm += 1
        events, died = tick_status(p)
        self._status_events(events)
        if died:
            self.player_slain(self._status_death_cause(p))
            return
        if p.alive:
            PROG.maybe_regenerate(self)
        lv = self.current_level()
        lv.spawn_timer += cost
        self._maybe_wanderer()
        AI.tick_shoot_cooldowns(lv)
        lv.monsters = [m for m in lv.monsters if m.alive]
        self.refresh_dmap()
        self.refresh_vision()
        self.check_interrupts()

    def after_monster_action(self, m, cost):
        if not m.alive:
            return
        events, died = tick_status(m)
        for kind, tgt, val in events:
            if kind == "poison_tick":
                self.state.add_message(
                    f"{combat.sentence_name(self, tgt)} takes {val} poison "
                    f"damage.", "good")
                if died:
                    combat.kill(self, tgt, self.player)
            elif kind == "burn_tick":
                self.state.add_message(
                    f"{combat.sentence_name(self, tgt)} takes {val} fire "
                    f"damage.", "good")
                if died:
                    combat.kill(self, tgt, self.player)
            elif kind == "status_end":
                pass
        if died:
            return
        if m.flags.get("ai") == "boss":
            return

    def _status_events(self, events):
        for kind, tgt, val in events:
            if kind == "poison_tick" and tgt.kind == "player":
                self.state.add_message(f"You take {val} poison damage.", "bad")
            elif kind == "burn_tick" and tgt.kind == "player":
                self.state.add_message(f"You take {val} fire damage.", "bad")
            elif kind == "status_end" and tgt.kind == "player":
                words = {POISON: "The poison wears off.",
                         BURNING: "The flames gutter out.",
                         STUN: "You can move freely again.",
                         SLOW: "Your pace returns to normal.",
                         CONFUSED: "Your head clears."}
                if val in words:
                    self.state.add_message(words[val], "good")

    @staticmethod
    def _status_death_cause(p):
        if BURNING in p.statuses:
            return "burned alive"
        if POISON in p.statuses:
            return "killed by poison"
        return "killed by lingering wounds"

    def check_interrupts(self):
        p = self.player
        if self.pending and (
                self.pathing_threats()
                or p.hp >= p.max_hp
                or POISON in p.statuses
                or BURNING in p.statuses):
            was_resting = len(self.pending) > 1
            self.pending.clear()
            if was_resting:
                self.state.add_message("You stop.", "neutral")

    def start_rest(self):
        for _ in range(200):
            self.pending.append(self._wait_once)

    def _wait_once(self):
        return NORMAL_COST

    # ---------------- world pressure ----------------

    def _maybe_wanderer(self):
        lv = self.current_level()
        carrying = self.has_artefact()
        interval = max(60, 150 - self.state.depth * 8)
        if carrying:
            interval = int(interval * 0.6)
        cap = 4 if self.state.depth <= 3 else 6
        if lv.spawns_used >= cap:
            return
        if lv.spawn_timer < interval * NORMAL_COST:
            return
        lv.spawn_timer = 0
        table = C.spawn_table(self.state.depth)
        pos = self._spawn_pos()
        if pos is None:
            return
        key = self.rng.weighted(table)
        m = make_monster(key, pos[0], pos[1], self.alloc_id())
        m.flags["asleep"] = False
        lv.monsters.append(m)
        lv.spawns_used += 1
        self.state.add_message("Something moves in the dark nearby.", "info")

    def _spawn_pos(self):
        lv = self.current_level()
        px, py = self.player.x, self.player.y
        cands = []
        for y in range(lv.h):
            for x in range(lv.w):
                if lv.walkable(x, y) and lv.tile(x, y) == 1 \
                        and lv.monster_at(x, y) is None:
                    d = max(abs(x - px), abs(y - py))
                    if 9 <= d <= 30 and (x, y) not in self.visible:
                        cands.append((x, y))
        if not cands:
            return None
        return self.rng.choice(cands)

    def has_artefact(self):
        inv = getattr(self.player, "inventory", [])
        return any(i.category == CAT_ARTEFACT for i in inv)

    # ---------------- player actions ----------------

    def queue(self, fn):
        self.pending.append(fn)

    def act_move(self, dx, dy):
        p = self.player
        lv = self.current_level()
        nx, ny = p.x + dx, p.y + dy
        if not lv.in_bounds(nx, ny):
            return MOVE_COST_BUMP
        target = lv.monster_at(nx, ny)
        if target is not None and target.alive:
            def attack():
                combat.resolve_attack(self, p, target)
                return NORMAL_COST
            self._wrap(attack)
            return
        tile = lv.tile(nx, ny)
        if tile == 2:
            def open_door():
                lv.set_tile(nx, ny, 3)
                self._dmap_key = None
                self.refresh_dmap()
                self.state.add_message("You open the door.", "neutral")
                return NORMAL_COST
            return self._wrap(open_door)
        if tile not in {1, 3, 4, 5, 6, 7, 8, 9}:
            def bump():
                self.state.add_message("The rock wall blocks your way.",
                                       "neutral")
                return MOVE_COST_BUMP
            return self._wrap(bump)

        def move():
            p.x, p.y = nx, ny
            self._enter_tile(nx, ny)
            self.refresh_dmap()
            self.refresh_vision()
            self.state.tutorial.add("moved")
            return move_cost(lv.tile(nx, ny))
        return self._wrap(move)

    def _wrap(self, fn):
        """Queue an action and execute through the scheduler immediately."""
        self.queue(fn)
        return None

    def _enter_tile(self, x, y):
        lv = self.current_level()
        tile = lv.tile(x, y)
        if tile == 7 and BURNING in self.player.statuses:
            del self.player.statuses[BURNING]
            self.state.add_message("The water quenches the flames.", "good")
        if tile == 8 and self.rng.chance(15):
            PROG.apply_status_to_player(self.state, POISON, 6, stacks=2)
            self.state.add_message("Spores burst around you.", "bad")
        if tile == 9 and self.rng.chance(20):
            apply_status(self.player, BURNING, 5)
            self.state.add_message("The vent belches flame over you.", "bad")
        if (x, y) in lv.traps_hidden:
            lv.traps_hidden.discard((x, y))
            lv.traps_found.add((x, y))
            self._trigger_trap(x, y)
        for it in list(lv.items.get((x, y), [])):
            if it.category == CAT_SALVAGE:
                lv.items[(x, y)].remove(it)
                self.state.stats["salvage"] += it.value
                self.state.add_message(
                    f"You gather salvage worth {it.value}.", "good")
            elif it.category == CAT_AMMO:
                lv.items[(x, y)].remove(it)
                I.add_to_inventory(self.state, it)
                self.state.add_message(f"You pick up {I.display_name(self.state, it)}.",
                                       "neutral")
        if lv.items.get((x, y)) == []:
            del lv.items[(x, y)]
        if (x, y) == lv.up and self.state.depth == 1 and self.has_artefact():
            self._win()

    def _trigger_trap(self, x, y):
        roll = self.rng.below(100)
        if roll < 40:
            PROG.apply_status_to_player(self.state, POISON, 8, stacks=2)
            self.state.add_message("A dart snaps from the wall. You are "
                                   "poisoned (8 turns).", "bad")
        elif roll < 70:
            apply_status(self.player, CONFUSED, 8)
            self.state.add_message("Gas hisses up. You are confused "
                                   "(8 turns).", "bad")
        else:
            apply_status(self.player, STUN, 3)
            self.state.add_message("A weighted net slams down. You are "
                                   "stunned (3 turns).", "bad")
        self.player.calm = 0

    def act_wait(self):
        def wait():
            return NORMAL_COST
        return self._wrap(wait)

    def act_close(self, dx, dy):
        p = self.player
        lv = self.current_level()
        nx, ny = p.x + dx, p.y + dy

        def close():
            if lv.in_bounds(nx, ny) and lv.tile(nx, ny) == 3 \
                    and lv.monster_at(nx, ny) is None:
                lv.set_tile(nx, ny, 2)
                self._dmap_key = None
                self.refresh_dmap()
                self.state.add_message("You shut the door.", "neutral")
            else:
                self.state.add_message("There is no open door there.",
                                       "neutral")
            return NORMAL_COST
        return self._wrap(close)

    def act_pickup(self):
        lv = self.current_level()
        here = lv.items.get((self.player.x, self.player.y), [])

        def pick():
            if not here:
                self.state.add_message("There is nothing here to take.",
                                       "neutral")
                return NORMAL_COST
            it = here[0]
            here.remove(it)
            if it.category == CAT_ARTEFACT:
                I.add_to_inventory(self.state, it)
                self.state.add_message(f"You take {C.ARTEFACT_NAME}.", "info")
                for line in C.ARTEFACT_LORE:
                    self.state.add_message(line, "info")
                self.state.add_message("Carry it back to the surface exit "
                                       "on floor 1.", "info")
                return NORMAL_COST
            if I.add_to_inventory(self.state, it):
                self.state.add_message(
                    f"You take {I.display_name(self.state, it)}.", "neutral")
            else:
                here.insert(0, it)
                self.state.add_message("Your pack is full.", "bad")
            return NORMAL_COST
        return self._wrap(pick)

    def act_drop(self, item):
        def drop():
            if item in self.player.inventory:
                eq_slots = [s for s, v in self.player.equipment.items()
                            if v is item]
                if eq_slots and item.cursed:
                    self.state.add_message("It will not leave you.", "bad")
                    return NORMAL_COST
                self.player.inventory.remove(item)
                lv = self.current_level()
                lv.items.setdefault((self.player.x, self.player.y),
                                    []).append(item)
                self.state.add_message(f"You drop {item.key}.", "neutral")
            return NORMAL_COST
        return self._wrap(drop)

    def act_equip(self, item):
        def equip():
            slot = self._slot_for(item)
            if slot is None:
                self.state.add_message("You cannot use that.", "bad")
                return NORMAL_COST
            cur = self.player.equipment.get(slot)
            if cur is not None and cur.cursed:
                self.state.add_message("Your hands will not let go of what "
                                       "they hold.", "bad")
                return NORMAL_COST
            if item in self.player.inventory:
                self.player.inventory.remove(item)
            self.player.equipment[slot] = item
            if cur is not None:
                self.player.inventory.append(cur)
            if item.cursed:
                self.state.add_message("It grips you painfully. You cannot "
                                       "remove it.", "bad")
            else:
                self.state.add_message(
                    f"You ready {I.display_name(self.state, item)}.",
                    "neutral")
            if slot == "charm":
                self._apply_charm(slot)
            return NORMAL_COST
        return self._wrap(equip)

    def _apply_charm(self, slot):
        old = getattr(self, "_charm_prev", None)
        charm = self.player.equipment.get(slot)
        if old is not None and old is not charm:
            if old.key == "charm_vigour":
                delta = 5 if old.cursed else -5
                self.player.max_hp += delta
                self.player.hp = min(self.player.max_hp,
                                     max(1, self.player.hp + delta))
        self._charm_prev = charm
        if charm and charm.key == "charm_vigour":
            delta = -5 if charm.cursed else 5
            self.player.max_hp += delta
            self.player.hp = min(self.player.max_hp,
                                 max(1, self.player.hp + delta))

    def _slot_for(self, item):
        if item.category == I.CAT_WEAPON:
            return "weapon"
        if item.category == I.CAT_RANGED:
            return "weapon"
        if item.category == I.CAT_ARMOUR:
            return C.ARMOURS[item.key]["slot"]
        if item.category == I.CAT_CHARM:
            return "charm"
        return None

    def act_unequip(self, slot):
        def uneq():
            it = self.player.equipment.get(slot)
            if it is None:
                return NORMAL_COST
            if it.cursed:
                self.state.add_message("It will not leave you.", "bad")
                return NORMAL_COST
            self.player.equipment[slot] = None
            if slot == "charm":
                if it.key == "charm_vigour" and not it.cursed:
                    self.player.max_hp -= 5
                    self.player.hp = min(self.player.hp, self.player.max_hp)
                self._charm_prev = None
            if len(self.player.inventory) >= I.BACKPACK_CAP:
                lv = self.current_level()
                lv.items.setdefault((self.player.x, self.player.y),
                                    []).append(it)
                self.state.add_message("Your pack is full; you set it down.",
                                       "neutral")
            else:
                self.player.inventory.append(it)
            self.state.add_message(f"You put away your {I.base_name(it)}.",
                                   "neutral")
            return NORMAL_COST
        return self._wrap(uneq)

    def act_quaff(self, item):
        def quaff():
            if item not in self.player.inventory:
                return NORMAL_COST
            meta = C.POTIONS[item.key]
            known_first = I.identify_base(self.state, item)
            self.state.stats["potions_quaffed"] += 1
            if known_first:
                self.state.add_message(
                    f"This was {meta['name']}.", "info")
            self.player.inventory.remove(item)
            e = meta["effect"]
            if e == "heal":
                amount = combat.roll_dice(self.rng, meta["dice"]) + meta["flat"]
                self.player.hp = min(self.player.max_hp,
                                     self.player.hp + amount)
                self.state.add_message(f"It heals {amount}.", "good")
            elif e == "might":
                apply_status(self.player, "might", meta["turns"],
                             stacks=meta["amount"])
                self.state.add_message("Strength floods your arms.",
                                       "good")
            elif e == "haste":
                apply_status(self.player, "haste", meta["turns"])
                self.state.add_message("The world slows around you.", "good")
            elif e == "stone":
                apply_status(self.player, "stone", meta["turns"],
                             stacks=meta["amount"])
                self.state.add_message("Your skin hardens.", "good")
            elif e == "cure":
                self.player.statuses.pop(POISON, None)
                self.player.statuses.pop(BURNING, None)
                self.state.add_message("The sickness drains away.", "good")
            elif e == "confuse":
                apply_status(self.player, CONFUSED, meta["turns"])
                self.state.add_message("The room will not hold still.",
                                       "bad")
            elif e == "poison":
                PROG.apply_status_to_player(self.state, POISON,
                                            meta["turns"],
                                            stacks=meta["stacks"])
                self.state.add_message("It burns going down. You are "
                                       "poisoned.", "bad")
            return NORMAL_COST
        return self._wrap(quaff)

    def act_read(self, item):
        def read():
            if item not in self.player.inventory:
                return NORMAL_COST
            meta = C.SCROLLS[item.key]
            known_first = I.identify_base(self.state, item)
            self.state.stats["scrolls_read"] += 1
            if known_first:
                self.state.add_message(f"This was {meta['name']}.", "info")
            self.player.inventory.remove(item)
            e = meta["effect"]
            lv = self.current_level()
            if e == "magic_mapping":
                for i in range(lv.w * lv.h):
                    if lv.tiles[i] != 0:
                        lv.seen[i] = 1
                self.state.add_message("The layout of this floor settles "
                                       "into your mind.", "good")
            elif e == "teleport":
                pos = self._random_free_tile()
                self.player.x, self.player.y = pos
                self.state.add_message("The world lurches sideways.", "good")
                self.refresh_dmap()
                self.refresh_vision()
            elif e == "enchant_weapon":
                w = self.player.equipment.get("weapon")
                if w is None:
                    self.state.add_message("Nothing you wield improves.",
                                           "neutral")
                else:
                    w.enchant += 1
                    self.state.add_message(
                        f"Your {I.base_name(w)} sharpens ({w.enchant:+d}).",
                        "good")
            elif e == "enchant_armour":
                a = self.player.equipment.get("armour") or \
                    self.player.equipment.get("shield")
                if a is None:
                    self.state.add_message("Nothing you wear improves.",
                                           "neutral")
                else:
                    a.enchant += 1
                    self.state.add_message(
                        f"Your {I.base_name(a)} hardens ({a.enchant:+d}).",
                        "good")
            elif e == "remove_curse":
                n = 0
                pool = list(self.player.inventory) + \
                    [v for v in self.player.equipment.values() if v]
                for it in pool:
                    if it.cursed:
                        it.cursed = False
                        n += 1
                self.state.add_message(
                    "You feel lighter." if n else
                    "Nothing you carry was cursed.", "good")
            elif e == "fear":
                n = 0
                for m in self.enemies_visible():
                    m.flags["fear"] = 10
                    n += 1
                self.state.add_message(
                    f"{n} enemies flee from you." if n else
                    "The words echo unanswered.", "good")
            return NORMAL_COST
        return self._wrap(read)

    def _random_free_tile(self):
        lv = self.current_level()
        for _ in range(500):
            x, y = self.rng.below(lv.w), self.rng.below(lv.h)
            if lv.walkable(x, y) and lv.monster_at(x, y) is None \
                    and (x, y) != self.player.pos:
                return (x, y)
        return self.player.pos

    def act_zap(self, item, target):
        """target: monster Actor, (x,y) tile, or direction tuple for tunnels."""
        def zap():
            if item not in self.player.inventory:
                return NORMAL_COST
            if item.charges <= 0:
                self.state.add_message("It fizzles, spent.", "neutral")
                return NORMAL_COST
            item.charges -= 1
            known_first = I.identify_base(self.state, item)
            self.state.stats["wands_zapped"] += 1
            effect = C.WANDS[item.key]["effect"]
            if known_first:
                self.state.add_message(
                    f"This was {C.WANDS[item.key]['name']}.", "info")
            if effect == "tunnel":
                self._tunnel(item, target)
                return NORMAL_COST
            victim, hit_wall = self._ray_target(target)
            if victim is None:
                self.state.add_message("The beam strikes stone.", "neutral")
                return NORMAL_COST
            lv = self.current_level()
            if not bresenham_los(lv, self.player.x, self.player.y,
                                 victim.x, victim.y):
                self.state.add_message("No clear shot.", "neutral")
                return NORMAL_COST
            if effect == "ember_bolt":
                dmg = combat.roll_dice(self.rng, "2d6")
                self._bolt_damage(victim, dmg, "seared")
                if victim.alive and self.rng.chance(40):
                    apply_status(victim, BURNING, 5)
                    self.state.add_message(
                        f"{combat.name_of(self, victim)} catches fire.",
                        "good")
            elif effect == "frost_bolt":
                dmg = combat.roll_dice(self.rng, "2d4")
                self._bolt_damage(victim, dmg, "frozen")
                if victim.alive:
                    apply_status(victim, SLOW, 8)
                    self.state.add_message(
                        f"{combat.name_of(self, victim)} slows.", "good")
            return NORMAL_COST
        return self._wrap(zap)

    def _bolt_damage(self, victim, dmg, word):
        dmg -= victim.armour
        dmg = max(1, dmg)
        victim.hp -= dmg
        if victim.kind == "player":
            self.state.stats["damage_taken"] += dmg
            self.player.calm = 0
        else:
            self.state.stats["damage_dealt"] += dmg
        self.state.add_message(
            f"{combat.sentence_name(self, victim)} "
            f"{'are' if victim.kind == 'player' else 'is'} "
            f"{word} for {dmg}.",
            "bad" if victim.kind == "player" else "good")
        if victim.hp <= 0:
            if victim.kind == "player":
                self.player_slain(f"killed by a wand blast")
            else:
                combat.kill(self, victim, self.player)

    def _ray_target(self, target):
        if isinstance(target, Actor):
            return target, False
        lv = self.current_level()
        tx, ty = target
        for m in lv.monsters:
            if m.alive and m.pos == (tx, ty):
                return m, False
        return None, True

    def _tunnel(self, item, direction):
        lv = self.current_level()
        dx, dy = direction
        x, y = self.player.x, self.player.y
        for _ in range(6):
            x, y = x + dx, y + dy
            if not lv.in_bounds(x, y):
                break
            if lv.tile(x, y) == 0:
                lv.set_tile(x, y, 1)
                self._dmap_key = None
                self.state.add_message("Stone melts away.", "good")
                self.refresh_dmap()
                self.refresh_vision()
                return
        self.state.add_message("The ray fades against bare stone.",
                               "neutral")

    def act_fire(self, target):
        def fire():
            bow = self.player.equipment.get("weapon")
            if bow is None or bow.category != I.CAT_RANGED:
                self.state.add_message("You are not wielding a bow.", "bad")
                return NORMAL_COST
            if not I.consume_arrow(self.state):
                self.state.add_message("You have no arrows.", "bad")
                return NORMAL_COST
            lv = self.current_level()
            p = self.player
            victim = target
            if isinstance(victim, tuple):
                m = lv.monster_at(*victim)
                if m is None:
                    self.state.add_message("No target there.", "neutral")
                    return NORMAL_COST
                victim = m
            if not bresenham_los(lv, p.x, p.y, victim.x, victim.y):
                self.state.add_message("No clear shot.", "neutral")
                return NORMAL_COST
            combat.resolve_attack(self, p, victim, ranged=True,
                                  verb=("shoot", "shoot and miss"))
            return NORMAL_COST
        return self._wrap(fire)

    def act_descend(self):
        def down():
            lv = self.current_level()
            if (self.player.x, self.player.y) != lv.down:
                self.state.add_message("There are no stairs down here.",
                                       "neutral")
                return NORMAL_COST
            self._change_depth(self.state.depth + 1)
            return NORMAL_COST
        return self._wrap(down)

    def act_ascend(self):
        def up():
            lv = self.current_level()
            if (self.player.x, self.player.y) != lv.up:
                self.state.add_message("There are no stairs up here.",
                                       "neutral")
                return NORMAL_COST
            if self.state.depth == 1:
                if self.has_artefact():
                    self._win()
                else:
                    self.state.add_message(
                        "You cannot leave without the Heart.", "info")
                return NORMAL_COST
            self._change_depth(self.state.depth - 1)
            return NORMAL_COST
        return self._wrap(up)

    def _change_depth(self, depth):
        old = self.state.depth
        self.state.depth = depth
        self.state.stats["deepest"] = max(self.state.stats["deepest"], depth)
        self.ensure_level(depth)
        lv = self.current_level()
        anchor = lv.up if depth > old else (lv.down or lv.up)
        self.player.x, self.player.y = anchor
        self._dmap_key = None
        self._explore_goal = None
        self.pending.clear()
        self.refresh_dmap()
        self.refresh_vision()
        theme = C.THEMES[lv.theme]["name"]
        self.state.add_message(f"You are on floor {depth}: {theme}.", "info")
        if depth == 12:
            self.state.add_message("The water here is black and still.",
                                   "info")
        if self.autosave_fn:
            self.autosave_fn(self)

    def _win(self):
        self.state.stats["won"] = True
        self.victory = True
        self.state.add_message("You climb into daylight, the Tideglass "
                               "Heart beating in your hands.", "good")

    def player_slain(self, cause):
        self.death_cause = cause
        self.player.alive = False
        self.pending.clear()
        if self.delete_save_fn:
            try:
                self.delete_save_fn()
            except OSError:
                pass

    # ---------------- convenience ----------------

    def eff_sight(self):
        s = self.player.sight
        charm = self.player.equipment.get("charm")
        if charm and charm.key == "charm_lantern":
            s += -1 if charm.cursed else 1
        return max(3, s)

    def explore_next(self, ignore_ids=()):
        """Next step toward the nearest unexplored tile, or None.
        Commits to one frontier goal until reached/unreachable to avoid
        dithering between frontiers. Frontier recomputes only when the
        seen-map grows or the committed goal dies."""
        if [m for m in self.pathing_threats() if m.id not in ignore_ids]:
            return None
        lv = self.current_level()
        p = self.player

        def goal_ok(goal):
            return (goal is not None and lv.in_bounds(*goal)
                    and lv.seen[goal[1] * lv.w + goal[0]] != 1)

        seen_now = sum(lv.seen)
        cached = getattr(self, "_frontier", None)
        if cached:
            cgoal, ccount = cached
            if ccount != seen_now or not goal_ok(cgoal):
                self._frontier = None
                cached = None
        goal = getattr(self, "_explore_goal", None)
        if not goal_ok(goal):
            goal = pathing.nearest_unexplored(lv, lv.seen, p.pos)
            self._explore_goal = goal
            self._frontier = (goal, seen_now)
        elif not cached:
            self._frontier = (goal, seen_now)
        if goal is None:
            return None
        steps = pathing.path_to(lv, p.pos, goal)
        if not steps:
            self._explore_goal = None
            return None
        nxt = steps[0]
        if tuple(nxt) == tuple(p.pos):
            self._explore_goal = None
            return None
        return nxt

    def travel_next(self, dest, ignore_ids=()):
        """Next step toward dest, or None when arrived/unreachable/threat."""
        if [m for m in self.pathing_threats() if m.id not in ignore_ids]:
            return None
        if self.player.pos == tuple(dest):
            return None
        steps = pathing.path_to(self.current_level(), self.player.pos,
                                tuple(dest))
        return steps[0] if steps else None

    def score(self):
        st = self.state.stats
        s = st["salvage"] + st["kills"] * 2 + st["deepest"] * 15
        if st["won"]:
            s += 400
        s -= self.state.turn // 60
        return max(0, s)


def _eff_speed(a):
    from .engine import effective_speed
    return effective_speed(a)


def _level_seed(master, depth):
    from .rng import derive_seed
    return derive_seed(master, f"floor-{depth}")
