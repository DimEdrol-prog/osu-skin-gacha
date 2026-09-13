"""osu! Skin Gacha: gacha_skins."""
from __future__ import annotations
import copy
import configparser
import hashlib
import zlib
from datetime import datetime
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
import zipfile
from modules.gacha_config import RANKS, tr
from modules.gacha_storage import atomic_json
from modules.gacha_skin_apply import cleanup_imports, recover_live, is_live_folder

def skin_manifest(source):
    """Содержимое без распаковки OSK: размер + CRC, одинаковый отпечаток папки и архива."""
    source = Path(source)
    if source.is_file():
        with zipfile.ZipFile(source) as archive:
            items = [(i.filename.replace('\\','/'),i.file_size,i.CRC) for i in archive.infolist() if not i.is_dir()]
    else:
        items = []
        for path in source.rglob('*'):
            if path.is_file() and not path.is_symlink() and path.name != '.gacha-origin.json':
                crc = 0
                with path.open('rb') as stream:
                    for chunk in iter(lambda:stream.read(1024*1024),b''):
                        crc = zlib.crc32(chunk,crc)
                items.append((path.relative_to(source).as_posix(),path.stat().st_size,crc))
    if items and all('/' in name for name,_,_ in items):
        roots = {name.split('/')[0] for name,_,_ in items}
        if len(roots) == 1:
            items = [(name.split('/',1)[1],size,crc) for name,size,crc in items]
    items = sorted((name.casefold(),size,crc) for name,size,crc in items if name != '.gacha-origin.json')
    digest = hashlib.sha256(json.dumps(items,ensure_ascii=False).encode('utf-8')).hexdigest()
    return digest,sum(size for _,size,_ in items)


def read_skin_ini(folder):
    config = configparser.ConfigParser(delimiters=(':' ,'='),interpolation=None,strict=False,comment_prefixes=('//',';','#'))
    config.optionxform = str
    path = next((p for p in Path(folder).iterdir() if p.name.lower() == 'skin.ini'),None)
    if path:
        raw = path.read_bytes()
        for encoding in ('utf-8-sig','cp1251','latin-1'):
            try:
                config.read_string(raw.decode(encoding))
                break
            except (UnicodeError,configparser.Error):
                config.clear()
    return config


def gameplay_file(path, prefix='default'):
    name = path.name.casefold()
    stem = re.sub(r'@2x$', '',path.stem.casefold())
    return (stem.startswith(('hitcircle','approachcircle','slider','reversearrow','followpoint','cursor','spinner','lighting','particle'))
            or bool(re.match(r'^hit(?:0|50|100|300)(?:k|g)?(?:-\d+)?$',stem))
            or bool(re.match(r'^(normal|soft|drum)-(hit(normal|whistle|finish|clap)|slider(slide|tick|whistle))\d*$',stem))
            or stem == 'combobreak'
            or bool(re.match(re.escape(Path(prefix).name.casefold())+r'-\d+$',stem))) and Path(name).suffix in ('.png','.jpg','.jpeg','.wav','.ogg','.mp3')


