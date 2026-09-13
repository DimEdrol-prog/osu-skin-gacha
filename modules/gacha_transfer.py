"""Portable user data; validated staging, additive import and rollback on write failure."""
import copy
import json
import re
import shutil
import tempfile
import zipfile
from pathlib import Path, PurePosixPath
from datetime import datetime
from modules.gacha_config import DEFAULTS
from modules.gacha_storage import atomic_json

LOCAL_KEYS={'osu_path','skin_pack_path','tablet_driver_path','skin_archive','interface_skin','setup_complete','osu_launch_enabled','tablet_driver_enabled','optimize_skins'}
SECRET_KEYS={'api_key','access_token','refresh_token','client_secret','password'}


def scrub(value, secret=''):
    if isinstance(value,dict):return {k:scrub(v,secret) for k,v in value.items() if k.casefold() not in SECRET_KEYS}
    if isinstance(value,(list,tuple)):return [scrub(v,secret) for v in value]
    if isinstance(value,str) and secret:return value.replace(secret,'[redacted]')
    return value


def slot_root(pack,slot):return pack if slot=='1' else pack/'slots'/slot


def export_data(path, settings, history, pack, include_key=False, box=None):
    if box is not None:
        if box.recover_needed():raise ValueError('Сначала завершите сессию')
        box.acquire()
    try:return _export_data(path,settings,history,pack,include_key)
    finally:
        if box is not None:box.release()


def _export_data(path, settings, history, pack, include_key=False):
    pack=Path(pack).resolve();path=Path(path)
    secret=settings.get('api_key','')
    config=scrub({k:v for k,v in settings.items() if k in DEFAULTS or k=='server_user_ids'},secret)
    for key in LOCAL_KEYS:config.pop(key,None)
    if include_key:config['api_key']=secret
    payload={'format':'osu-gacha-transfer','version':1,'settings':config,'sessions':scrub(list(history.values()),secret),'slots':{}}
    entries=[]
    for slot in ('1','2','3'):
        root=slot_root(pack,slot);ledger=root/'gacha_collection.json'
        if not root.resolve().is_relative_to(pack) or not (root/'gacha_active').resolve().is_relative_to(pack):raise ValueError('External slot folder')
        drops=json.loads(ledger.read_text(encoding='utf-8')).get('drops',{}) if ledger.exists() else {}
        payload['slots'][slot]={}
        for ident,item in drops.items():
            if not re.fullmatch(r'[a-zA-Z0-9_-]+',ident):raise ValueError('Invalid collection ID')
            source=(root/'gacha_active'/item['installed_name']).resolve()
            if source.parent!=(root/'gacha_active').resolve() or not (source/'skin.ini').is_file():raise ValueError('Не найден скин: '+item['name'])
            row=scrub(item,secret);row.pop('exported_name',None);payload['slots'][slot][ident]=row
            for file in source.rglob('*'):
                if file.is_symlink() or not file.resolve().is_relative_to(source):raise ValueError('External skin link')
                if file.is_file():entries.append((file,f'skins/{slot}/{ident}/{file.relative_to(source).as_posix()}'))
    temporary=path.with_name(path.name+'.part')
    try:
        with zipfile.ZipFile(temporary,'w',zipfile.ZIP_DEFLATED,compresslevel=5) as z:
            z.writestr('manifest.json',json.dumps(payload,ensure_ascii=False))
            for file,name in entries:z.write(file,name)
        temporary.replace(path)
    finally:temporary.unlink(missing_ok=True)
    return str(path)


def validate_manifest(data):
    if not isinstance(data,dict) or data.get('format')!='osu-gacha-transfer' or data.get('version')!=1:raise ValueError('Unsupported transfer file')
    if not isinstance(data.get('settings'),dict) or not isinstance(data.get('slots'),dict) or not isinstance(data.get('sessions'),list):raise ValueError('Invalid manifest')
    for session in data['sessions']:
        if not isinstance(session,dict) or not re.fullmatch(r'[a-zA-Z0-9_-]+',str(session.get('id',''))):raise ValueError('Invalid session')
        datetime.fromisoformat(session['started_at'])
        if not isinstance(session.get('user_id'),str) or not isinstance(session.get('records'),list):raise ValueError('Invalid history')
        for row in session['records']:
            if not isinstance(row,dict) or not isinstance(row.get('score'),dict) or not isinstance(row.get('map'),dict) or 'reward' not in row:raise ValueError('Invalid score')
    for slot,drops in data['slots'].items():
        if slot not in ('1','2','3') or not isinstance(drops,dict):raise ValueError('Invalid slot')
        for ident,item in drops.items():
            if not re.fullmatch(r'[a-zA-Z0-9_-]+',ident) or not isinstance(item,dict) or not isinstance(item.get('name'),str):raise ValueError('Invalid skin')
            name=item.get('installed_name','')
            if not name or Path(name).name!=name or any(c in name for c in '/\\:') or name in ('.','..'):raise ValueError('Invalid skin folder')
    for key,value in data['settings'].items():
        if key in DEFAULTS:
            default=DEFAULTS[key]
            if isinstance(default,bool) and not isinstance(value,bool):raise ValueError('Invalid setting: '+key)
            if isinstance(default,str) and not isinstance(value,str):raise ValueError('Invalid setting: '+key)
            if isinstance(default,(int,float)) and not isinstance(default,bool):
                import math
                if not isinstance(value,(int,float)) or isinstance(value,bool) or not math.isfinite(value):raise ValueError('Invalid number')
    from modules.gacha_config import THEMES, COLORS
    for key,allowed in {'theme':THEMES,'color':COLORS,'language':('Русский','English'),'difficulty':('Hard','Medium','Fun'),'slot':('1','2','3'),'server':('bancho','gatari'),'skin_source':('drive','zip','folder'),'ui_scale':('90%','100%','110%','125%')}.items():
        if key in data['settings'] and data['settings'][key] not in allowed:raise ValueError('Invalid setting: '+key)
    for key,low,high in [('interval',1,300),('rofl_chance',0,100)]:
        if key in data['settings'] and (not low<=data['settings'][key]<=high or int(data['settings'][key])!=data['settings'][key]):raise ValueError('Invalid setting: '+key)
    ids=data['settings'].get('server_user_ids',{})
    if not isinstance(ids,dict) or any(k not in ('bancho','gatari') or not isinstance(v,str) or (v and not v.isdigit()) for k,v in ids.items()):raise ValueError('Invalid profile IDs')
    user=data['settings'].get('user_id','')
    if user and not user.isdigit():raise ValueError('Invalid user ID')
    for key,value in data['settings'].items():
        if key.startswith('goal_'):
            maximum=20 if key=='goal_stars' else 100 if key.startswith('goal_Hard_') else 100000
            if not 0<value<=maximum:raise ValueError('Invalid reward threshold')
    return data


