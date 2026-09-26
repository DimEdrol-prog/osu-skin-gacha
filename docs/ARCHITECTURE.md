# Модули osu! Skin Gacha

## В корне проекта
- main.py - импорт модулей.
- skin_gacha.py - запуск приложения и совместимые экспорты для тестов.
- gacha_app.py - главное окно, мастер первого запуска, сессии, очередь событий.
- gacha_config.py - значения по умолчанию, переводы, темы, пороги.
- gacha_storage.py - атомарная запись настроек и истории.
- gacha_rules.py - расчёт ранга награды, комбо/pp, моды, ссылки на скоры.
- gacha_skins.py - коллекция, избранное, установка, журнал переноса и восстановление.
- gacha_api.py - совместимый Legacy-клиент и обложки карт.
- gacha_api_v2.py - действующий Bancho API v2 через Worker, адаптер профилей и скоров.
- gacha_oauth.py - браузерный вход и защищённая сессия приложения.
- gacha_sources.py - Drive/ZIP/папки, локальные карты и pp, Offline/Gatari.
- gacha_previews.py - кэш превью Drive, фоновая загрузка и плавная лента рулетки.
- gacha_driver.py - запуск выбранного пользователем драйвера планшета и сворачивание его окна.
- gacha_team.py - состав команды, аватарки и ссылки на профили.
- gacha_widgets.py - общие виджеты.
- gacha_settings.py - окно настроек и пояснения.
- gacha_setup.py - мастер первого запуска.
- gacha_reports.py - форма отчёта и публичные GitHub Issues; токен GitHub не нужен.
- gacha_bootstrap.py - установка и проверка локального окружения Python.
- gacha_insights.py - сравнение одинаковых сложностей/модов, дневные агрегаты, график и итоги сессии.
- gacha_transfer.py - архив пользовательских данных всех слотов.

## В oauth_worker/
- /desktop/start: создание входа с SHA-256 challenge.
- /login и /oauth/callback: официальный Authorization Code Grant; state и cookie привязывают ответ к браузеру.
- /desktop/poll: результат доступен только создателю verifier.
- /session: проверка сессии osu!gacha и данные пользователя.
- /logout: аннулирование только этой сессии, сессия сайта остаётся отдельной.
- /api/v2/*: разрешённые запросы к osu! выполняет Worker, включая обновление истёкших токенов.

## beta4, 13.09.2026
- gacha_updates.py: краткий двуязычный CHANGELOG, поиск сессий, анимация PP.
  Каждую следующую итерацию дополнять CHANGELOG краткими пунктами.
- Hard получает позицию текущего результата через API.leaderboard; строго
  playcount > 1000 на выбранном сервере. Личный PP-топ больше не определяет награды.
- F запрещён во всех режимах. claimed_ranks хранит максимальную выданную
  обычную награду по сложности в истории профиля/сервера/слота; DT отдельно.
- Удаление неизбранных доступно только по явной настройке и подтверждению;
  текущий неактивный слот, проверка всех путей и запрет reparse points.
- График: диапазон по данным, smoothstep без выбросов, значения дней и их
  изменения, переход к исходным скорам. Итоги включают обложку и превью наград.
- Регрессии: tests.test_gacha_beta4_iteration + test_gacha_features_ui.


## beta4 - музыка и навигация
- gacha_audio.py: AudioFilename из локального .osu (индекс osu!.db или
  каталог Songs/<set_id>), пути внутри папки карты, pygame-ce/SDL_mixer,
  один поток аудио, загрузка в отдельном executor. Кнопка в cover_widget
  распространяется на все виды карточек. Закрытие владельца/приложения
  останавливает поток и освобождает аудиофайл.
- gacha_connection.py: отметки реальных запросов, идентичность
  server/user/API/offline для отсечения старых ответов, ручная проверка.
  Таймер обновляет только текст времени и не обращается в сеть.
- Поиск настроек: отдельная стрелка сворачивания и ссылка-заголовок категории.
- gacha_previews.open_preview общий для рулетки и коллекции.
- CHANGELOG дополнен 78 пунктами по истории переписки; будущие пункты
  добавлять в начало, сохраняя доступ к прошлым разделам.
- Дополнительная регрессия: test_gacha_music_connection.


## beta4 Harmony (2026-09-13)
- gacha_polish: release names and manual update guidance. Scaling uses Tk
  idle redraws; native WM_SETREDRAW was removed because it delayed updates.
- Audio: first direct .osu/set-folder lookup, then database fallback. One
  worker and stream; mutagen reads duration without decoding entire tracks.
  Persistent sidebar transport, seek offset, shared volume; card destruction
  does not stop playback. Cover controls have a solid themed toolbar.
- Fun uses a capped logarithmic star curve; Medium a capped sublinear PP
  curve. reward_scale applies only to custom requirements; Hard ranks scale
  inversely. Fresh custom settings seed from the current profile's defaults.
- Downloads retry transient errors three times, reset partial files and
  validate Content-Length plus ZIP signature before atomic replacement.
- Live skin recovery recognizes both localized marker-owned names. A
  language change runs in the serial file queue under the existing lock.
- Map progress compares the same difficulty; per-attempt deltas stay within
  matching mods. Chart resize rebuilds are debounced.
- Garbage collections remain on the UI thread: young generation every 15s,
  generation 1 every minute and full collection every two minutes.


### Harmony usability follow-up
- Player distinguishes paused/stopped/hidden states; only × hides its panel.
- ensure_live prepares a marker-owned, default-backed skin under the file lock
  when a valid game folder is configured. Existing rewards remain untouched.
- Right-click labels opens Copy / Select text. The wizard URL is a read-only
  Entry with an explicit copy button. Password/API entry behaviour is unchanged.
- Reward scale is 0.5–2; Hard placement thresholds remain within the API top 100.
- Score rank badges are right-anchored, independent of score-link presence.



## v0.4.3 standalone
- Direct entry: skin_gacha.py. No sibling application imports.
- gacha_skin_variants.py rebuilds the managed current skin from its original source.
- gacha_skin_stats.py records confirmed reload transitions and aggregates associated scores.