def mix_skin(gameplay, base, output):
    """osu!standard: UI/HUD базы, игровые ресурсы награды. Исходники не меняются."""
    donor,ui = read_skin_ini(gameplay),read_skin_ini(base)
    donor_prefix = donor.get('Fonts','HitCirclePrefix',fallback='default')
    base_prefix = ui.get('Fonts','HitCirclePrefix',fallback='default')
    # Копируем интерфейс базы. Шрифты score/combo могут совпадать с hitcircle — сохраняем их.
    for path in Path(base).rglob('*'):
        if path.is_file() and not path.is_symlink() and path.name not in ('skin.ini','.gacha-origin.json'):
            if gameplay_file(path,base_prefix) and not re.match(re.escape(Path(base_prefix).name)+r'-\d+(?:@2x)?$',path.stem,re.I):
                continue
            dest = output/path.relative_to(base)
            dest.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(path,dest)
    for path in Path(gameplay).rglob('*'):
        if path.is_file() and not path.is_symlink() and gameplay_file(path,donor_prefix):
            if re.match(re.escape(Path(donor_prefix).name)+r'-\d+(?:@2x)?$',path.stem,re.I):
                dest = output/re.sub('^'+re.escape(Path(donor_prefix).name),'gacha-hit',path.name,flags=re.I)
            else:
                dest = output/path.relative_to(gameplay)
            dest.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(path,dest)
    for section in ('General','Colours','Fonts'):
        if not ui.has_section(section):
            ui.add_section(section)
    general = ('AllowSliderBallTint','CursorCentre','CursorExpand','CursorRotate','CursorTrailRotate','CursorTrailLength',
               'SliderBallFlip','SliderBallFrames','HitCircleOverlayAboveNumber','SliderStyle','SpinnerFadePlayfield',
               'SpinnerFrequencyModulate','SpinnerNoBlink','AnimationFramerate')
    for key in general:
        ui.remove_option('General',key)
        if donor.has_option('General',key):
            ui.set('General',key,donor.get('General',key))
    for key in list(ui['Colours']):
        if key.startswith('Combo') or key in ('SliderBorder','SliderTrackOverride','SliderBall','SpinnerBackground'):
            ui.remove_option('Colours',key)
    if donor.has_section('Colours'):
        for key,value in donor.items('Colours'):
            if key.startswith('Combo') or key in ('SliderBorder','SliderTrackOverride','SliderBall','SpinnerBackground'):
                ui.set('Colours',key,value)
    ui.set('Fonts','HitCirclePrefix','gacha-hit')
    ui.set('Fonts','HitCircleOverlap',donor.get('Fonts','HitCircleOverlap',fallback='0'))
    # При отсутствии цифр в доноре используем стандартный префикс, не чужие цифры базы.
    if not list(output.glob('gacha-hit-*')):
        ui.set('Fonts','HitCirclePrefix','gacha-default-missing')
    ui.set('General','Name',Path(gameplay).name+' + UI')
    with (output/'skin.ini').open('w',encoding='utf-8') as stream:
        ui.write(stream,space_around_delimiters=True)


