"""Combat resolution: stated formulas shared by every attacker and defender.

Melee/ranged to-hit : hit% = clamp(75 + 5*(accuracy - evasion), 20, 95)
Critical            : chance% = 5 + crit_bonus; doubles rolled damage
Damage              = dice + dmg_bonus + weapon_enchant - absorption, min 1
Absorption          = defender armour + worn armour/shield + temporary effects
"""
import re

from . import content as C
from .engine import POISON, BURNING, STUN, apply_status
from . import items as I


def parse_dice(spec):
    m = re.fullmatch(r"(\d+)d(\d+)([+-]\d+)?", spec)
    if not m:
        raise ValueError(f"bad dice spec: {spec}")
    return int(m.group(1)), int(m.group(2)), int(m.group(3) or 0)


def roll_dice(rng, spec):
    n, sides, mod = parse_dice(spec)
    total = mod
    for _ in range(n):
        total += rng.range(1, sides)
    return total


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def hit_chance(att_acc, def_eva):
    return clamp(75 + 5 * (att_acc - def_eva), 20, 95)


def player_weapon(game):
    w = game.player.equipment.get("weapon")
    if w and w.category == I.CAT_WEAPON:
        spec = C.WEAPONS[w.key]
        return {"dmg": spec["dmg"], "acc": spec["acc_mod"] + w.enchant,
                "name": spec["name"], "enchant": w.enchant}
    if w and w.category == I.CAT_RANGED:
        spec = C.RANGED[w.key]
        return {"dmg": spec["dmg"], "acc": spec["acc_mod"] + w.enchant,
                "name": spec["name"], "enchant": w.enchant}
    return {"dmg": "1d3", "acc": 0, "name": "bare hands", "enchant": 0}


def player_absorb(game):
    total = game.player.armour
    for slot in ("armour", "shield"):
        it = game.player.equipment.get(slot)
        if it and it.category == I.CAT_ARMOUR:
            a = C.ARMOURS[it.key]
            total += a["absorb"] + it.enchant
    total += game.player.statuses.get("stone", {}).get("stacks", 0)
    return max(0, total)


def player_evasion(game):
    eva = game.player.eva
    for slot in ("armour", "shield"):
        it = game.player.equipment.get(slot)
        if it and it.category == I.CAT_ARMOUR:
            eva += C.ARMOURS[it.key]["eva_mod"]
    return eva


def player_accuracy(game):
    return game.player.acc + player_weapon(game)["acc"]


def player_crit_chance(game):
    c = 5 + game.player.crit_bonus
    charm = game.player.equipment.get("charm")
    if charm and charm.key == "charm_luck" and not charm.cursed:
        c += 10
    return c


def player_damage_spec(game):
    w = player_weapon(game)
    bonus = game.player.dmg_bonus + w["enchant"]
    bonus += game.player.statuses.get("might", {}).get("stacks", 0)
    if bonus >= 0:
        return f"{w['dmg']}+{bonus}"
    return f"{w['dmg']}{bonus}"


def _absorb_of(defender, game=None):
    if defender.kind == "player":
        return player_absorb(game)
    return defender.armour


def _eva_of(defender, game=None):
    if defender.kind == "player":
        return player_evasion(game)
    return defender.eva


