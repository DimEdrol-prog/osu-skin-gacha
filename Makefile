.PHONY: run fix-imports install clean shell

run:
	python3 main.py

install:
	python3 -m pip install -r requirements.txt && python3 -m PyInstaller --hidden-import=customtkinter --hidden-import=requests --hidden-import=Pillow --hidden-import=beautifulsoup4 --hidden-import=rosu-pp-py --hidden-import=pygame-ce --onefile main.py

clean:
	find . -type d -name "__pycache__" -exec rm -r {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .venv && rm -rf build && rm -rf dist && rm -rf __pycache__