class SkinLibrary:
    """Постоянный реестр выдач. Все изменения выполняет один файловый поток."""
    def __init__(self,sandbox,sources=None):
        self.box = sandbox
        self.path = sandbox.slot_root/'gacha_collection.json'
        self.sources = sources
        self.drops,self.catalog = {},{}
        self.loaded = False

    def save(self):
        atomic_json(self.path,{'version':1,'drops':self.drops})

    def load(self):
        if not self.loaded:
            if self.path.exists():
                data = json.loads(self.path.read_text(encoding='utf-8'))
                self.drops = data['drops']
            self.loaded = True

    def scan(self):
        self.load()
        self.compact_names()
        remote = self.sources is not None and self.sources.settings.get('skin_source') != 'folder'
        pool = {rank:[] for rank in (*RANKS,'DT','special')} if remote else self.box.scan()
        catalog = {}
        for rank,paths in pool.items():
            for path in paths:
                try:
                    ident,size = skin_manifest(path)
                    catalog[str(path)] = dict(id=ident,size=size,rank=rank,name=path.stem if path.is_file() else path.name,source=str(path))
                except (OSError,zipfile.BadZipFile):
                    self.box.log(f'Не удалось прочитать скин / Cannot read skin: {path.name}')
        self.catalog = catalog
        if remote:
            catalog.update(self.sources.catalog())
            for source,item in catalog.items():
                cached = self.sources.cached_path(item)
                if not item.get('fingerprint') and cached.is_file():
                    ident,size = skin_manifest(cached)
                    item.update(id=ident,size=size)
                pool[item['rank']].append(Path(source))
        # Миграция старых выдач по имени и содержимому; личные скины не считаются наградами.
        folders = [self.box.active]
        if self.box.journal.exists():
            folders.append(self.box.skins)
        changed = False
        for folder in folders:
            if not folder.exists():
                continue
            for installed in folder.iterdir():
                if not installed.is_dir():
                    continue
                marker = installed/'.gacha-origin.json'
                try:
                    if marker.exists():
                        saved = json.loads(marker.read_text(encoding='utf-8'))
                        ident = saved['id']
                        if ident not in self.drops:
                            self.drops[ident] = saved
                            changed = True
                        continue
                    candidates = [c for c in catalog.values() if installed.name == c['name'] or re.fullmatch(re.escape(c['name'])+r' \(\d+\)',installed.name)]
                    if not candidates:
                        ident,_ = skin_manifest(installed)
                        candidates = [c for c in catalog.values() if c['id'] == ident]
                    for item in candidates:
                        if item['id'] not in self.drops:
                            self.drops[item['id']] = dict(item,installed_name=installed.name,favorite=False,unlocked_at='legacy',status='complete')
                            changed = True
                except (OSError,ValueError,KeyError):
                    continue
        for ident,item in list(self.drops.items()):
            if item.get('status') == 'pending':
                exists = any((f/item['installed_name']/'.gacha-origin.json').exists() for f in folders)
                if exists:
                    item['status'] = 'complete'
                else:
                    del self.drops[ident]
                changed = True
        if changed:
            self.save()
        coexist = False
        if self.box.journal.exists():
            coexist = bool(json.loads(self.box.journal.read_text(encoding='utf-8')).get('keep_personal'))
        bases = self.box.backup if self.box.journal.exists() and not coexist else self.box.skins
        base_names = sorted(p.name for p in bases.iterdir() if p.is_dir()) if bases.exists() else []
        return dict(pool=pool,catalog=catalog,drops=copy.deepcopy(self.drops),bases=base_names,roots=self.box.identity)

    def award(self,source,settings):
        self.load()
        item = self.catalog[str(source)]
        ident = item['id']
        if ident in self.drops:
            raise ValueError('Этот скин уже выпадал / Skin already unlocked')
        if settings['exclude_heavy'] and item['size'] is not None and item['size'] > 30*1024*1024:
            raise ValueError('Скин больше 30 МБ / Skin exceeds 30 MB')
        if self.sources:
            source = self.sources.materialize(item,settings)
            content_id,size = skin_manifest(source)
            if item.get('fingerprint') and item['fingerprint'] != content_id:
                raise ValueError('Скин в источнике изменился; обновите каталог / Skin fingerprint changed')
            item = dict(item,id=content_id,size=size,content_id=content_id)
            self.catalog[item['source']] = item
            ident = content_id
            if content_id in self.drops or any(d.get('content_id')==content_id for d in self.drops.values()):
                raise ValueError('Этот скин уже выпадал / Skin already unlocked')
            if settings['exclude_heavy'] and size > 30*1024*1024:
                raise ValueError('Скин больше 30 МБ / Skin exceeds 30 MB')
        base = None
        if settings['optimize_skins']:
            base_folder = self.box.skins if settings.get('keep_personal') else self.box.backup
            base = base_folder/settings['interface_skin']
            if not settings['interface_skin'] or base.parent != base_folder or not base.is_dir():
                raise ValueError(tr('no_base',settings['language']))
        # Имена группируют новые награды в начале сортировки по папке, свежие — выше старых.
        order = max(0,1999-len(self.drops))
        name = f'!{order:04d} {item["name"]}'[:180]
        name = self.box.free_name(self.box.skins,name).name
        drop = dict(item,installed_name=name,favorite=False,status='pending',unlocked_at=datetime.now().astimezone().isoformat())
        self.drops[ident] = drop
        self.save()
        try:
            self.box.install(source,target_name=name,base=base,origin=drop)
            drop['status'] = 'complete'
            self.save()
            return copy.deepcopy(drop)
        except Exception:
            if not (self.box.skins/name/'.gacha-origin.json').exists():
                self.drops.pop(ident,None)
                self.save()
            raise

    def compact_names(self):
        """Миграция имён только в закрытом слоте; намерение сохраняется до rename."""
        if self.box.recover_needed():
            return
        candidates = [d for d in self.drops.values() if d.get('rename_to') or re.match(r'^! Gacha \d{8} - ',d.get('installed_name',''))]
        if not candidates:
            return
        self.box.acquire()
        try:
            if self.box.recover_needed():
                return
            active = self.box.active.resolve()
            if active != self.box.slot_root.resolve()/'gacha_active':
                raise ValueError('Unsafe skin migration directory')
            for item in candidates:
                old = active/item['installed_name']
                if old.resolve().parent != active:
                    raise ValueError('Unsafe skin migration path')
                if not item.get('rename_to'):
                    number = int(re.match(r'^! Gacha (\d{8}) - ',old.name)[1])
                    order = max(0,1999-(99999999-number))
                    target = self.box.free_name(active,f'!{order:04d} {item["name"]}'[:180])
                    if not old.is_dir():
                        continue
                    item['rename_to'] = target.name
                    self.save()
                target = active/item['rename_to']
                if target.resolve().parent != active:
                    raise ValueError('Unsafe skin migration target')
                if old.is_dir():
                    if target.exists():
                        raise ValueError('Skin migration name collision')
                    old.rename(target)
                if target.is_dir():
                    item['installed_name'] = target.name
                    item.pop('rename_to',None)
                    self.save()
                    self.box.log('Имя награды сокращено / Reward name shortened: '+target.name)
        finally:
            self.box.release()

    def favorite(self,ident,value):
        self.load()
        self.drops[ident]['favorite'] = bool(value)
        self.save()
        return copy.deepcopy(self.drops)

    def delete_nonfavorites(self):
        """Delete registered rewards in the inactive current slot; never game folders."""
        if self.box.recover_needed():raise ValueError('Сначала завершите сессию / End the session first')
        self.box.acquire()
        try:
            if self.box.recover_needed():raise ValueError('Session recovery required')
            self.load()
            active=self.box.active.resolve()
            if active != self.box.slot_root.resolve()/'gacha_active':raise ValueError('Unsafe collection directory')
            protected={(active/i['installed_name']).resolve() for i in self.drops.values() if i.get('favorite')}
            targets=[]
            for ident,item in self.drops.items():
                if item.get('favorite'):continue
                target=active/item.get('installed_name','')
                resolved=target.resolve()
                if resolved.parent!=active or resolved==active or resolved in protected or target.is_symlink():
                    raise ValueError('Unsafe collection path')
                # Reject reparse points inside the tree as well as at its root.
                if target.exists():
                    for root,dirs,files in os.walk(target,followlinks=False):
                        for child in [Path(root)]+[Path(root)/n for n in dirs+files]:
                            if child.is_symlink() or getattr(child.lstat(),'st_file_attributes',0)&0x400:
                                raise ValueError('Linked files cannot be removed by collection cleanup')
                            if not child.resolve().is_relative_to(active):raise ValueError('Unsafe child path')
                targets.append((ident,resolved))
            for ident,target in targets:
                if target.is_dir():shutil.rmtree(target)
                elif target.exists():raise ValueError('Expected a skin directory')
                self.drops.pop(ident,None);self.save()
            return copy.deepcopy(self.drops)
        finally:self.box.release()

    def reset_all(self):
        """Удаляем только зарегистрированные награды в активных папках слотов."""
        if self.box.recover_needed():
            raise ValueError('Сначала завершите сессию / End the session first')
        self.box.acquire()
        try:
            reset_plan = []
            for root in (self.box.pack,self.box.pack/'slots'/'2',self.box.pack/'slots'/'3'):
                ledger = root/'gacha_collection.json'
                drops = json.loads(ledger.read_text(encoding='utf-8')).get('drops',{}) if ledger.exists() else {}
                active = (root/'gacha_active').resolve()
                if active != self.box.pack.resolve()/root.relative_to(self.box.pack)/'gacha_active':
                    raise ValueError('Unsafe skin reset directory')
                targets = []
                for item in drops.values():
                    target = (active/item.get('installed_name','')).resolve()
                    if target.parent != active or target == active or target.is_symlink():
                        raise ValueError('Unsafe skin reset path')
                    targets.append(target)
                reset_plan.append((ledger, targets))
            # Проверяем весь план до первого удаления, включая пути остальных слотов.
            for ledger, targets in reset_plan:
                for target in targets:
                    if target.is_dir():
                        shutil.rmtree(target)
                if ledger.exists():
                    atomic_json(ledger,{'version':1,'drops':{}})
            self.drops = {}
            return True
        finally:
            self.box.release()

    def export(self,ident):
        if self.box.recover_needed():
            raise ValueError('Сначала завершите сессию / End the session first')
        self.box.acquire()
        try:
            self.load()
            item = self.drops[ident]
            source = self.box.active/item['installed_name']
            if not source.is_dir() or source.parent != self.box.active:
                raise FileNotFoundError('Выигранный скин не найден / Unlocked skin is missing')
            previous = self.box.skins/item.get('exported_name','__none__')
            if previous.is_dir() and item.get('exported_name'):
                return previous.name
            dest = self.box.free_name(self.box.skins,item['name'])
            with tempfile.TemporaryDirectory(prefix='.gacha-export-',dir=self.box.pack) as tmp:
                stage = Path(tmp)/'skin'
                shutil.copytree(source,stage)
                (stage/'.gacha-origin.json').unlink(missing_ok=True)
                shutil.move(str(stage),str(dest))
            item['exported_name'] = dest.name
            self.save()
            return dest.name
        finally:
            self.box.release()


