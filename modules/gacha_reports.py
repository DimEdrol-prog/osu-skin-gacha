"""Public GitHub feedback: browser-confirmed submission and read-only inbox."""
from datetime import datetime
from pathlib import Path
import re
import tkinter as tk
from tkinter import filedialog, messagebox
from urllib.parse import urlencode
import webbrowser
import customtkinter as ctk
from modules.gacha_sources import session_for
from modules.gacha_storage import atomic_json
from modules.gacha_widgets import IconWindow, FastTextbox, FastScrollableFrame

REPOSITORY = 'DimEdrol-prog/osu-skin-gacha'
REPOSITORY_URL = 'https://github.com/' + REPOSITORY


def redact(text, secret=''):
    if secret:
        text = text.replace(secret, '***')
    return re.sub(r'(?i)((?:api[_-]?key|access_token|authorization|[?&]k)\s*[=:]\s*)[^\s&]+', r'\1***', text)


def report_body(description, logs=(), secret=''):
    import html
    body='osu! Skin Gacha beta4\n\n'+description.strip()
    if logs:
        body+='\n\n<details>\n<summary>Логи / Logs — развернуть / expand</summary>\n\n<pre>'+html.escape(redact('\n'.join(logs),secret))+'</pre>\n</details>'
    return redact(body,secret)



def report_parts(body):
    import html
    match=re.search(r'<details>\s*<summary>.*?</summary>\s*<pre>(.*?)</pre>\s*</details>',body,re.S)
    if not match:return body,None
    return body[:match.start()]+body[match.end():],html.unescape(match[1])


def fetch_reports(ignore_proxy=False):
    with session_for(ignore_proxy) as session:
        response = session.get('https://api.github.com/repos/' + REPOSITORY + '/issues',
                               params={'state': 'all', 'sort': 'created', 'direction': 'desc', 'per_page': 100},
                               timeout=(12, 25), headers={'Accept': 'application/vnd.github+json'})
        response.raise_for_status()
        rows = response.json()
        if not isinstance(rows, list):
            raise ValueError('GitHub returned an invalid issue list')
        return [dict(number=int(r['number']), title=str(r['title']), body=str(r.get('body') or ''),
                     state=str(r.get('state', 'open'))) for r in rows if 'pull_request' not in r]


