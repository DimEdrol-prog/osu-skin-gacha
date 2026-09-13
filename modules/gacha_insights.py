"""Comparable score history, daily aggregates and session results."""
from datetime import datetime
from collections import Counter, defaultdict
import tkinter as tk
import json
from PIL import Image, ImageDraw, ImageTk
import customtkinter as ctk
from modules.gacha_rules import accuracy, mods_string
from modules.gacha_widgets import IconWindow, FastScrollableFrame


def text(app, ru, en):
    return en if app.settings['language']=='English' else ru


def timestamp(value):
    try: return datetime.fromisoformat(str(value).replace('Z','+00:00')).timestamp()
    except (ValueError,TypeError,OverflowError): return 0


def all_records(app):
    sessions=dict(app.history)
    if app.current_session:
        sessions[app.current_session['id']]=dict(app.current_session,records=list(app.records))
    result=[];seen=set()
    for session in sessions.values():
        if not app.session_matches(session):continue
        for index,r in enumerate(session.get('records',[])):
            key=json.dumps(r.get('key') or (session['id'],index),ensure_ascii=False)
            if key in seen:continue
            seen.add(key)
            when=timestamp(r['score'].get('date')) or timestamp(session.get('started_at'))+index*.0001
            result.append((when,r))
    return sorted(result,key=lambda row:row[0])


def comparison_index(rows):
    previous={};result={}
    for when,record in sorted(rows,key=lambda row:row[0]):
        score=record['score']
        key=(str(score.get('beatmap_id') or record['map'].get('beatmap_id')),mods_string(score.get('enabled_mods')))
        old=previous.get(key)
        if old and when>old[0]:
            before=old[1]['score']
            result[id(record)]=(int(score.get('maxcombo') or 0)-int(before.get('maxcombo') or 0),accuracy(score)-accuracy(before),int(score.get('countmiss') or 0)-int(before.get('countmiss') or 0))
        previous[key]=(when,record)
    return result


def comparison_text(app,record):
    delta=getattr(app,'comparison_cache',{}).get(id(record))
    if delta is None:return ''
    combo,acc,miss=delta
    return text(app,f'К прошлой попытке: {combo:+d} комбо · {acc:+.2f}% точности · {miss:+d} миссов',f'Previous play: {combo:+d} combo · {acc:+.2f}% accuracy · {miss:+d} misses')


def daily_rows(rows,hide_failed=False):
    groups=defaultdict(list)
    for when,r in rows:
        if not when or (hide_failed and r['score'].get('rank')=='F'):continue
        groups[datetime.fromtimestamp(when).strftime('%Y-%m-%d')].append(r['score'])
    result=[]
    for day,scores in sorted(groups.items()):
        pp=[float(s['pp']) for s in scores if s.get('pp') is not None]
        result.append(dict(date=day,count=len(scores),pp=max(pp) if pp else None,combo=max(int(s.get('maxcombo') or 0) for s in scores),accuracy=sum(accuracy(s) for s in scores)/len(scores)))
    return result


def chart_range(values,key):
    low,high=min(values),max(values)
    padding=max((high-low)*.12, .1 if key=='accuracy' else 1)
    return max(0,low-padding),min(100,high+padding) if key=='accuracy' else high+padding


def smooth_points(points,steps=18):
    """Smoothstep interpolation passes through samples without inventing extrema."""
    result=[]
    for (x0,y0),(x1,y1) in zip(points,points[1:]):
        for i in range(steps):
            t=i/steps;u=t*t*(3-2*t)
            result.extend((x0+(x1-x0)*t,y0+(y1-y0)*u))
    if points:result.extend(points[-1])
    return result


def result_card(app,parent,record):
    from modules.gacha_config import RANK_COLORS
    card=app.panel(parent);card.pack(fill='x',pady=7)
    app.cover_widget(card,record).pack(side='left',padx=12,pady=12)
    details=ctk.CTkFrame(card,fg_color='transparent');details.pack(side='left',fill='both',expand=True,padx=(0,12),pady=12)
    score,info=record['score'],record['map']
    title=f"{info.get('artist','')} — {info.get('title','')} [{info.get('version','')}]"
    app.label(details,title,bold=True,wraplength=450,justify='left',anchor='w').pack(fill='x')
    pp='—' if score.get('pp') is None else f"{float(score['pp']):.1f}"
    stats=text(app,f"Комбо: {score.get('maxcombo',0)} · Точность: {accuracy(score):.2f}% · Миссы: {score.get('countmiss',0)}",f"Combo: {score.get('maxcombo',0)} · Accuracy: {accuracy(score):.2f}% · Misses: {score.get('countmiss',0)}")
    app.label(details,stats,muted=True,wraplength=450,anchor='w').pack(fill='x',pady=6)
    app.label(details,f"{pp} PP · {mods_string(score.get('enabled_mods'))} · {float(info.get('difficultyrating') or 0):.2f}★",anchor='w').pack(fill='x')
    grade=app.label(card,score.get('rank','?'),size=26,bold=True,width=55);grade.configure(text_color=RANK_COLORS.get(score.get('rank'),app.theme['accent']));grade.pack(side='right',padx=12)
    return card