class Sandbox:
    """Последовательный файловый сервис с журналом и блокировкой второго экземпляра."""
    def __init__(self, osu, pack, log=lambda value: None, slot='1'):
        self.skins = Path(osu).resolve() / "Skins"
        self.pack = Path(pack).resolve()
        self.backup, self.active = self.pack / "user_backup", self.pack / "gacha_active"
        self.journal = self.pack / "gacha_session.json"
        self.slot = str(slot) if str(slot) in ('1','2','3') else '1'
        # Журнал определяет слот восстановления после аварии, а не новое значение настройки.
        if self.journal.exists():
            self.slot = str(json.loads(self.journal.read_text(encoding='utf-8')).get('slot','1'))
            if self.slot not in ('1','2','3'):
                raise ValueError('Invalid journal slot')
        self.slot_root = self.pack if self.slot == '1' else self.pack/'slots'/self.slot
        self.active = self.slot_root/'gacha_active'
        self.identity = (str(self.pack),str(self.skins),self.slot)
        self.log = log
        self.lock_file = None

    def acquire(self):
        if self.lock_file:
            return
        self.pack.mkdir(parents=True, exist_ok=True)
        self.lock_file = (self.pack / ".gacha.lock").open("a+b")
        try:
            self.lock_file.seek(0)
            if os.name == "nt":
                import msvcrt
                if not self.lock_file.read(1):
                    self.lock_file.write(b"0")
                    self.lock_file.flush()
                self.lock_file.seek(0)
                msvcrt.locking(self.lock_file.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            self.lock_file.close()
            self.lock_file = None
            raise OSError("Песочница занята другим экземпляром / Sandbox is in use") from None

    def release(self):
        if self.lock_file:
            self.lock_file.close()
            self.lock_file = None

    @staticmethod
    def free_name(folder, name):
        target = folder / name
        number = 1
        while target.exists():
            target = folder / f"{name} ({number})"
            number += 1
        return target

    def move(self, source, destination):
        # Ничего не удаляем и не сливаем при совпадении имён.
        if source.exists():
            destination.parent.mkdir(parents=True, exist_ok=True)
            if destination.exists():
                raise FileExistsError(str(destination))
            shutil.move(str(source), str(destination))
            self.log(f"{source.name} → {destination.parent.name}/{destination.name}")

    def recover_needed(self):
        return self.journal.exists() or (self.backup.exists() and any(self.backup.iterdir()))

    def start(self, keep_personal=False, progress=lambda done,total:None, cancel=None):
        if not self.skins.parent.is_dir() or not self.pack.is_dir():
            raise OSError("Папка не найдена / Folder not found")
        for path in (self.pack, self.backup, self.active):
            if path == self.skins or self.skins in path.parents or path in self.skins.parents:
                raise ValueError("Папки песочницы пересекаются / Sandbox folders overlap")
        self.acquire()
        if self.recover_needed():
            raise RuntimeError("Сначала восстановите скины / Recover skins first")
        for path in (self.skins, self.backup, self.active):
            path.mkdir(parents=True, exist_ok=True)
        cleanup_imports(self)
        recover_live(self)
        data = {"phase": "starting", "skins": str(self.skins), "personal": [], "gacha": [], "slot":self.slot,"keep_personal":keep_personal}
        # Записываем намерение ДО каждого переноса: восстановление идемпотентно.
        atomic_json(self.journal, data)
        personal = [] if keep_personal else [p for p in self.skins.iterdir() if not is_live_folder(p)]
        progress(0,len(personal))
        for done,source in enumerate(personal,1):
            if cancel and cancel.is_set():
                self.stop()
                raise RuntimeError('Запуск отменён, личные скины восстановлены / Start cancelled; personal skins restored')
            dest = self.free_name(self.backup, source.name)
            data["personal"].append([source.name, dest.name])
            atomic_json(self.journal, data)
            self.move(source, dest)
            progress(done,len(personal))
        for source in list(self.active.iterdir()):
            if cancel and cancel.is_set():
                self.stop()
                raise RuntimeError('Запуск отменён / Start cancelled')
            dest = self.free_name(self.skins, source.name)
            data["gacha"].append([source.name, dest.name])
            atomic_json(self.journal, data)
            self.move(source, dest)
        if cancel and cancel.is_set():
            self.stop()
            raise RuntimeError('Запуск отменён / Start cancelled')
        data["phase"] = "active"
        atomic_json(self.journal, data)

    def stop(self, progress=lambda done,total:None):
        self.acquire()
        cleanup_imports(self)
        recover_live(self)
        if self.journal.exists():
            data = json.loads(self.journal.read_text(encoding="utf-8"))
            if Path(data["skins"]).resolve() != self.skins:
                raise ValueError("Путь osu! отличается от журнала / osu! path differs from journal")
            # Неполный старт откатывается строго по журналу.
            if data["phase"] == "starting":
                for old, new in reversed(data["gacha"]):
                    self.move(self.skins / new, self.active / old)
                data['phase'] = 'rollback_personal'
                atomic_json(self.journal, data)
            if data['phase'] == 'rollback_personal':
                progress(0,len(data['personal']))
                for done, (old, new) in enumerate(reversed(data["personal"]),1):
                    self.move(self.backup / new, self.skins / old)
                    progress(done,len(data['personal']))
                self.journal.unlink()
                self.release()
                return
        else:
            # Совместимость со старой версией: непустой user_backup означает активную сессию.
            if not self.backup.exists() or not any(self.backup.iterdir()):
                self.release()
                return
            data = {"phase": "active", "skins": str(self.skins)}
        if data["phase"] == "active":
            self.active.mkdir(parents=True, exist_ok=True)
            data["returns"] = []
            reserved = {p.name for p in self.active.iterdir()}
            owned = {new for old,new in data.get('gacha',[])}
            for source in self.skins.iterdir():
                if is_live_folder(source): continue
                if data.get('keep_personal') and source.name not in owned:
                    continue
                name, n = source.name, 1
                while name in reserved:
                    name = f"{source.name} ({n})"
                    n += 1
                reserved.add(name)
                data["returns"].append([source.name, name])
            data["restores"] = [[p.name, p.name] for p in self.backup.iterdir()]
            data["phase"] = "stopping"
            atomic_json(self.journal, data)
        if data["phase"] == "stopping":
            for old, new in data["returns"]:
                self.move(self.skins / old, self.active / new)
            data["phase"] = "restoring"
            atomic_json(self.journal, data)
        progress(0,len(data['restores']))
        for done, (old, new) in enumerate(data["restores"],1):
            source = self.backup / old
            if source.exists():
                dest = self.free_name(self.skins, new)
                self.move(source, dest)
            progress(done,len(data['restores']))
        self.journal.unlink(missing_ok=True)
        self.release()

    def scan(self):
        result = {r: [] for r in (*RANKS, "DT", "special")}
        for rank in result:
            folders = ("особые", "особая", "special") if rank == "special" else (rank,)
            for folder in folders:
                path = self.pack / folder
                if path.is_dir():
                    result[rank].extend(p for p in path.iterdir() if p.suffix.lower() == ".osk" or (p.is_dir() and (p / "skin.ini").exists()))
        return result

    def install(self, source, target_name=None, base=None, origin=None):
        if not self.lock_file or not self.journal.exists():
            raise RuntimeError("Песочница не активна / Sandbox is not active")
        target = self.free_name(self.skins, target_name or (source.stem if source.is_file() else source.name))
        # Извлекаем во временную папку на том же диске; готовый скин публикуем переименованием.
        with tempfile.TemporaryDirectory(prefix=".gacha-stage-", dir=self.pack) as tmp:
            stage = Path(tmp) / "skin"
            stage.mkdir()
            if source.is_dir():
                shutil.copytree(source, stage, dirs_exist_ok=True)
            else:
                with zipfile.ZipFile(source) as archive:
                    for item in archive.infolist():
                        name = item.filename.replace("\\", "/")
                        parts = Path(name).parts
                        if Path(name).is_absolute() or ".." in parts or ":" in name or ((item.external_attr >> 16) & 0o170000) == 0o120000:
                            raise ValueError("Небезопасный путь в архиве / Unsafe archive path")
                        dest = stage.joinpath(*parts)
                        if item.is_dir():
                            dest.mkdir(parents=True, exist_ok=True)
                        else:
                            dest.parent.mkdir(parents=True, exist_ok=True)
                            with archive.open(item) as inp, dest.open("wb") as out:
                                shutil.copyfileobj(inp, out)
            roots = list(stage.iterdir())
            if len(roots) == 1 and roots[0].is_dir() and (roots[0] / "skin.ini").exists():
                stage = roots[0]
            if base is not None:
                mixed = Path(tmp)/'mixed'
                mixed.mkdir()
                mix_skin(stage,base,mixed)
                stage = mixed
            if origin is not None:
                atomic_json(stage/'.gacha-origin.json',origin)
            # Регистрируем назначение до публикации: восстановление после сбоя не трогает личные папки.
            journal = json.loads(self.journal.read_text(encoding='utf-8'))
            journal.setdefault('gacha',[]).append([target.name,target.name])
            atomic_json(self.journal,journal)
            shutil.move(str(stage), str(target))
        self.log(f"Скин установлен / Skin installed: {target.name}")
        return target.name

