"""Collection browser. Workers load only PIL images; Tk images stay on the UI thread."""
import tkinter as tk
from tkinter import messagebox
from datetime import datetime, timedelta
import customtkinter as ctk
from modules.gacha_widgets import IconWindow, FastScrollableFrame
from modules.gacha_config import RANK_COLORS
from modules.gacha_skin_apply import apply_collection
from modules.gacha_previews import open_preview


def words(app, ru, en):
    return en if app.settings['language']=='English' else ru


def filter_drops(drops, query='', rank='', favorites=False, days=0, order='new'):
    cutoff = (datetime.now().astimezone()-timedelta(days=days)).timestamp() if days else None
    result=[]
    for ident, item in drops.items():
        if query.casefold() not in item.get('name','').casefold(): continue
        if rank and item.get('rank')!=rank: continue
        if favorites and not item.get('favorite'): continue
        try: date=datetime.fromisoformat(item.get('unlocked_at','')).timestamp()
        except (ValueError,TypeError): date=0
        if cutoff and date<cutoff: continue
        result.append((ident,item,date))
    result.sort(key=lambda row: row[1].get('name','').casefold() if order=='name' else row[2], reverse=order=='new')
    return [(ident,item) for ident,item,_ in result]


class CollectionWindow(IconWindow):
    def __init__(self, app):
        super().__init__(app)
        self.app=app
        self.title(app.t('collection'))
        self.geometry('960x740'); self.minsize(660,450)
        self.configure(fg_color=app.theme['bg'])
        self.query=tk.StringVar(); self.rank=tk.StringVar(value=words(app,'Все ранги','All ranks'))
        self.favorite=tk.BooleanVar(); self.period=tk.StringVar(value=words(app,'За всё время','All time'))
        self.order=tk.StringVar(value=words(app,'Сначала новые','Newest first'))
        self.timer=None; self.page=0; self.revision=0; self.columns=3; self.resize_timer=None
        app.label(self,app.t('collection'),size=23,bold=True).pack(anchor='w',padx=20,pady=(18,8))
        app.label(self,words(app,'Примените скин, затем нажмите Ctrl+Shift+Alt+S в osu!. В игре должен быть выбран «! osu!gacha — Текущий скин».','Apply a skin, then press Ctrl+Shift+Alt+S in osu!. Select “! osu!gacha — Текущий скин” in the game.'),muted=True,wraplength=860,justify='left').pack(fill='x',padx=20)
        app.label(self,words(app,'Поиск по названию','Search by name'),muted=True).pack(anchor='w',padx=20,pady=(8,0))
        bar=ctk.CTkFrame(self,fg_color='transparent'); bar.pack(fill='x',padx=20,pady=12)
        ctk.CTkEntry(bar,textvariable=self.query,placeholder_text=words(app,'Название скина','Skin name')).pack(side='left',fill='x',expand=True,padx=(0,12))
        ctk.CTkCheckBox(bar,text=words(app,'Только избранные','Favorites only'),variable=self.favorite,command=self.reset).pack(side='right')
        filters=ctk.CTkFrame(self,fg_color='transparent'); filters.pack(fill='x',padx=20)
        self.periods={words(app,'За всё время','All time'):0,words(app,'За 24 часа','Last 24 hours'):1,words(app,'За 7 дней','Last 7 days'):7,words(app,'За 30 дней','Last 30 days'):30}
        self.orders={words(app,'Сначала новые','Newest first'):'new',words(app,'Сначала старые','Oldest first'):'old',words(app,'По названию','By name'):'name'}
        self.rank_options={self.rank.get():'',**{r:r for r in ('SS','S','A','B','C','D','DT')},words(app,'Особая','Special'):'special'}
        for var,values in [(self.rank,list(self.rank_options)),(self.period,list(self.periods)),(self.order,list(self.orders))]:
            ctk.CTkOptionMenu(filters,variable=var,values=values,command=lambda _:self.reset(),fg_color=app.theme['card'],button_color=app.theme['card'],text_color=app.theme['text'],width=175).pack(side='left',padx=(0,8))
        self.cleanup=app.button(self,words(app,'Удалить неизбранные','Remove nonfavorites'),self.delete_nonfavorites,True)
        self.count=app.label(self,'',muted=True);self.count.pack(anchor='w',padx=20,pady=8)
        self.body=FastScrollableFrame(self,fg_color=app.theme['bg']);self.body.pack(fill='both',expand=True,padx=12,pady=(0,12))
        footer=ctk.CTkFrame(self,fg_color='transparent');footer.pack(fill='x',padx=20,pady=8)
        app.button(footer,'←',lambda:self.turn(-1),True).pack(side='left')
        self.page_label=app.label(footer,'');self.page_label.pack(side='left',expand=True)
        app.button(footer,'→',lambda:self.turn(1),True).pack(side='right')
        self.body._parent_canvas.bind('<Configure>',self.resize_grid,add='+')
        self.query.trace_add('write',lambda *_:self.debounce())
        self.refresh()

    def resize_grid(self,event):
        columns=max(1,min(4,int(event.width/(245*self.body._get_widget_scaling()))))
        if columns!=self.columns:
            self.columns=columns
            if self.resize_timer:self.after_cancel(self.resize_timer)
            self.resize_timer=self.after(180,self.refresh)

    def debounce(self):
        if self.timer: self.after_cancel(self.timer)
        self.timer=self.after(200,self.reset)

    def reset(self):
        self.timer=None;self.page=0;self.refresh();self.body._parent_canvas.yview_moveto(0)

    def turn(self, delta):
        self.page=max(0,min(self.pages-1,self.page+delta));self.refresh();self.body._parent_canvas.yview_moveto(0)

    def refresh(self):
        self.resize_timer=None
        app=self.app;self.revision+=1
        self.cleanup.pack_forget()
        if app.settings.get('allow_skin_delete'):
            self.cleanup.pack(fill='x',padx=20,pady=6,before=self.count)
            self.cleanup.configure(state='normal' if app.state_name=='idle' and not app.applying_skin else 'disabled')
        for w in self.body.winfo_children(): w.destroy()
        rank=self.rank_options.get(self.rank.get(),'')
        items=filter_drops(app.drops,self.query.get(),rank,self.favorite.get(),self.periods[self.period.get()],self.orders[self.order.get()])
        self.pages=max(1,(len(items)+11)//12);self.page=min(self.page,self.pages-1)
        self.count.configure(text=words(app,f'Найдено: {len(items)}',f'Found: {len(items)}'))
        self.page_label.configure(text=f'{self.page+1} / {self.pages}')
        for col in range(4):self.body.grid_columnconfigure(col,weight=1 if col<self.columns else 0,uniform='skins' if col<self.columns else '',minsize=0)
        if not items: app.label(self.body,words(app,'Нет подходящих скинов','No matching skins'),muted=True).grid(row=0,column=0,columnspan=self.columns,pady=40)
        for n,(ident,item) in enumerate(items[self.page*12:(self.page+1)*12]):
            card=app.panel(self.body);card.grid(row=n//self.columns,column=n%self.columns,sticky='nsew',padx=5,pady=5)
            apply=app.button(card,words(app,'Применить','Apply'),lambda i=ident:self.apply(i))
            apply.pack(fill='x',padx=8,pady=8)
            if app.state_name not in ('idle','running') or app.applying_skin: apply.configure(state='disabled')
            picture=app.label(card,words(app,'Нет превью','No preview'),height=117,width=208,muted=True)
            picture.pack(padx=8)
            entry=next((v for v in app.catalog.values() if v.get('source')==item.get('source')),item)
            cache=app.preview_cache
            picture.configure(cursor='hand2')
            picture.bind('<Button-1>',lambda e,w=picture,i=entry,c=cache:open_preview(self,dict(item=i,image=getattr(w,'_preview_pil',None),path=c.path(i))))
            app.submit(app.images,'collection_image',lambda w=picture,i=entry,c=cache:(w,c.get(i)))
            app.label(card,item['name'],bold=True,wraplength=215,height=54).pack(fill='x',padx=8,pady=4)
            badge=app.label(card,('★  ' if item.get('favorite') else '')+(words(app,'Особая','Special') if item.get('rank')=='special' else item.get('rank','?')),bold=True)
            badge.configure(text_color=RANK_COLORS.get(item.get('rank'),app.theme['accent']));badge.pack()
            try: date=datetime.fromisoformat(item.get('unlocked_at','')).strftime('%d.%m.%Y %H:%M')
            except (ValueError,TypeError): date='—'
            app.label(card,date,size=10,muted=True).pack()
            app.button(card,app.t('unfavorite' if item.get('favorite') else 'favorite'),lambda i=ident,v=not item.get('favorite'):app.submit(app.files,'favorites',app.library.favorite,i,v),True).pack(fill='x',padx=8,pady=6)
            export=app.button(card,app.t('export_skin'),lambda i=ident:app.export_favorite(i),True);export.pack(fill='x',padx=8,pady=(0,8))
            if app.state_name!='idle' or not item.get('favorite'):export.configure(state='disabled')

    def apply(self, ident):
        app=self.app
        if app.applying_skin or app.state_name not in ('idle','running'): return
        app.applying_skin=True
        app.status_label.configure(text=words(app,'Применение скина…','Applying skin…'))
        app.submit(app.files,'skin_applied',apply_collection,app.library,ident)
        self.refresh()

    def delete_nonfavorites(self):
        app=self.app
        if not app.settings.get('allow_skin_delete') or app.state_name!='idle' or app.applying_skin:return
        count=sum(not item.get('favorite') for item in app.drops.values())
        if not count:return
        explanation=words(app,f'Удалить {count} неизбранных скинов из текущего слота?\n\nИзбранное, личные скины osu!, их экспортированные копии и история останутся. Удалённые награды смогут выпасть снова.',f'Remove {count} nonfavorite skins from the current slot?\n\nFavorites, personal osu! skins, exported copies and history are kept. Removed rewards may drop again.')
        if not messagebox.askyesno(words(app,'Удаление скинов','Remove skins'),explanation,parent=self):return
        app.state_name='resetting';app.update_controls();self.refresh()
        app.submit(app.files,'skins_deleted',app.library.delete_nonfavorites)
