"""Источники скинов, локальные карты/скоры и публичный API Gatari.

Файлы osu! читаются только на чтение. Сетевые запросы не содержат API-ключ osu!.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import struct
import time
import zipfile
from datetime import datetime, timezone
from collections import OrderedDict
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
import rosu_pp_py as rosu

DRIVE_FOLDER = '1TjGeOjrcdXY6VHy4lJqpPrsRuHdmRCqv'
RANKS = ('SS', 'S', 'A', 'B', 'C', 'D', 'DT', 'special')


def session_for(ignore_proxy=False):
    session = requests.Session()
    session.trust_env = not ignore_proxy
    session.headers['User-Agent'] = 'osu-Skin-Gacha/3.0'
    return session


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + '.tmp')
    with tmp.open('w', encoding='utf-8') as out:
        json.dump(data, out, ensure_ascii=False)
        out.flush()
        os.fsync(out.fileno())
    os.replace(tmp, path)


def rank_name(value):
    return 'special' if value.casefold() in ('особая', 'особые', 'special') else value if value in RANKS else None


def drive_folder_id(value):
    match = re.search(r'/folders/([\w-]+)', value)
    ident = match.group(1) if match else value
    if not re.fullmatch(r'[\w-]{15,}', ident):
        raise ValueError('Неверная ссылка на папку Drive / Invalid Drive folder URL')
    return ident


def drive_listing(folder, session):
    """Публичный HTML-каталог; доступ редактора и вход в Google не нужны."""
    response = session.get('https://drive.google.com/embeddedfolderview', params={'id': folder}, timeout=(12, 25))
    response.raise_for_status()
    soup = BeautifulSoup(response.content, 'html.parser', from_encoding='utf-8')
    result = []
    for link in soup.find_all('a', href=True):
        href = link['href']
        match = re.match(r'https://drive\.google\.com/(?:drive/folders/|file/d/)([\w-]+)', href)
        if match:
            result.append(dict(id=match.group(1), name=link.get_text(strip=True), folder='/folders/' in href))
    if not result:
        raise ValueError('Drive: папка пуста или недоступна по ссылке / Folder is empty or not public')
    return result


class SkinSources:
    def __init__(self, settings, root, manifest=None, log=lambda text: None):
        self.settings, self.root, self.log = settings.copy(), Path(root), log
        self.cache = self.root / 'gacha_cache'
        self.manifest = manifest or Path(__file__).with_name('drive_catalog.json')
        self.progress = lambda *args: None
        self.known = {}
        if self.manifest.exists():
            data = json.loads(self.manifest.read_text(encoding='utf-8'))
            self.known = {(r['rank'], r['filename']): r for r in data.get('files', [])}

    def catalog(self):
        mode = self.settings.get('skin_source', 'folder')
        result = {}
        if mode == 'zip':
            archive = Path(self.settings.get('skin_archive', ''))
            if not archive.is_file():
                raise ValueError('Выберите ZIP со скинами / Select a skin ZIP')
            with zipfile.ZipFile(archive) as z:
                for entry in z.infolist():
                    parts = PurePosixPath(entry.filename.replace('\\', '/')).parts
                    if len(parts) < 2 or not entry.filename.lower().endswith('.osk'):
                        continue
                    rank = rank_name(parts[-2])
                    if not rank:
                        continue
                    known = self.known.get((rank, parts[-1]), {})
                    # CRC внешнего ZIP позволяет сверить вложенный .osk без распаковки гигабайт.
                    known = known if known.get('archive_crc') == entry.CRC else {}
                    ident = known.get('id') or hashlib.sha256(f'{entry.CRC}:{entry.file_size}:{parts[-1]}'.encode()).hexdigest()
                    token = 'zip-' + ident + '.osk'
                    result[token] = dict(id=ident, name=Path(parts[-1]).stem, rank=rank, size=known.get('size'),
                        source=token, kind='zip', archive=str(archive.resolve()), member=entry.filename,
                        archive_crc=entry.CRC, fingerprint=known.get('id'))
            if not result:
                raise ValueError('ZIP должен содержать папки рангов с .osk / No rank folders with .osk found in ZIP')
        elif mode == 'drive':
            folder = drive_folder_id(self.settings.get('drive_folder', DRIVE_FOLDER))
            index = self.cache / ('drive-' + folder + '.json')
            if self.settings.get('offline'):
                if index.exists():
                    rows = json.loads(index.read_text(encoding='utf-8'))
                elif folder == DRIVE_FOLDER:
                    rows = list(self.known.values())
                else:
                    raise ValueError('Нет офлайн-каталога Drive / No cached Drive index')
            else:
                self.log('Чтение каталога Drive / Reading Drive catalog…')
                rows = []
                try:
                    with session_for(self.settings.get('ignore_proxy')) as session:
                        for category in drive_listing(folder, session):
                            rank = rank_name(category['name'])
                            if not category['folder'] or not rank:
                                continue
                            listing = drive_listing(category['id'], session)
                            previews = {Path(f['name']).stem.casefold(): f['id'] for f in listing
                                        if not f['folder'] and Path(f['name']).suffix.lower() in ('.jpg', '.jpeg', '.png')}
                            for file in listing:
                                if not file['folder'] and file['name'].lower().endswith('.osk'):
                                    rows.append(dict(drive_id=file['id'], filename=file['name'], rank=rank,
                                                     preview_id=previews.get(Path(file['name']).stem.casefold())))
                    write_json(index, rows)
                except (requests.RequestException, ValueError) as error:
                    rows = []
                    if index.exists():
                        try:
                            rows = json.loads(index.read_text(encoding='utf-8'))
                        except (OSError, ValueError):
                            pass
                    if not rows and folder == DRIVE_FOLDER:
                        rows = list(self.known.values())
                    if not rows:
                        raise RuntimeError('Drive недоступен, резервного каталога нет. Проверьте сеть/VPN. / Drive unavailable; no cached catalog. Check network/VPN.') from None
                    self.log('Drive недоступен: используется резервный каталог. Загрузка скинов требует соединения. / Drive unavailable: using fallback catalog; downloads need a connection.')

            for row in rows:
                known = self.known.get((row['rank'], row['filename']), {})
                known = known if known.get('drive_id') == row['drive_id'] else {}
                ident = known.get('id') or 'drive-' + row['drive_id']
                token = 'drive-' + row['drive_id'] + '.osk'
                if self.settings.get('offline') and not (self.cache/token).is_file():
                    continue
                result[token] = dict(id=ident, name=Path(row['filename']).stem, rank=row['rank'], size=known.get('size'),
                    source=token, kind='drive', drive_id=row['drive_id'], fingerprint=known.get('id'),
                    preview_id=row.get('preview_id'))
        return result

    def materialize(self, item, settings):
        if item.get('kind', 'folder') == 'folder':
            return Path(item['source'])
        self.cache.mkdir(parents=True, exist_ok=True)
        target = self.cached_path(item)
        if target.is_file() and zipfile.is_zipfile(target):
            return target
        tmp = target.with_suffix('.part')
        try:
            if item['kind'] == 'zip':
                with zipfile.ZipFile(item['archive']) as z, z.open(item['member']) as inp, tmp.open('wb') as out:
                    shutil.copyfileobj(inp, out, 1024*1024)
            else:
                if settings.get('offline'):
                    raise ValueError('Скин не скачан: нужен интернет / Skin not cached: internet required')
                self.log('Загрузка / Download: '+item['name'])
                with session_for(settings.get('ignore_proxy')) as session:
                    url = 'https://drive.usercontent.google.com/download'
                    params = dict(id=item['drive_id'], export='download', confirm='t')
                    for attempt in range(2):
                        with session.get(url, params=params, stream=True, timeout=(8, 35)) as response:
                            response.raise_for_status()
                            if 'text/html' in response.headers.get('Content-Type', ''):
                                soup = BeautifulSoup(response.content, 'html.parser')
                                form = soup.find('form', id='download-form')
                                if form is None or attempt:
                                    raise ValueError('Drive: скачивание недоступно или превышена квота / Download unavailable or quota exceeded')
                                url = form.get('action', '')
                                if urlparse(url).hostname not in ('drive.usercontent.google.com', 'drive.google.com'):
                                    raise ValueError('Unexpected Drive download host')
                                params = {e['name']: e.get('value', '') for e in form.find_all('input', attrs={'name':True})}
                                continue
                            total = int(response.headers.get('Content-Length') or 0)
                            done, began, notified = 0, time.monotonic(), 0
                            self.progress(item['name'], 0, total, 0, None)
                            with tmp.open('wb') as out:
                                for block in response.iter_content(128*1024):
                                    out.write(block)
                                    done += len(block)
                                    now = time.monotonic()
                                    if now-notified >= .25:
                                        speed = done/max(.001, now-began)
                                        self.progress(item['name'], done, total, speed, max(0,total-done)/speed if total and speed else None)
                                        notified = now
                            self.progress(item['name'], done, total, done/max(.001,time.monotonic()-began), 0)
                            break
            if not zipfile.is_zipfile(tmp):
                raise ValueError('Загруженный файл не является .osk / Download is not an .osk archive')
            os.replace(tmp, target)
            return target
        finally:
            tmp.unlink(missing_ok=True)

    def cached_path(self,item):
        return self.cache / (hashlib.sha256(item['source'].encode()).hexdigest()+'.osk' if item['kind']=='zip' else item['source'])


class BinaryReader:
    """Ограниченный little-endian reader: повреждённая БД не даёт бесконечный цикл."""
    def __init__(self, stream):
        self.stream = stream

    def read(self, size):
        if not 0 <= size <= 256*1024*1024:
            raise ValueError('Invalid binary length')
        data = self.stream.read(size)
        if len(data) != size:
            raise ValueError('osu! ещё записывает файл / Incomplete osu! data')
        return data

    def number(self, fmt):
        return struct.unpack('<'+fmt, self.read(struct.calcsize('<'+fmt)))[0]

    def string(self):
        flag = self.number('B')
        if flag == 0:
            return ''
        if flag != 11:
            raise ValueError('Invalid osu! string')
        length = 0
        for shift in range(0, 35, 7):
            byte = self.number('B')
            length |= (byte & 127) << shift
            if not byte & 128:
                return self.read(length).decode('utf-8', errors='replace')
        raise ValueError('Invalid ULEB128')

    def count(self):
        count = self.number('i')
        if not 0 <= count <= 2_000_000:
            raise ValueError('Invalid item count')
        return count


def read_score(reader, replay=False):
    mode, version = reader.number('B'), reader.number('i')
    map_hash, player, replay_hash = reader.string(), reader.string(), reader.string()
    hits = [reader.number('H') for _ in range(6)]
    points, combo, perfect, mods = reader.number('I'), reader.number('H'), reader.number('B'), reader.number('I')
    reader.string()
    ticks, length = reader.number('q'), reader.number('i')
    if replay and length >= 0:
        reader.read(length)
    elif length != -1:
        raise ValueError('Invalid replay payload')
    online = reader.number('q') if version >= 20140721 else reader.number('i') if version >= 20121008 else 0
    if mods & (1 << 23):
        reader.number('d')
    return dict(mode=mode, beatmap_id=map_hash, map_hash=map_hash, player=player,
        replay_hash=replay_hash, score=points, maxcombo=combo, perfect=perfect, enabled_mods=mods,
        count300=hits[0], count100=hits[1], count50=hits[2], countgeki=hits[3], countkatu=hits[4], countmiss=hits[5],
        date=datetime.fromtimestamp((ticks-621355968000000000)/10_000_000, timezone.utc).strftime('%Y-%m-%d %H:%M:%S'),
        score_id=0, local_score_id=online, provider='offline', pp=None)


def read_scores_db(path):
    result = []
    with Path(path).open('rb') as stream:
        r = BinaryReader(stream)
        r.number('i')
        for _ in range(r.count()):
            r.string()
            for _ in range(r.count()):
                score = read_score(r)
                if score['mode'] == 0:
                    result.append(score)
    return result


def game_rank(score, failed=False):
    if failed:
        return 'F'
    n300,n100,n50,miss = (int(score.get(k) or 0) for k in ('count300','count100','count50','countmiss'))
    total = n300+n100+n50+miss
    if not total:
        return 'F'
    p = n300/total
    rank = 'X' if n300==total else 'S' if p>.9 and n50/total<.01 and not miss else 'A' if (p>.8 and not miss) or p>.9 else 'B' if (p>.7 and not miss) or p>.8 else 'C' if p>.6 else 'D'
    return rank+'H' if rank in ('X','S') and int(score.get('enabled_mods') or 0)&(8|1024) else rank


class LocalMaps:
    def __init__(self, osu):
        self.osu, self.songs = Path(osu), Path(osu)/'Songs'
        self.index, self.by_id, self.loaded, self.username = {}, {}, False, ''
        self.calculated = {}
        self.parsed = OrderedDict()
        self.db_stamp = None

    def load(self):
        db = self.osu/'osu!.db'
        stamp = (db.stat().st_mtime_ns,db.stat().st_size) if db.exists() else None
        if self.loaded and self.db_stamp==stamp:
            return
        if db.is_file():
            with db.open('rb') as stream:
                r = BinaryReader(stream)
                version = r.number('i')
                r.read(13)
                self.username = r.string()
                for _ in range(r.count()):
                    if version < 20191106:
                        r.number('i')
                    strings = [r.string() for _ in range(9)]
                    r.read(15)
                    r.read(16 if version >= 20140609 else 4)
                    r.read(8)
                    if version >= 20140609:
                        for _ in range(4):
                            r.read(r.count()*(10 if version >= 20250107 else 14))
                    r.read(12)
                    r.read(r.count()*17)
                    beatmap, set_id = r.number('i'), r.number('i')
                    r.read(14)
                    mode = r.number('B')
                    r.string(); r.string(); r.read(2); r.string(); r.read(10)
                    folder = r.string()
                    r.read(13)
                    if version < 20140609:
                        r.read(2)
                    r.read(5)
                    path = (self.songs/folder/strings[8]).resolve()
                    if mode == 0 and self.songs.resolve() in path.parents:
                        item = dict(path=str(path), beatmap_id=str(beatmap), beatmapset_id=str(set_id),
                            artist=strings[0], title=strings[2], version=strings[5], file_md5=strings[7])
                        self.index[strings[7]] = item
                        self.by_id[str(beatmap)] = item
        self.loaded = True
        self.db_stamp = stamp

    def locate(self, ident):
        self.load()
        return self.index.get(str(ident)) or self.by_id.get(str(ident))

    def calculate(self, score, session=None):
        item = self.locate(score.get('map_hash') or score['beatmap_id'])
        key = item['file_md5'] if item else str(score['beatmap_id'])
        beatmap = self.parsed.get(key)
        if beatmap is None:
            if item and Path(item['path']).is_file():
                data = Path(item['path']).read_bytes()
            elif session is not None and str(score['beatmap_id']).isdigit():
                response = session.get('https://osu.ppy.sh/osu/'+str(score['beatmap_id']), timeout=(5,15))
                response.raise_for_status()
                data = response.content
                if not data.lstrip(b'\xef\xbb\xbf').startswith(b'osu file format'):
                    raise ValueError('Map download is not an .osu file')
            else:
                raise ValueError('Локальный .osu файл не найден / Local .osu file not found')
            beatmap = rosu.Beatmap(bytes=data)
            self.parsed[key] = beatmap
            if len(self.parsed)>64:
                self.parsed.popitem(last=False)
        else:
            self.parsed.move_to_end(key)
        if beatmap.mode != rosu.GameMode.Osu or beatmap.is_suspicious():
            raise ValueError('Unsupported or suspicious beatmap')
        mods = int(score.get('enabled_mods') or 0)
        attrs = rosu.Difficulty(mods=mods, lazer=False).calculate(beatmap)
        hits = sum(int(score.get(k) or 0) for k in ('count300','count100','count50','countmiss'))
        failed = score.get('rank')=='F' or (score.get('provider')=='offline' and hits < beatmap.n_objects)
        args = dict(mods=mods, lazer=False, combo=int(score.get('maxcombo') or 0),
            n300=int(score.get('count300') or 0), n100=int(score.get('count100') or 0),
            n50=int(score.get('count50') or 0), misses=int(score.get('countmiss') or 0))
        if failed:
            args['passed_objects'] = hits
        pp = rosu.Performance(**args).calculate(beatmap).pp
        enriched = dict(score)
        if enriched.get('pp') is None:
            enriched.update(pp=pp, pp_source='calculated')
        if score.get('provider')=='offline':
            enriched['rank'] = game_rank(score, failed)
        info = dict(item or {}, difficultyrating=attrs.stars, max_combo=attrs.max_combo)
        return enriched, info


class OfflineAPI:
    """Полностью локальный монитор. Hard использует локальный PP-топ, не серверный."""
    def __init__(self, settings):
        self.settings = settings.copy()
        self.maps = LocalMaps(settings['osu_path'])
        self.session = session_for()
        self.language = settings.get('language')
        self.raw, self.done, self.stamps, self.map_infos = {}, {}, {}, {}
        self.user = settings.get('user_id','')
        self.baseline_weighted = None
        folder_id = hashlib.sha256(str(self.maps.osu.resolve()).encode()).hexdigest()[:16]
        self.cache_path = Path(settings['skin_pack_path'])/'gacha_cache'/('offline-rosu4-'+folder_id+'.json')
        if self.cache_path.is_file():
            try:
                cached = json.loads(self.cache_path.read_text(encoding='utf-8'))
                self.done = cached.get('scores',{})
                self.map_infos = {(row[0],row[1]):row[2] for row in cached.get('maps',[])}
            except (OSError,ValueError,KeyError,TypeError):
                self.done,self.map_infos = {},{}

    def snapshot(self):
        self.maps.load()
        username = self.settings.get('offline_username') or self.maps.username
        if not username:
            raise ValueError('Укажите локальный ник для офлайн-режима / Enter your local offline username')
        db = self.maps.osu/'scores.db'
        if db.exists():
            stat = db.stat()
            stamp = stat.st_mtime_ns,stat.st_size
            if self.stamps.get(str(db)) != stamp:
                rows = read_scores_db(db)
                after = db.stat()
                if stamp != (after.st_mtime_ns,after.st_size):
                    raise ValueError('osu! записывает scores.db; повторим чтение / Database is being written')
                for score in rows:
                    if score['player'].casefold() == username.casefold():
                        self.raw[score['replay_hash'] or str(score)] = score
                self.stamps[str(db)] = stamp
        for folder in (self.maps.osu/'Data'/'r', self.maps.osu/'Replays'):
            if not folder.exists():
                continue
            for path in folder.glob('*.osr'):
                stat = path.stat()
                stamp = stat.st_mtime_ns,stat.st_size
                if self.stamps.get(str(path)) == stamp:
                    continue
                try:
                    with path.open('rb') as stream:
                        score = read_score(BinaryReader(stream), replay=True)
                    if score['mode']==0 and score['player'].casefold()==username.casefold():
                        self.raw[score['replay_hash'] or str(score)] = score
                    self.stamps[str(path)] = stamp
                except (OSError,ValueError,OverflowError):
                    continue  # Незавершённый реплей перечитаем следующим опросом.
        changed = False
        for key, score in self.raw.items():
            if key not in self.done:
                try:
                    enriched, info = self.maps.calculate(score)
                    self.done[key] = enriched
                    self.map_infos[(score['beatmap_id'],int(score['enabled_mods']))] = info
                    changed = True
                except (OSError,ValueError):
                    continue
        if changed:
            write_json(self.cache_path,dict(scores=self.done,maps=[[k[0],k[1],v] for k,v in self.map_infos.items()]))
        values = [s for k,s in self.done.items() if k in self.raw and s['player'].casefold()==username.casefold()]
        best = {}
        for score in values:
            if score['rank']=='F':
                continue
            key = score['map_hash']
            if key not in best or score['pp'] > best[key]['pp']:
                best[key] = score
        best = sorted(best.values(),key=lambda s:s['pp'],reverse=True)[:100]
        weighted = sum(s['pp']*.95**i for i,s in enumerate(best))
        if self.baseline_weighted is None:
            self.baseline_weighted = weighted
        total = max(0,float(self.settings.get('offline_total_pp') or 0)+weighted-self.baseline_weighted)
        return dict(user_id=self.user,username=username,pp_raw=total),best,sorted(values,key=lambda s:s['date'],reverse=True)

    def beatmap(self, ident, mods):
        return self.map_infos[(ident,mods)]

    def enrich_pp(self, score):
        return score


class GatariAPI:
    def __init__(self, settings):
        self.session = session_for(settings.get('ignore_proxy'))
        self.user, self.language = settings['user_id'], settings.get('language')
        self.maps, self.local = {}, LocalMaps(settings['osu_path'])

    def get(self, endpoint, **params):
        try:
            response = self.session.get('https://api.gatari.pw/'+endpoint,params=params,timeout=(5,15))
            response.raise_for_status()
            data = response.json()
            if data.get('code',200) != 200:
                raise ValueError()
            return data
        except (requests.RequestException,ValueError):
            raise RuntimeError('Gatari API недоступен: проверьте ID и сеть / Check Gatari ID and connection') from None

    def profile(self):
        rows = self.get('users/get', ids=self.user).get('users') or []
        if not rows:
            raise ValueError('Профиль Gatari не найден / Gatari user not found')
        stats = self.get('user/stats',u=self.user,mode=0).get('stats') or {}
        return dict(user_id=str(rows[0]['id']),username=rows[0]['username'],pp_raw=stats.get('pp',0))

    def normalize(self, row):
        info = row['beatmap']
        score = dict(beatmap_id=str(info['beatmap_id']),score_id=row['id'],score=row['score'],
            user_id=self.user,
            maxcombo=row['max_combo'],enabled_mods=row['mods'],pp=row.get('pp'),
            rank='F' if row.get('completed',2)<2 else row.get('ranking','?'),provider='gatari',
            date=datetime.fromtimestamp(row['time'],timezone.utc).strftime('%Y-%m-%d %H:%M:%S'))
        for key,original in (('count300','count_300'),('count100','count_100'),('count50','count_50'),('countmiss','count_miss')):
            score[key] = row.get(original,0)
        self.maps[(score['beatmap_id'],score['enabled_mods'])] = dict(info,
            difficultyrating=info.get('difficulty',0), max_combo=info.get('fc'), stars_base=True)
        return score

    def snapshot(self):
        return (self.profile(),
            [self.normalize(r) for r in self.get('user/scores/best',id=self.user,mode=0,l=100).get('scores') or []],
            [self.normalize(r) for r in self.get('user/scores/recent',id=self.user,mode=0,l=50,f=1).get('scores') or []])

    def beatmap(self, ident, mods):
        key = ident,mods
        info = self.maps[key]
        if info.get('stars_base'):
            dummy = dict(beatmap_id=ident,enabled_mods=mods,pp=0)
            try:
                _, calculated = self.local.calculate(dummy, self.session)
                info.update(difficultyrating=calculated['difficultyrating'],max_combo=calculated['max_combo'],stars_base=False)
            except (OSError,ValueError,requests.RequestException):
                if mods & (2|16|64|256|512):
                    raise ValueError('Не удалось рассчитать ★ с модами / Modded star rating unavailable') from None
        return info

    def leaderboard(self, score):
        rows=self.get('beatmaps/get',bb=score['beatmap_id']).get('data') or []
        plays=int(rows[0].get('playcount') or 0) if rows else 0
        if plays<=1000:return None,plays
        leaders=self.get('beatmap/'+str(score['beatmap_id'])+'/scores',mode=0).get('data') or []
        for position,row in enumerate(leaders[:100],1):
            if str(row.get('userid'))==str(self.user) and str(row.get('id'))==str(score.get('score_id')):return position,plays
        return None,plays

    def enrich_pp(self, score):
        if score.get('pp') is None:
            try:
                score,_ = self.local.calculate(score,self.session)
            except (OSError,ValueError,requests.RequestException):
                pass
        return score
