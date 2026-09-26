run:
	python main.py

depens:
	uv sync

build:
	uv run pyinstaller --windowed --add-data "assets:assets" --onefile --name osu-gacha main.py
