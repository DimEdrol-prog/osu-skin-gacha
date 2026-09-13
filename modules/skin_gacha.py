"""Entry point for osu! Skin Gacha."""
from modules.gacha_config import BASE, DEV_API_KEY_HASH, RANKS, COMBO, TOP, RANK_COLORS, _PALETTES, THEMES, COLORS, DEFAULTS, TEXT, tr, blend
from modules.gacha_storage import atomic_json, SettingsStore, HistoryStore
from modules.gacha_rules import pp_thresholds, stars_threshold, score_key, accuracy, mods_string, reward_for, dt_reward, score_url, resolve_score_url
from modules.gacha_skins import skin_manifest, read_skin_ini, gameplay_file, mix_skin, SkinLibrary, Sandbox
from modules.gacha_api import API, Covers
from modules.gacha_widgets import FastScrollableFrame, FastTextbox, Particles, bind_api_paste, apply_window_icon, IconWindow
from modules.gacha_settings import SETTING_HELP, SettingsWindow
from modules.gacha_app import SkinGachaApp
