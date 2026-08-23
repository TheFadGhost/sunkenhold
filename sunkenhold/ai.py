"""Monster AI archetypes over a shared influence map.

charger : close and melee
kiter   : ranged; retreats when prey closes, shoots from afar
pack    : charger that flanks and alerts nearby packmates
ambusher: dormant until prey is very close, then relentless
gaze    : immobile; wounding stare with stun
brute   : slow heavy charger
coward  : flees below 35% HP, returns once with friends
boss    : summons thralls, telegraphed slam
"""
from . import combat, content as C
from .engine import POISON, STUN, NORMAL_COST, move_cost
from .fov import bresenham_los
from .pathing import (step_toward, step_away, flank_target)
from .mapgen import make_monster


def cheb(ax, ay, bx, by):
    return max(abs(ax - bx), abs(ay - by))


def can_see_player(game, m):
    p = game.player
    d = cheb(m.x, m.y, p.x, p.y)
    if d > m.sight:
        return False
    return bresenham_los(game.current_level(), m.x, m.y, p.x, p.y)


def wake(game, m, propagate=False):
    if not m.flags.get("asleep", False):
        return
    m.flags["asleep"] = False
    if propagate and m.species == "hound":
        lv = game.current_level()
        for other in lv.monsters:
            if other is not m and other.alive and other.species == "hound" \
                    and cheb(other.x, other.y, m.x, m.y) <= 12:
                other.flags["asleep"] = False


def _melee_or_step(game, m, target_pos, occupied):
    lv = game.current_level()
    p = game.player
    if cheb(m.x, m.y, p.x, p.y) <= 1:
        combat.resolve_attack(game, m, p)
        return move_cost(lv.tile(m.x, m.y))
    nxt = step_toward(lv, m.x, m.y, game.dmap, occupied)
    if nxt is None:
        return _wander(game, m)
    return _move_monster(game, m, nxt)


def _move_monster(game, m, dest):
    lv = game.current_level()
    nx, ny = dest
    if not lv.walkable(nx, ny) or (nx, ny) == (game.player.x, game.player.y):
        return NORMAL_COST
    if lv.tile(nx, ny) == 2:
        lv.set_tile(nx, ny, 3)
        if (m.x, m.y) in game.visible:
            game.add_message("Something forces a door.", "neutral")
        return NORMAL_COST
    blocker = lv.monster_at(nx, ny)
    if blocker is not None:
        return NORMAL_COST
    cost = move_cost(lv.tile(nx, ny))
    m.x, m.y = nx, ny
    return cost


def _wander(game, m):
    lv = game.current_level()
    opts = [(m.x + dx, m.y + dy) for dx, dy in
            ((0, -1), (1, 0), (0, 1), (-1, 0))]
    opts = [o for o in opts if lv.walkable(*o) and lv.monster_at(*o) is None]
    if opts:
        return _move_monster(game, m, game.rng.choice(opts))
    return NORMAL_COST


def _confused_act(game, m):
    roll = game.rng.below(100)
    if roll < 50:
        return _wander(game, m)
    game.add_message(f"{combat.sentence_name(game, m)} staggers.",
                     "neutral")
    return NORMAL_COST


def monster_turn(game, m):
    """One monster action. Returns energy cost."""
    if not m.alive:
        return 0

    if m.flags.get("fear", 0) > 0:
        m.flags["fear"] -= 1
        lv = game.current_level()
        nxt = step_away(lv, m.x, m.y, game.dmap,
                        {(game.player.x, game.player.y)})
        if nxt:
            return _move_monster(game, m, nxt)
        return NORMAL_COST

    if STUN in m.statuses:
        return NORMAL_COST

    if "confused" in m.statuses:
        return _confused_act(game, m)

    if m.flags.get("asleep", False):
        p = game.player
        d = cheb(m.x, m.y, p.x, p.y)
        if d <= 1 or (d <= m.sight and can_see_player(game, m)):
            wake(game, m, propagate=(m.flags.get("ai") == "pack"))
            game.add_message(f"{combat.sentence_name(game, m)} notices you.",
                             "bad")
        else:
            return NORMAL_COST

    if not can_see_player(game, m):
        return _wander(game, m)

    ai = m.flags.get("ai")
    occupied = {o.pos for o in game.current_level().monsters
                if o.alive and o is not m}

    if ai == "kiter":
        return _kiter(game, m, occupied)
    if ai == "pack":
        return _pack(game, m, occupied)
    if ai == "ambusher":
        pass
    if ai == "gaze":
        return _gaze(game, m)
    if ai == "coward":
        return _coward(game, m, occupied)
    if ai == "boss":
        return _boss(game, m, occupied)
    return _melee_or_step(game, m, None, occupied)


def _try_ranged(game, m):
    s = C.SPECIES[m.species]
    if s.ranged_dmg is None or s.range_ <= 0:
        return False
    p = game.player
    if cheb(m.x, m.y, p.x, p.y) > s.range_:
        return False
    if m.flags.get("shoot_cd", 0) > 0:
        return False
    if not bresenham_los(game.current_level(), m.x, m.y, p.x, p.y):
        return False
    m.flags["shoot_cd"] = s.cooldown
    backup_dmg = m.dmg
    m.dmg = s.ranged_dmg
    verb = ("stares at", "gazes past") if s.ai == "gaze" else \
        (("hurls embers at", "hurls embers wide of")
         if m.species == "cinder" else ("shoots", "shoots and misses"))
    combat.resolve_attack(game, m, p, ranged=True, verb=verb)
    m.dmg = backup_dmg
    return True


