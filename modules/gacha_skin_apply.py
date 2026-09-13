"""Persistent live skin; old OSK import cleanup retained for migration."""
import json
from pathlib import Path
import shutil
from modules.gacha_storage import atomic_json

LIVE_NAME = '! osu!gacha — Текущий скин'
MARKER = '.gacha-live.json'
OWNER = {'owner':'osu-skin-gacha-live-v1'}


def owned_live(path):
    try:
        return not path.is_symlink() and json.loads((path/MARKER).read_text(encoding='utf-8')) == OWNER
    except (OSError,ValueError):
        return False


def live_paths(box):
    paths = [box.skins/(LIVE_NAME+suffix) for suffix in ('','.new','.old')]
    if any(p.resolve().parent != box.skins.resolve() for p in paths):
        raise ValueError('Live skin path escaped Skins')
    return paths


def recover_live(box):
    live,new,old = live_paths(box)
    for path in (live,new,old):
        if path.exists() and not owned_live(path):
            raise ValueError('Папка текущего скина занята личными файлами: '+str(path))
    if old.exists() and not live.exists():
        old.rename(live)
    for path in (new,old):
        if path.exists(): shutil.rmtree(path)


def is_live_folder(path):
    return path.name == LIVE_NAME and owned_live(path)


def update_live(box, installed_name):
    journal = json.loads(box.journal.read_text(encoding='utf-8'))
    if not box.lock_file or journal.get('phase') != 'active':
        raise RuntimeError('Session is not active')
    source = (box.skins/installed_name).resolve()
    if source.parent != box.skins.resolve() or installed_name not in {n for _,n in journal.get('gacha',[])}:
        raise ValueError('Not a session skin')
    if not (source/'skin.ini').is_file(): raise ValueError('skin.ini not found')
    return copy_live(box, source, installed_name)


def copy_live(box, source, installed_name):
    files = [p for p in source.rglob('*') if p.is_file()]
    if any(not p.resolve().is_relative_to(source) for p in files): raise ValueError('External skin link')
    recover_live(box)
    live,new,old = live_paths(box)
    new.mkdir()
    atomic_json(new/MARKER,OWNER)
    try:
        for path in files:
            if path.name in (MARKER,'.gacha-origin.json','.gacha-apply.json'): continue
            dest = new/path.relative_to(source)
            dest.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(path,dest)
        if live.exists(): live.rename(old)
        new.rename(live)
    except Exception:
        recover_live(box)
        raise
    if old.exists(): shutil.rmtree(old)
    return installed_name


def cleanup_imports(box):
    """Remove only exact marker-owned temporary copies; retain pending imports for recovery."""
    registry = box.pack/'gacha_imports.json'
    if not registry.exists():
        return
    remaining = []
    for row in json.loads(registry.read_text(encoding='utf-8')):
        name,token = row['name'],row['token']
        if name != '!gacha-apply-'+token or len(token)!=32 or any(c not in '0123456789abcdef' for c in token):
            raise ValueError('Invalid import journal')
        if Path(row['skins']).resolve()!=box.skins.resolve():
            remaining.append(row)
            continue
        target = box.skins/name
        if target.resolve().parent != box.skins.resolve():
            raise ValueError('Import folder escaped Skins')
        marker = target/'.gacha-apply.json'
        try:
            owned = json.loads(marker.read_text()) == {'token':token}
        except (OSError,ValueError):
            owned = False
        if not owned:
            remaining.append(row)
            continue
        shutil.rmtree(target)
        archive = box.pack/'.gacha-imports'/(name+'.osk')
        try:
            archive.unlink(missing_ok=True)
        except OSError:
            pass
    atomic_json(registry,remaining)


def apply_collection(library, ident):
    """Apply an unlocked skin under the same sandbox lock as session operations."""
    box = library.box
    acquired = not box.lock_file
    if acquired: box.acquire()
    try:
        library.load()
        item = library.drops[ident]
        name = item['installed_name']
        if Path(name).name != name or name in ('.', '..'):
            raise ValueError('Invalid skin name')
        if box.journal.exists():
            return update_live(box, name)
        source = (box.active/name).resolve()
        if source.parent != box.active.resolve() or not (source/'skin.ini').is_file():
            raise ValueError('Skin files are missing')
        return copy_live(box, source, name)
    finally:
        if acquired: box.release()