def import_data(path, app_settings, history, box, settings_store, history_store):
    """UI guarantees idle; process lock also excludes another app instance."""
    if box.recover_needed():raise ValueError('Сначала завершите сессию')
    box.acquire();created=[];backups={}
    def write(path,data):
        path=Path(path)
        if path not in backups:backups[path]=path.read_bytes() if path.exists() else None
        atomic_json(path,data)
    try:
        with tempfile.TemporaryDirectory(prefix='.gacha-transfer-',dir=box.pack) as tmp, zipfile.ZipFile(path) as z:
            if z.getinfo('manifest.json').file_size>50*1024*1024:raise ValueError('Manifest too large')
            data=validate_manifest(json.loads(z.read('manifest.json')))
            total=sum(info.file_size for info in z.infolist())
            if total>shutil.disk_usage(box.pack).free:raise ValueError('Недостаточно свободного места для импорта')
            stage=Path(tmp);seen=set()
            for entry in z.infolist():
                parts=PurePosixPath(entry.filename).parts
                if entry.filename=='manifest.json':continue
                if entry.is_dir():continue
                if len(parts)<4 or parts[0]!='skins' or parts[1] not in data['slots'] or parts[2] not in data['slots'][parts[1]]:raise ValueError('Unexpected archive entry')
                if any(p in ('..','.') or ':' in p or '\\' in p for p in parts) or PurePosixPath(entry.filename).is_absolute():raise ValueError('Unsafe archive path')
                dest=stage.joinpath(*parts)
                if not dest.resolve().is_relative_to(stage.resolve()) or str(dest).casefold() in seen:raise ValueError('Duplicate or unsafe path')
                seen.add(str(dest).casefold());dest.parent.mkdir(parents=True,exist_ok=True)
                with z.open(entry) as source,dest.open('wb') as target:shutil.copyfileobj(source,target)
            plans=[]
            for slot,drops in data['slots'].items():
                root=slot_root(box.pack,slot);ledger=root/'gacha_collection.json'
                if not root.resolve().is_relative_to(box.pack.resolve()) or not (root/'gacha_active').resolve().is_relative_to(box.pack.resolve()):raise ValueError('External slot folder')
                current=json.loads(ledger.read_text(encoding='utf-8')).get('drops',{}) if ledger.exists() else {}
                reserved={p.name.casefold() for p in (root/'gacha_active').iterdir()} if (root/'gacha_active').exists() else set()
                for ident,item in drops.items():
                    source=stage/'skins'/slot/ident
                    if not (source/'skin.ini').is_file():raise ValueError('Missing skin.ini: '+item['name'])
                    if ident in current:continue
                    name=item['installed_name'];n=1
                    while name.casefold() in reserved:name=f"{item['installed_name']} ({n})";n+=1
                    reserved.add(name.casefold());dest=root/'gacha_active'/name
                    if dest.resolve().parent!=(root/'gacha_active').resolve():raise ValueError('Unsafe destination')
                    row=dict(item,id=ident,installed_name=name,status='complete');row.pop('exported_name',None)
                    atomic_json(source/'.gacha-origin.json',row)
                    current[ident]=row;plans.append((source,dest))
                data['slots'][slot]=current
            updated=copy.deepcopy(app_settings)
            updated.update({k:v for k,v in data['settings'].items() if (k in DEFAULTS or k=='server_user_ids') and k not in LOCAL_KEYS and k!='api_key'})
            if data['settings'].get('api_key'):updated['api_key']=data['settings']['api_key']
            # Local sources are machine-specific; keep the destination source selection.
            for key in ('skin_source','drive_folder'):updated[key]=app_settings[key]
            for source,dest in plans:
                dest.parent.mkdir(parents=True,exist_ok=True);shutil.move(str(source),str(dest));created.append(dest)
            for slot,drops in data['slots'].items():write(slot_root(box.pack,slot)/'gacha_collection.json',{'version':1,'drops':drops})
            merged=dict(history)
            for session in data['sessions']:
                if session['id'] not in merged:
                    write(history_store.paths[0]/(session['id']+'.json'),session);merged[session['id']]=session
            write(settings_store.paths[0],updated)
            return updated,merged,len(created)
    except Exception:
        for target,original in reversed(list(backups.items())):
            if original is None:target.unlink(missing_ok=True)
            else:target.write_bytes(original)
        for target in reversed(created):
            if target.resolve().is_relative_to(box.pack.resolve()):shutil.rmtree(target)
        raise
    finally:box.release()