class ReportsMixin:
    def report_text(self,ru,en):
        return en if self.settings["language"]=="English" else ru

    def report_bug(self):
        window = IconWindow(self)
        window.title(self.t('report_bug'))
        window.geometry('720x580')
        window.configure(fg_color=self.theme['bg'])
        self.label(window, self.report_text('Опишите проблему и шаги повторения','Describe the problem and steps'),
                   wraplength=660).pack(padx=18, pady=12)
        field = FastTextbox(window, fg_color=self.theme['panel'], text_color=self.theme['text'])
        field.pack(fill='both', expand=True, padx=18, pady=8)
        include = tk.BooleanVar(value=False)
        ctk.CTkCheckBox(window, text=self.report_text('Приложить логи','Include logs'), variable=include).pack(pady=8)
        self.label(window, self.report_text('Отчёт будет публичным. На GitHub проверьте текст и нажмите Create. Нужен аккаунт GitHub.', 'Reports are public. Review and submit on GitHub with your account.'), wraplength=660).pack(padx=18, pady=8)

        def body():
            description = field.get('1.0', 'end').strip()
            return report_body(description, list(self.logs) if include.get() else (),
                               self.settings.get('api_key', '')) if description else ''

        def send():
            text = body()
            if not text:
                return
            # A full report stays available even when too long for a browser URL.
            self.clipboard_clear()
            self.clipboard_append(text)
            draft = text if len(text.encode('utf-8')) <= 1200 else (
                self.report_text('Полный отчёт скопирован. Вставьте его сюда через Ctrl+V перед отправкой.', 'The full report is copied. Paste it here with Ctrl+V before submitting.'))
            webbrowser.open(REPOSITORY_URL + '/issues/new?' + urlencode({'title': 'Ошибка в osu! Skin Gacha', 'body': draft}))

        def save():
            text = body()
            if not text:
                return
            path = filedialog.asksaveasfilename(parent=window, defaultextension='.json',
                                               initialfile='gacha-bug-report.json', filetypes=[('JSON', '*.json')])
            if path:
                try:
                    atomic_json(Path(path), {'created_at': datetime.now().astimezone().isoformat(), 'body': text})
                except OSError as error:
                    messagebox.showerror(self.t('error'), str(error), parent=window)
        self.button(window, self.report_text('Отправить через GitHub','Open GitHub report'), send).pack(pady=6)
        self.button(window, self.report_text('Сохранить в файл','Save to file'), save).pack(pady=(0, 12))

    def check_reports(self):
        if self.closing or getattr(self, 'reports_loading', False):
            return
        self.reports_loading = True
        self.submit(self.network, 'reports', fetch_reports, self.settings.get('ignore_proxy', False))

    def receive_reports(self, rows):
        self.reports_loading = False
        self.report_rows = rows
        newest = max((r['number'] for r in rows), default=0)
        seen = int(self.settings.get('reports_seen', 0))
        new = sum(r['number'] > seen for r in rows)
        opened = getattr(self, 'reports_window', None)
        if opened and opened.winfo_exists():
            self.render_reports()
            self.settings['reports_seen'] = newest
            self.store.save(self.settings)
            new = 0
        self.reports_button.configure(text=f"{self.t('reports')} ({new})" if new else self.t('reports'))
        if new:
            self.log(f'Новые отчёты / New reports: {new}. Откройте «Отзывы» / Open Reports.')

    def report_error(self, error):
        self.reports_loading = False
        window = getattr(self, 'reports_window', None)
        if window and window.winfo_exists():
            self.reports_status.configure(text='Не удалось прочитать GitHub. Нажмите «Обновить».\n' + str(error))

    def open_reports(self):
        window = getattr(self, 'reports_window', None)
        if window and window.winfo_exists():
            window.lift()
            return
        window = self.reports_window = IconWindow(self)
        window.title(self.t('reports')+' — GitHub Issues')
        window.geometry('800x620')
        window.configure(fg_color=self.theme['bg'])
        self.reports_status = self.label(window, self.report_text('Загрузка','Loading…'), wraplength=740)
        self.reports_status.pack(padx=18, pady=12)
        self.button(window, self.report_text('Обновить','Refresh'), self.check_reports).pack(pady=4)
        self.reports_list = FastScrollableFrame(window, fg_color=self.theme['panel'])
        self.reports_list.pack(fill='both', expand=True, padx=18, pady=12)
        self.check_reports()

    def render_reports(self):
        for child in self.reports_list.winfo_children():
            child.destroy()
        rows = self.report_rows
        self.reports_status.configure(text=self.report_text(f'Последние отчёты: {len(rows)} (до 100)',f'Latest reports: {len(rows)} (up to 100)'))
        for row in rows:
            number = row['number']
            self.button(self.reports_list, f'#{number} [{row["state"]}] {row["title"][:90]}',
                        lambda n=number: webbrowser.open(REPOSITORY_URL + f'/issues/{n}')).pack(fill='x', pady=5)
            description,logs=report_parts(row['body'])
            self.label(self.reports_list,description[:700],wraplength=690,justify='left').pack(fill='x',padx=8,pady=(0,12))
            if logs is not None:
                container=ctk.CTkFrame(self.reports_list,fg_color='transparent');container.pack(fill='x',pady=(0,12))
                field=FastTextbox(container,height=180,fg_color=self.theme['card'],text_color=self.theme['text'])
                field.insert('1.0',logs);field.configure(state='disabled')
                button=self.button(container,self.report_text('▸ Развернуть логи','▸ Expand logs'),lambda:None,True);button.pack(anchor='w')
                def toggle(f=field,b=button):
                    opened=bool(f.winfo_manager())
                    if opened:f.pack_forget()
                    else:f.pack(fill='x',pady=8)
                    b.configure(text=self.report_text('▸ Развернуть логи','▸ Expand logs') if opened else self.report_text('▾ Свернуть логи','▾ Collapse logs'))
                button.configure(command=toggle)
