.PHONY: bootstrap backend frontend demo test ui app

bootstrap:
	python3 bootstrap.py

backend:
	python3 -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload

frontend:
	cd frontend && npm run dev

ui:
	cd frontend && npm install && npm run build

app: bootstrap ui
	python3 desktop.py

demo: app

test:
	PYTHONPATH=. python3 tests/test_cycle.py
	PYTHONPATH=. python3 tests/test_intent.py