def resolve_attack(game, attacker, defender, ranged=False, verb=None,
                   silent_miss=False):
    """One attack attempt. Logs everything honestly. Returns True on hit.
    verb: (hit_verb, miss_verb) tuple or string for both."""
    rng = game.rng
    if attacker.kind == "player":
        att_acc = player_accuracy(game)
        spec = player_damage_spec(game)
        crit_c = player_crit_chance(game)
    else:
        att_acc = attacker.acc
        spec = f"{attacker.dmg}+{attacker.dmg_bonus}"
        crit_c = 5 + attacker.crit_bonus

    def_eva = _eva_of(defender, game)
    hc = hit_chance(att_acc, def_eva)

    dname = name_of(game, defender)

    if verb is None:
        verb = ("shoots", "shoots and misses") if ranged else ("hits", "misses")
    elif isinstance(verb, str):
        verb = (verb, "misses")
    hit_verb, miss_verb = verb

    if rng.below(100) >= hc:
        game.add_message(
            f"{sentence_name(game, attacker)} {_conj(attacker, miss_verb)} "
            f"{dname}.",
            "neutral")
        return False

    dmg = roll_dice(rng, spec)
    crit = rng.below(100) < crit_c
    if crit:
        dmg *= 2
    dmg -= _absorb_of(defender, game)
    dmg = max(1, dmg)

    if attacker.kind == "player":
        game.stats["damage_dealt"] += dmg
    if defender.kind == "player":
        game.stats["damage_taken"] += dmg
        defender.calm = 0

    if crit:
        game.add_message(
            f"{sentence_name(game, attacker)} critically "
            f"{_conj(attacker, hit_verb)} {dname} for {dmg}.",
            "good" if attacker.kind == "player" else "bad")
    else:
        game.add_message(
            f"{sentence_name(game, attacker)} {_conj(attacker, hit_verb)} "
            f"{dname} for {dmg}.",
            "good" if attacker.kind == "player" else "bad")

    defender.hp -= dmg
    if defender.hp <= 0:
        if defender.kind == "player":
            game.player_slain(f"slain by {name_of(game, attacker)}")
        else:
            kill(game, defender, attacker)
        return True

    src_species = C.SPECIES.get(attacker.species) if attacker.species else None
    if src_species and src_species.on_hit_status:
        if rng.chance(src_species.status_chance):
            st = src_species.on_hit_status
            turns = 5 if st == POISON else (4 if st == BURNING else 3)
            apply_status(defender, st, turns,
                         stacks=1 if st == POISON else 1)
            who = "You are" if defender.kind == "player" else f"The {dname} is"
            game.add_message(status_apply_text(who, st, turns),
                             "bad" if defender.kind == "player" else "good")
    return True


def status_apply_text(who, status, turns):
    words = {POISON: "poisoned", BURNING: "on fire", STUN: "stunned",
             "slow": "slowed", "confused": "confused"}
    return f"{who} {words.get(status, status)} ({turns} turns)."


def _conj(actor, verb):
    """Verbs are written for third person ('hits'); the player speaks in
    second person ('hit')."""
    if actor.kind == "player":
        table = {"hits": "hit", "misses": "miss", "shoots": "shoot",
                 "critically hits": "critically hit",
                 "shoot and miss": "shoot and miss",
                 "hit": "hit", "miss": "miss"}
        return table.get(verb, verb)
    return verb


def name_of(game, actor):
    if actor.kind == "player":
        return "you"
    s = C.SPECIES.get(actor.species)
    return f"the {s.name}" if s else "something"


def sentence_name(game, actor):
    """Capitalised subject for sentence start."""
    if actor.kind == "player":
        return "You"
    s = C.SPECIES.get(actor.species)
    return f"The {s.name}" if s else "Something"


def kill(game, victim, killer):
    victim.alive = False
    if victim.kind == "monster":
        s = C.SPECIES.get(victim.species)
        game.add_message(f"{sentence_name(game, victim)} dies.", "good")
        from .progression import update_memory
        update_memory(getattr(game, "state", game), victim.species, "killed")
        if killer and killer.kind == "player":
            game.stats["kills"] += 1
            gain_xp(game, s.xp if s else 5)
        if game.rng.chance(25) and s and s.key != "warden":
            from .items import Item, CAT_SALVAGE
            lv = game.current_level()
            pos = (victim.x, victim.y)
            lv.items.setdefault(pos, []).append(
                Item("salvage", CAT_SALVAGE,
                     value=game.rng.range(4, 10 + game.depth * 2)))
    # player death is finalised by the game loop, which owns cause tracking


def gain_xp(game, amount):
    p = game.player
    p.xp = getattr(p, "xp", 0) + amount
    while p.xp >= xp_needed(p.level):
        p.xp -= xp_needed(p.level)
        p.level += 1
        p.flags["pending_levelups"] = p.flags.get("pending_levelups", 0) + 1


def xp_needed(level):
    return int(round(18 * (level ** 1.45)))
