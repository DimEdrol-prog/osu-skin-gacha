"""Editable credits; avatars use the app's background image loader."""
import webbrowser
import customtkinter as ctk

TEAM = [
    ('DimEl', '18086030', 'Главный разработчик', 'Lead developer'),
    ('anastasena', '24754751', 'Дизайнер', 'Designer'),
    ('naru', '31129671', 'Плейтестер', 'Playtester'),
    ('scoleopa', '40306760', 'Плейтестер', 'Playtester'),
]


def build_team(window, body):
    app = window.app
    english = app.settings['language']=='English'
    app.label(body,'Команда osu!gacha' if not english else 'osu!gacha team',size=22,bold=True).pack(anchor='w',pady=14)
    for name, ident, ru, en in TEAM:
        row = ctk.CTkFrame(body,fg_color=app.theme['panel'])
        row.pack(fill='x',pady=7)
        avatar = app.label(row,name[:1],width=64,height=64,size=24)
        avatar.pack(side='left',padx=14,pady=14)
        text = ctk.CTkFrame(row,fg_color='transparent')
        text.pack(side='left',fill='x',expand=True)
        app.label(text,name,size=18,bold=True).pack(anchor='w')
        app.label(text,en if english else ru,muted=True).pack(anchor='w')
        app.button(row,'Profile' if english else 'Профиль',lambda i=ident:webbrowser.open('https://osu.ppy.sh/users/'+i),True).pack(side='right',padx=14)
        key = ('bancho',ident,app.settings['ignore_proxy'])
        if key in app.avatar_cache:
            set_avatar(app,avatar,key,app.avatar_cache[key])
        elif not app.settings['offline']:
            def fetch(widget=avatar, ident=ident):
                key,picture=app.fetch_avatar(ident,app.settings['ignore_proxy'],'bancho')
                return widget,key,picture
            app.submit(app.network,'team_avatar',fetch)


def set_avatar(app, widget, key, picture):
    if picture is None: return
    app.avatar_cache[key] = picture
    if widget.winfo_exists():
        image = ctk.CTkImage(light_image=picture,dark_image=picture,size=(64,64))
        widget.configure(image=image,text='')
        widget.avatar = image
