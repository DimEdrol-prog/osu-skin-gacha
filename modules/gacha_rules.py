"""osu! Skin Gacha: gacha_rules."""
from __future__ import annotations
import requests
from modules.gacha_config import RANKS, COMBO, TOP

def pp_thresholds(total, settings=None):
    if settings and settings.get("custom_rewards"):
        return {r:float(settings["goal_Medium_"+r]) for r in RANKS}
    ss = int(total * 0.063) - 107
    return {rank: max(0, ss - i * 50) for i, rank in enumerate(RANKS)}


def stars_threshold(total, settings=None):
    if settings and settings.get("custom_rewards"): return float(settings["goal_stars"])
    return total / 4000 + 3


def special_chance(settings):
    return int(settings.get('rofl_chance',5)) if settings.get('custom_special_chance',False) else 5


def special_gain(before, after):
    # Avoid losing an exact 0.1 gain to binary floating point rounding.
    from decimal import Decimal
    return Decimal(str(after))-Decimal(str(before)) >= Decimal('0.1')


def score_key(score):
    # Recent v1 не содержит score_id: один отпечаток для recent, best и get_scores.
    fields = ("beatmap_id", "date", "score", "maxcombo", "enabled_mods", "count300", "count100", "count50", "countmiss")
    return tuple(str(score.get(k, "0") or "0") for k in fields)


def accuracy(score):
    a, b, c, d = (int(score.get(k, 0) or 0) for k in ("count300", "count100", "count50", "countmiss"))
    return (300*a + 100*b + 50*c) / (300*(a+b+c+d)) * 100 if a+b+c+d else 0


def mods_string(bits):
    bits = int(bits or 0)
    pairs = ((1,"NF"),(2,"EZ"),(4,"TD"),(8,"HD"),(16,"HR"),(32,"SD"),(64,"DT"),(128,"RX"),
             (256,"HT"),(512,"NC"),(1024,"FL"),(2048,"AT"),(4096,"SO"),(8192,"AP"),(16384,"PF"),
             (32768,"4K"),(65536,"5K"),(131072,"6K"),(262144,"7K"),(524288,"8K"),(1048576,"FI"),
             (2097152,"RD"),(4194304,"CN"),(8388608,"TP"),(16777216,"9K"),(33554432,"CO"),
             (67108864,"1K"),(134217728,"3K"),(268435456,"2K"),(536870912,"V2"),(1073741824,"MR"))
    return "+".join(name for bit, name in pairs if bits & bit and not
        (name == "DT" and bits & 512 or name == "SD" and bits & 16384)) or "NM"


def reward_for(mode, total, score, stars, position=None, settings=None):
    if score.get("rank") == "F":
        return "F"
    if mode == "Hard":
        return next((r for r in RANKS if position and position <= rank_thresholds("Hard",settings)[r]), "F")
    if mode == "Fun":
        return next((r for r in RANKS if stars >= stars_threshold(total,settings) and int(score.get("maxcombo", 0)) >= rank_thresholds("Fun",settings)[r]), "F")
    pp = score.get("pp")
    return next((r for r, limit in pp_thresholds(total,settings).items() if pp is not None and float(pp) >= limit), "F")


def dt_reward(mode,total,score,stars,position=None,settings=None):
    if score.get('rank')=='F' or not int(score.get('enabled_mods') or 0) & (64|512):
        return False
    return (mode == 'Hard' and position is not None and position <= 50 or
            mode == 'Fun' and int(score.get('maxcombo') or 0) >= 750 and stars >= stars_threshold(total,settings))


def score_url(score):
    # score_id API v1 — legacy ID, поэтому обязателен маршрут с режимом.
    if score.get('rank') == 'F' or score.get('provider') == 'offline':
        return None
    ident = str(score.get('score_id') or '')
    if score.get('provider') == 'gatari':
        return None
    if str(score.get('modern_id') or '').isdigit():
        return 'https://osu.ppy.sh/scores/'+str(score['modern_id'])
    return f'https://osu.ppy.sh/scores/osu/{ident}' if ident.isdigit() and int(ident) > 0 else None


def resolve_score_url(score,ignore_proxy=False):
    legacy = score_url(score)
    if not legacy:
        return None
    if score.get('provider') == 'gatari':
        return legacy
    # Публичная JSON-версия страницы возвращает современный ID. Ключ API не передаётся.
    with requests.Session() as session:
        session.trust_env = not ignore_proxy
        try:
            response = session.get(legacy,headers={'Accept':'application/json'},timeout=(5,12))
            response.raise_for_status()
            ident = str(response.json().get('id') or '')
            if ident.isdigit() and int(ident) > 0:
                return f'https://osu.ppy.sh/scores/{ident}'
        except (requests.RequestException,ValueError,AttributeError):
            pass
    return legacy



def difficulty_key(score):
    """Stable difficulty identity; mods and attempt date must not reset rewards."""
    ident = str(score.get('beatmap_id') or '')
    if ident and ident != '0':
        return ident
    return score.get('beatmap_md5') or score.get('file_md5') or None


def rank_thresholds(mode,settings=None):
    if settings and settings.get('custom_rewards'):
        return {r:float(settings['goal_'+mode+'_'+r]) for r in RANKS}
    return TOP if mode=='Hard' else COMBO


def rank_level(rank):
    return len(RANKS)-RANKS.index(rank) if rank in RANKS else 0


def claimed_ranks(records):
    claimed={}
    for r in records:
        if r['score'].get('rank')=='F' or not r.get('awarded',r.get('reward','F')!='F'):continue
        key=difficulty_key(r['score'])
        if key:claimed[key]=max(claimed.get(key,0),rank_level(r.get('reward')))
    return claimed


def reward_upgrade(score, rank, claimed):
    key=difficulty_key(score)
    return bool(key and score.get('rank')!='F' and rank_level(rank)>claimed.get(key,0))
