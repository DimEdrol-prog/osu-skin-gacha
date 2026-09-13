"""osu! Skin Gacha: gacha_api."""
from __future__ import annotations
import csv
import io
from pathlib import Path
import re
import time
import threading
import requests
from PIL import Image, ImageOps
from modules.gacha_sources import LocalMaps, session_for
from modules.gacha_rules import score_key, score_url

class API:
    _request_lock = threading.Lock()
    _last_request = 0.0
    def __init__(self, settings):
        self.key, self.user = settings["api_key"], settings["user_id"]
        self.session = requests.Session()
        self.session.trust_env = not settings.get('ignore_proxy',False)
        self.language = settings.get('language','Русский')
        self.session.headers["User-Agent"] = "osu-Skin-Gacha/2.0"
        self.maps = {}
        self.local_maps = LocalMaps(settings['osu_path'])
        self.last_request = 0.0

    def get(self, endpoint, **params):
        # Ограничиваем всплески при пачке новых скоров. Только рабочий поток.
        with API._request_lock:
            delay = 1.05 - (time.monotonic() - API._last_request)
            if delay > 0:
                time.sleep(delay)
            API._last_request = self.last_request = time.monotonic()
        try:
            response = self.session.get("https://osu.ppy.sh/api/" + endpoint,
                params=dict(k=self.key, m=0, **params), timeout=(12, 25))
            response.raise_for_status()
            data = response.json()
            if not isinstance(data, list):
                raise ValueError("Invalid API response")
            return data
        except requests.exceptions.ProxyError:
            message = ('Ошибка HTTP-прокси. Попробуйте галочку «Не использовать системный HTTP-прокси» для VPN/TUN.',
                       'HTTP proxy failed. Try Ignore system HTTP proxy for VPN/TUN.')
        except requests.exceptions.SSLError:
            message = ('Ошибка TLS-сертификата. Проверьте время Windows и HTTPS-фильтрацию VPN/антивируса.',
                       'TLS certificate error. Check Windows time and VPN/antivirus HTTPS filtering.')
        except requests.exceptions.Timeout:
            message = ('osu! API не ответил вовремя. Проверьте соединение или другой сервер VPN.',
                       'osu! API timed out. Check the connection or another VPN server.')
        except requests.exceptions.HTTPError as error:
            code = error.response.status_code if error.response is not None else '?'
            message = (f'osu! API: HTTP {code}. 401/403: ключ или блокировка IP/VPN; 429: лимит запросов.',
                       f'osu! API: HTTP {code}. 401/403: key or IP/VPN block; 429: rate limit.')
        except requests.exceptions.ConnectionError:
            message = ('Нет соединения с osu! API (DNS/маршрут/VPN). Попробуйте другой сервер VPN.',
                       'Cannot connect to osu! API (DNS/routing/VPN). Try another VPN server.')
        except (requests.RequestException,ValueError):
            message = ('osu! API вернул неверный ответ; возможна страница проверки VPN/IP.',
                       'Invalid osu! API response; possibly a VPN/IP verification page.')
        # URL исключения содержит API-ключ — показываем только безопасную диагностику.
        raise RuntimeError(message[self.language == 'English']) from None

    def snapshot(self):
        user = self.get("get_user", u=self.user, type="id")
        if not user:
            raise RuntimeError("Профиль не найден / Profile not found")
        best = self.get("get_user_best", u=self.user, type="id", limit=100)
        recent = self.get("get_user_recent", u=self.user, type="id", limit=50)
        return user[0], best, recent

    def beatmap(self, beatmap_id, mods):
        difficulty_mods = mods & (2 | 16 | 64 | 256)
        if mods & 512:
            difficulty_mods |= 64
        key = (beatmap_id, difficulty_mods)
        if key not in self.maps:
            rows = self.get("get_beatmaps", b=beatmap_id, mods=difficulty_mods)
            if not rows:
                raise RuntimeError("Карта недоступна / Beatmap unavailable")
            self.maps[key] = rows[0]
        return self.maps[key]

    def leaderboard(self, score):
        rows=self.get('get_beatmaps',b=score['beatmap_id'])
        plays=int(rows[0].get('playcount') or 0) if rows else 0
        if plays<=1000:return None,plays
        leaders=self.get('get_scores',b=score['beatmap_id'],limit=100)
        for position,row in enumerate(leaders,1):
            row=dict(row,beatmap_id=score['beatmap_id'])
            if str(row.get('user_id'))!=str(self.user):continue
            same_id=score.get('score_id') and str(row.get('score_id'))==str(score['score_id'])
            if same_id or score_key(row)==score_key(score):return position,plays
        return None,plays

    def enrich_pp(self, score):
        if score.get("pp") is not None:
            return score
        if score.get('rank') != 'F':
            try:
                rows = self.get("get_scores", b=score["beatmap_id"], u=self.user, type="id", limit=100)
                for row in rows:
                    row["beatmap_id"] = score["beatmap_id"]
                    if score_key(row) == score_key(score):
                        score = dict(score, pp=row.get("pp"),score_id=row.get('score_id'))
                        break
            except RuntimeError:
                pass
            url = score_url(score)
            if score.get('pp') is None and url:
                try:
                    response = self.session.get(url,headers={'Accept':'application/json'},timeout=(5,12))
                    response.raise_for_status()
                    data = response.json()
                    if data.get('pp') is not None:
                        score = dict(score,pp=float(data['pp']),modern_id=data.get('id'),pp_source='server')
                except (requests.RequestException,ValueError,AttributeError):
                    pass
        if score.get('pp') is None:
            try:
                score,_ = self.local_maps.calculate(score,self.session)
            except (OSError,ValueError,requests.RequestException):
                pass
        return score


