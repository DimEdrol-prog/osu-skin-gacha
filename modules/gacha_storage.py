"""osu! Skin Gacha: gacha_storage."""
from __future__ import annotations
from datetime import datetime
import json
import math
import os
from pathlib import Path
import re
import tempfile
from modules.gacha_config import BASE, THEMES, COLORS, DEFAULTS

def atomic_json(path, data):
    """Старый JSON остаётся целым при обрыве записи."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=path.name, suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(data, stream, ensure_ascii=False, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


class SettingsStore:
    def __init__(self):
        self.paths = [BASE / "settings.json", Path(os.getenv("APPDATA", str(Path.home()))) / "osu_skin_gacha/settings.json"]

    def load(self):
        result = DEFAULTS.copy()
        existing = sorted((p for p in self.paths if p.exists()), key=lambda p: p.stat().st_mtime, reverse=True)
        for path in existing:
            try:
                data = json.loads(path.read_text(encoding="utf-8-sig"))
                if isinstance(data, dict):
                    result.update(data)
                    if 'setup_complete' not in data:
                        result['setup_complete'] = bool(data.get('user_id') or data.get('offline'))
                    break
            except (OSError, ValueError):
                continue
        for key, low, high in (("interval", 1, 300), ("rofl_chance", 0, 100), ("rofl_pp", 0, 100000)):
            try:
                value = float(result[key])
                result[key] = max(low, min(high, value)) if math.isfinite(value) else DEFAULTS[key]
            except (TypeError, ValueError):
                result[key] = DEFAULTS[key]
        for key, allowed in (("theme", THEMES), ("color", COLORS), ("language", ("Русский", "English")), ("difficulty", ("Hard", "Medium", "Fun"))):
            if result[key] not in allowed:
                result[key] = DEFAULTS[key]
        for key, values in (('skin_source',('folder','zip','drive')),('slot',('1','2','3')),('server',('bancho','gatari'))):
            if result[key] not in values:
                result[key] = DEFAULTS[key]
        if result.get('ui_scale') not in ('90%','100%','110%','125%'): result['ui_scale']='100%'
        result['dt_bonus'] = True
        result['interval'] = int(result['interval'])
        result['rofl_chance'] = int(result['rofl_chance'])
        result['rofl_pp'] = 0.1
        result['ui_motion'] = True
        result['log_mode'] = True
        ids = result.get('server_user_ids',{})
        result['server_user_ids'] = dict(ids) if isinstance(ids,dict) else {}
        result['server_user_ids'][result['server']] = str(result.get('user_id',''))
        return result


    def save(self, data):
        for path in self.paths:
            try:
                atomic_json(path, data)
                return
            except OSError:
                continue
        raise OSError("Не удалось сохранить настройки / Cannot save settings")


class HistoryStore:
    """Отдельный атомарный JSON на сессию, без API-ключей и путей профиля."""
    def __init__(self):
        self.paths = [BASE/'sessions', Path(os.getenv('APPDATA',str(Path.home())))/'osu_skin_gacha/sessions']

    def save(self, session):
        ident = session['id']
        if not re.fullmatch(r'[0-9a-zA-Z_-]+', ident):
            raise ValueError('Invalid session ID')
        for folder in self.paths:
            try:
                atomic_json(folder/(ident+'.json'),session)
                return
            except OSError:
                continue
        raise OSError('Не удалось сохранить историю / Cannot save history')

    def load(self):
        sessions = {}
        for folder in self.paths:
            try:
                paths = list(folder.glob('*.json'))
            except OSError:
                continue
            for path in paths:
                try:
                    data = json.loads(path.read_text(encoding='utf-8-sig'))
                    if not isinstance(data,dict) or not isinstance(data.get('records'),list):
                        continue
                    datetime.fromisoformat(data['started_at'])
                    if not isinstance(data.get('id'),str) or not isinstance(data.get('user_id'),str):
                        continue
                    data['records'] = [r for r in data['records'] if isinstance(r,dict) and isinstance(r.get('score'),dict)
                                       and isinstance(r.get('map'),dict) and 'reward' in r]
                    modified = path.stat().st_mtime
                    if data['id'] not in sessions or modified > sessions[data['id']][0]:
                        sessions[data['id']] = (modified,data)
                except (OSError,ValueError,KeyError,TypeError):
                    continue
        return {key:value for key,(_,value) in sessions.items()}