def _kiter(game, m, occupied):
    lv = game.current_level()
    p = game.player
    d = cheb(m.x, m.y, p.x, p.y)
    s = C.SPECIES[m.species]
    if d > s.range_ + 3:
        m.flags["bored"] = m.flags.get("bored", 0) + 1
        if m.flags["bored"] >= 6:
            m.flags["asleep"] = True
            m.flags["bored"] = 0
            return NORMAL_COST
    else:
        m.flags["bored"] = 0
    shot = _try_ranged(game, m)
    if shot:
        return move_cost(lv.tile(m.x, m.y))
    if d < 3:
        # Imperfect retreat: openings exist for a charging player.
        if m.flags.get("shoot_cd", 0) > 0 or game.rng.chance(50):
            nxt = step_away(lv, m.x, m.y, game.dmap, occupied)
            if nxt:
                return _move_monster(game, m, nxt)
    elif d > s.range_:
        nxt = step_toward(lv, m.x, m.y, game.dmap, occupied)
        if nxt:
            return _move_monster(game, m, nxt)
    return _melee_or_step(game, m, None, occupied)


def _pack(game, m, occupied):
    lv = game.current_level()
    p = game.player
    if cheb(m.x, m.y, p.x, p.y) <= 1:
        combat.resolve_attack(game, m, p)
        return move_cost(lv.tile(m.x, m.y))
    tgt = flank_target(lv, m, p, game.dmap, occupied | {(p.x, p.y)})
    if tgt is None:
        tgt = step_toward(lv, m.x, m.y, game.dmap, occupied)
    if tgt is None:
        return _wander(game, m)
    return _move_monster(game, m, tgt)


def _gaze(game, m):
    lv = game.current_level()
    if _try_ranged(game, m):
        return move_cost(lv.tile(m.x, m.y))
    return NORMAL_COST


def _coward(game, m, occupied):
    lv = game.current_level()
    p = game.player
    low = m.hp * 100 < m.max_hp * 35
    if low and not m.flags.get("called_friends"):
        m.flags["called_friends"] = True
        m.flags["fleeing"] = 10
    if m.flags.get("fleeing", 0) > 0:
        m.flags["fleeing"] -= 1
        if m.flags["fleeing"] == 0:
            n = 0
            for _ in range(6):
                dx = game.rng.range(-2, 2)
                dy = game.rng.range(-2, 2)
                nx, ny = m.x + dx, m.y + dy
                if lv.walkable(nx, ny) and lv.monster_at(nx, ny) is None \
                        and (nx, ny) != (p.x, p.y):
                    ally = make_monster("gnawling", nx, ny,
                                        game.alloc_id())
                    ally.flags["asleep"] = False
                    lv.monsters.append(ally)
                    n += 1
                if n >= 3:
                    break
            if n:
                game.add_message(
                    f"The skitterking returns with {n} gnawlings.", "bad")
            return NORMAL_COST
        nxt = step_away(lv, m.x, m.y, game.dmap,
                        occupied | {(p.x, p.y)})
        if nxt:
            return _move_monster(game, m, nxt)
        return NORMAL_COST
    return _melee_or_step(game, m, None, occupied)


def _boss(game, m, occupied):
    lv = game.current_level()
    p = game.player

    if m.flags.get("slam_windup"):
        m.flags["slam_windup"] = False
        m.flags["next_slam"] = 12
        game.add_message("Black water crashes down.", "bad")
        if cheb(m.x, m.y, p.x, p.y) <= 1:
            dmg = max(1, combat.roll_dice(game.rng, "2d6") // 2 -
                      combat.player_absorb(game))
            p.hp -= dmg
            p.calm = 0
            game.stats["damage_taken"] += dmg
            game.add_message(f"You are smashed for {dmg}.", "bad")
            if game.rng.chance(30):
                from .engine import apply_status
                apply_status(p, STUN, 2)
                game.add_message("You are stunned (2 turns).", "bad")
            if p.hp <= 0:
                game.player_slain("crushed by the Drowned Warden")
        for o in lv.monsters:
            if o.alive and o.species == "thrall" and \
                    cheb(o.x, o.y, m.x, m.y) <= 1:
                o.hp -= combat.roll_dice(game.rng, "1d6")
                if o.hp <= 0:
                    o.alive = False
        return NORMAL_COST

    m.flags["next_slam"] = m.flags.get("next_slam", 10) - 1
    if m.flags["next_slam"] <= 0 and cheb(m.x, m.y, p.x, p.y) <= 2:
        m.flags["slam_windup"] = True
        game.add_message(C.BOSS_TELEGRAPH, "info")
        return NORMAL_COST

    cd = m.flags.get("summon_cd", 12)
    if cd <= 0:
        alive_thralls = sum(1 for o in lv.monsters
                            if o.alive and o.species == "thrall")
        spawned = 0
        if alive_thralls < 4:
            for _ in range(8):
                dx, dy = game.rng.range(-3, 3), game.rng.range(-3, 3)
                nx, ny = m.x + dx, m.y + dy
                if lv.walkable(nx, ny) and lv.monster_at(nx, ny) is None \
                        and (nx, ny) != (p.x, p.y):
                    t = make_monster("thrall", nx, ny, game.alloc_id())
                    t.flags["asleep"] = False
                    lv.monsters.append(t)
                    spawned += 1
                if spawned >= 2:
                    break
        m.flags["summon_cd"] = 16
        if spawned:
            game.add_message(
                f"The Drowned Warden calls {spawned} "
                f"{'thrall' if spawned == 1 else 'thralls'} from the water.",
                "bad")
            return NORMAL_COST
    else:
        m.flags["summon_cd"] = cd - 1

    return _melee_or_step(game, m, None, occupied)


def tick_shoot_cooldowns(level):
    for m in level.monsters:
        if m.alive and m.flags.get("shoot_cd", 0) > 0:
            m.flags["shoot_cd"] -= 1