class Covers:
    def __init__(self, songs, offline=False, ignore_proxy=False):
        self.songs = Path(songs)
        self.offline, self.ignore_proxy = offline, ignore_proxy
        self.index, self.cache = {}, {}
        self.index_time = -999.0

    def get(self, beatmap_id, set_id):
        key = (str(beatmap_id), str(set_id))
        if key in self.cache:
            return self.cache[key]
        if time.monotonic() - self.index_time > 60:
            self.index = {}
            if self.songs.is_dir():
                for path in self.songs.iterdir():
                    match = re.match(r"^(\d+)(?:\s|$)", path.name)
                    if path.is_dir() and match:
                        self.index.setdefault(match[1], []).append(path)
            self.index_time = time.monotonic()
        for folder in self.index.get(str(set_id), []):
            for osu in folder.glob("*.osu"):
                try:
                    text = osu.read_text(encoding="utf-8-sig", errors="replace")
                    if not re.search(r"^BeatmapID\s*:\s*" + re.escape(str(beatmap_id)) + r"\s*$", text, re.M):
                        continue
                    for line in text.splitlines():
                        if re.match(r"^(?:0|Background)\s*,", line.strip()):
                            row = next(csv.reader([line]))
                            path = (folder / row[2].replace("\\", "/")).resolve()
                            if folder.resolve() in path.parents and path.is_file():
                                with Image.open(path) as img:
                                    result = ImageOps.fit(img.convert("RGB"), (208, 116), method=Image.Resampling.LANCZOS)
                                if len(self.cache) >= 128:
                                    self.cache.pop(next(iter(self.cache)))
                                self.cache[key] = result
                                return result
                except (OSError, ValueError, IndexError, csv.Error):
                    continue
        # Сетовый ID, а не beatmap ID. Сетевой резерв используется только при отсутствии локального фона.
        if not self.offline and str(set_id).isdigit():
            try:
                with session_for(self.ignore_proxy) as session:
                    response = session.get(f"https://assets.ppy.sh/beatmaps/{set_id}/covers/card.jpg", timeout=(4, 8))
                response.raise_for_status()
                with Image.open(io.BytesIO(response.content)) as img:
                    result = ImageOps.fit(img.convert("RGB"), (208, 116))
                if len(self.cache) >= 128:
                    self.cache.pop(next(iter(self.cache)))
                self.cache[key] = result
                return result
            except (requests.RequestException, OSError):
                pass
        return None