def open_day(app,day,hide_failed):
    win=IconWindow(app);win.title(day);win.geometry('850x660');win.configure(fg_color=app.theme['bg'])
    app.label(win,day,size=24,bold=True).pack(anchor='w',padx=20,pady=14)
    body=FastScrollableFrame(win,fg_color=app.theme['bg']);body.pack(fill='both',expand=True,padx=14,pady=8)
    records=[r for when,r in all_records(app) if datetime.fromtimestamp(when).strftime('%Y-%m-%d')==day and not(hide_failed and r['score'].get('rank')=='F')]
    records.sort(key=lambda r:float(r['score'].get('pp') or 0),reverse=True)
    app.label(body,text(app,'Скоры дня · лучшие по PP сверху. Нажмите обложку, чтобы открыть карту.','Daily scores · highest PP first. Click a cover to open its map.'),muted=True,wraplength=760).pack(pady=8)
    for record in records:result_card(app,body,record)
    return win


def open_progress(app):
    win=IconWindow(app);win.title(app.t('progress_view'));win.geometry('980x790');win.minsize(780,600);win.configure(fg_color=app.theme['bg'])
    app.label(win,app.t('progress_view'),size=25,bold=True).pack(anchor='w',padx=22,pady=(18,6))
    app.label(win,text(app,'Выбранные профиль и слот · PP и комбо — лучшие за день; точность — средняя. Состав карт может меняться.','Selected profile and slot · daily best PP and combo; mean accuracy. The maps played may vary.'),muted=True,wraplength=890,justify='left').pack(anchor='w',padx=22)
    bar=ctk.CTkFrame(win,fg_color='transparent');bar.pack(fill='x',padx=22,pady=12)
    metrics={text(app,'Лучший PP','Best PP'):'pp',text(app,'Лучшее комбо','Best combo'):'combo',text(app,'Средняя точность','Mean accuracy'):'accuracy',text(app,'Количество скоров','Score count'):'count'}
    periods={text(app,'30 дней','30 days'):30,text(app,'90 дней','90 days'):90,text(app,'Всё время','All time'):0}
    metric=tk.StringVar(value=next(iter(metrics)));period=tk.StringVar(value=list(periods)[-1]);hide=tk.BooleanVar(value=app.settings['hide_failed'])
    canvas=tk.Canvas(win,height=265,bg=app.theme['panel'],highlightthickness=0);canvas.pack(fill='x',padx=22)
    caption=app.label(win,'',muted=True);caption.pack(anchor='w',padx=22,pady=8)
    app.label(win,text(app,'Дни и изменения · нажмите строку для разбора скоров','Days and changes · click a row to explore scores'),bold=True).pack(anchor='w',padx=22,pady=6)
    table=FastScrollableFrame(win,fg_color=app.theme['bg']);table.pack(fill='both',expand=True,padx=14,pady=(0,16))
    for col,weight in enumerate((2,1,2,2)):table.grid_columnconfigure(col,weight=weight,uniform='daily')
    def value_text(value,key):
        if value is None:return '—'
        return f'{value:.2f}%' if key=='accuracy' else f'{value:.1f} PP' if key=='pp' else f'{value:.0f}'
    def redraw(*_):
        rows=daily_rows(all_records(app),hide.get());key=metrics[metric.get()]
        days=periods[period.get()]
        if days and rows:
            cutoff=timestamp(rows[-1]['date'])-(days-1)*86400
            rows=[r for r in rows if timestamp(r['date'])>=cutoff]
        for child in table.winfo_children():child.destroy()
        headings=[text(app,'Дата','Date'),text(app,'Скоров','Scores'),metric.get(),text(app,'К прошлому дню','Previous day')]
        for col,label in enumerate(headings):app.label(table,label,muted=True).grid(row=0,column=col,sticky='ew',padx=5,pady=8)
        previous=None;data=[]
        for row in rows:
            value=row[key];delta=value-previous if value is not None and previous is not None else None
            if value is not None:previous=value
            data.append((row,delta))
        for index,(row,delta) in enumerate(reversed(data),1):
            line=ctk.CTkFrame(table,fg_color=app.theme['panel'],corner_radius=10);line.grid(row=index,column=0,columnspan=4,sticky='ew',pady=3)
            for col,weight in enumerate((2,1,2,2)):line.grid_columnconfigure(col,weight=weight,uniform='daily')
            diff='—' if delta is None else (f'{delta:+.2f} '+text(app,'п.п.','pts') if key=='accuracy' else f'{delta:+.1f}' if key=='pp' else f'{delta:+.0f}')
            for col,label in enumerate((row['date'],str(row['count']),value_text(row[key],key),diff)):
                cell=app.label(line,label,height=34,cursor='hand2');cell.grid(row=0,column=col,sticky='ew',padx=5)
                if col==3 and delta and delta>0:cell.configure(text_color=app.theme['accent'])
                cell.bind('<Button-1>',lambda e,d=row['date']:open_day(app,d,hide.get()))
        canvas.delete('all');w=max(650,canvas.winfo_width());points=[(timestamp(r['date']),r[key],r['date']) for r in rows if r[key] is not None]
        if not points:
            caption.configure(text=text(app,'Пока нет данных','No data yet'));return
        ymin,ymax=chart_range([p[1] for p in points],key);xmin,xmax=points[0][0],points[-1][0]
        delta=points[-1][1]-points[0][1]
        caption.configure(text=text(app,f'За выбранный период: {delta:+.2f}'+(' п.п.' if key=='accuracy' else '')+' · точки — фактические значения, линия — плавное соединение.',f'Selected period: {delta:+.2f}'+(' pts' if key=='accuracy' else '')+' · dots are observations, line is a smooth connection.'))
        coords=[]
        for i in range(5):
            y=220-i*45;canvas.create_line(70,y,w-25,y,fill=app.theme['card']);canvas.create_text(60,y,text=f'{ymin+(ymax-ymin)*i/4:.1f}',anchor='e',fill=app.theme['muted'],font=('Segoe UI',10))
        for date,value,label in points:
            x=70+(date-xmin)/max(1,xmax-xmin)*(w-100) if xmax!=xmin else w/2
            y=220-(value-ymin)/max(.0001,ymax-ymin)*180;coords.append((x,y))
        if len(coords)>1:
            # Supersampling avoids Tk's jagged diagonal strokes at normal DPI.
            curve=smooth_points(coords);scale=3
            layer=Image.new('RGBA',(w*scale,265*scale))
            ImageDraw.Draw(layer).line([(curve[i]*scale,curve[i+1]*scale) for i in range(0,len(curve),2)],fill=app.theme['accent'],width=3*scale,joint='curve')
            canvas._line_image=ImageTk.PhotoImage(layer.resize((w,265),Image.Resampling.LANCZOS),master=canvas)
            canvas.create_image(0,0,anchor='nw',image=canvas._line_image)
        for (x,y),(_,value,label) in zip(coords,points):
            dot=canvas.create_oval(x-4,y-4,x+4,y+4,fill=app.theme['accent'],outline=app.theme['panel'],width=2)
            canvas.tag_bind(dot,'<Enter>',lambda e,l=label,v=value:caption.configure(text=l+' · '+value_text(v,key)+' · '+text(app,'Нажмите для просмотра скоров','Click to explore scores')))
            canvas.tag_bind(dot,'<Button-1>',lambda e,d=label:open_day(app,d,hide.get()))
        canvas.create_text(70,247,text=points[0][2],anchor='w',fill=app.theme['muted']);canvas.create_text(w-25,247,text=points[-1][2],anchor='e',fill=app.theme['muted'])
    for var,values in ((metric,metrics),(period,periods)):
        ctk.CTkOptionMenu(bar,variable=var,values=list(values),command=redraw,fg_color=app.theme['card'],button_color=app.theme['card'],text_color=app.theme['text'],dropdown_fg_color=app.theme['panel'],dropdown_text_color=app.theme['text']).pack(side='left',padx=(0,10))
    ctk.CTkCheckBox(bar,text=app.t('hide_failed'),variable=hide,command=redraw,fg_color=app.theme['accent'],checkmark_color=app.ink,text_color=app.theme['text']).pack(side='left',padx=8)
    app.button(bar,text(app,'Обновить','Refresh'),redraw,True).pack(side='right')
    canvas.bind('<Configure>',redraw);redraw()
    return win


