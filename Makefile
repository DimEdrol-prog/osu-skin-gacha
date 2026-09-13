.PHONY: run fix-imports install clean shell

run:
	python3 main.py

install:
	pip install -r requirements.txt && pyinstaller --onefile main.py

clean:
	find . -type d -name "__pycache__" -exec rm -r {} +
	find . -type f -name "*.pyc" -delete
