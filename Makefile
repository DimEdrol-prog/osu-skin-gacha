.PHONY: run fix-imports install clean shell

run:
	python3 main.py

install:
	python3 -m pip install -r requirements.txt && python3 -m PyInstaller --onefile main.py

clean:
	find . -type d -name "__pycache__" -exec rm -r {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .venv && rm -rf build && rm -rf dist && rm -rf __pycache__