def session_summary(session):
    records=session.get('records',[])
    elapsed=max(0,(timestamp(session.get('ended_at')) or datetime.now().timestamp())-timestamp(session.get('started_at')))
    complete=[r for r in records if r['score'].get('rank')!='F' and r['score'].get('pp') is not None]
    best=max(complete,key=lambda r:float(r['score']['pp']),default=None)
    drops=session.get('drops',[])
    return elapsed,records,best,drops,Counter(d.get('rank','?') for d in drops)


def open_summary(app,session=None):
    from modules.gacha_config import RANK_COLORS
    session=session or (app.history.get(app.selected_session) if app.selected_session else app.current_session)
    if not session:return
    if session is app.current_session:session=dict(session,records=list(app.records))
    elapsed,records,best,drops,counts=session_summary(session)
    win=IconWindow(app);win.title(app.t('summary'));win.geometry('860x790');win.minsize(760,540);win.configure(fg_color=app.theme['bg'])
    body=FastScrollableFrame(win,fg_color=app.theme['bg']);body.pack(fill='both',expand=True,padx=16,pady=16)
    hero=app.panel(body);hero.pack(fill='x',pady=(0,14))
    app.label(hero,app.t('summary'),size=28,bold=True).pack(anchor='w',padx=20,pady=(16,4))
    when=timestamp(session.get('started_at'));date=datetime.fromtimestamp(when).strftime('%d.%m.%Y · %H:%M') if when else '—'
    app.label(hero,f"{session.get('username') or app.username} · {date}",muted=True).pack(anchor='w',padx=20,pady=(0,12))
    stats=ctk.CTkFrame(hero,fg_color='transparent');stats.pack(fill='x',padx=12,pady=(0,14))
    elapsed_label=f'{int(elapsed)//3600:02d}:{int(elapsed)//60%60:02d}:{int(elapsed)%60:02d}'
    gain=session.get('end_pp',0)-session.get('start_pp',0) if 'start_pp' in session else None
    metrics=[(text(app,'Длительность','Duration'),elapsed_label),(text(app,'Скоров','Scores'),str(len(records))),(text(app,'Новых скинов','New skins'),str(len(drops))),(text(app,'Прирост профиля','Profile change'),'—' if gain is None else f'{gain:+.2f} PP')]
    for col,(label,value) in enumerate(metrics):
        stats.grid_columnconfigure(col,weight=1,uniform='summary')
        tile=ctk.CTkFrame(stats,fg_color=app.theme['card'],corner_radius=12);tile.grid(row=0,column=col,sticky='nsew',padx=4)
        app.label(tile,value,size=22,bold=True).pack(padx=8,pady=(12,4))
        app.label(tile,label,muted=True,size=11).pack(padx=8,pady=(0,12))
    app.label(body,text(app,'Лучший пройденный скор по PP','Best passed score by PP'),size=18,bold=True).pack(anchor='w',padx=4)
    if best:result_card(app,body,best)
    else:app.label(body,text(app,'Пока нет пройденного скора с известным PP','No passed score with known PP yet'),muted=True).pack(anchor='w',pady=12)
    app.label(body,text(app,'Трофеи сессии','Session rewards'),size=20,bold=True).pack(anchor='w',padx=4,pady=(18,8))
    badges=ctk.CTkFrame(body,fg_color='transparent');badges.pack(fill='x',pady=6)
    for rank,count in counts.items():
        label=text(app,'Особая','Special') if rank=='special' else rank
        badge=app.label(badges,f'{label} × {count}',bold=True,fg_color=app.theme['card'],corner_radius=10,height=32,width=80)
        badge.configure(text_color=RANK_COLORS.get(rank,app.theme['accent']));badge.pack(side='left',padx=4)
    grid=ctk.CTkFrame(body,fg_color='transparent');grid.pack(fill='x')
    for col in range(3):grid.grid_columnconfigure(col,weight=1,uniform='reward')
    for index,drop in enumerate(drops):
        card=app.panel(grid);card.grid(row=index//3,column=index%3,sticky='nsew',padx=4,pady=6)
        image=app.label(card,text(app,'Нет превью','No preview'),height=117,width=208,muted=True);image.pack(padx=8,pady=8)
        item=app.drops.get(drop.get('id'),drop)
        entry=next((v for v in app.catalog.values() if (item.get('source') and v.get('source')==item['source']) or v.get('name')==drop.get('name')),item)
        cache=app.preview_cache;app.submit(app.images,'collection_image',lambda w=image,i=entry,c=cache:(w,c.get(i)))
        rank=drop.get('rank','?');label=text(app,'Особая','Special') if rank=='special' else rank
        badge=app.label(card,label,bold=True);badge.configure(text_color=RANK_COLORS.get(rank,app.theme['accent']));badge.pack()
        app.label(card,drop.get('name',''),wraplength=205,height=55,bold=True,justify='center').pack(fill='x',padx=8,pady=(0,8))
    if not drops:app.label(body,text(app,'В этой сессии пока нет новых скинов. Каждый следующий скор — новая попытка!','No new skins in this session yet. Every next score is another attempt!'),muted=True,wraplength=720).pack(pady=18)
    if 'drops' not in session:app.label(body,text(app,'В старой сессии список скинов не сохранялся.','Older sessions did not save their skin list.'),muted=True).pack(pady=8)
    return win
