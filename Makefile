.PHONY: bootstrap backend frontend demo test

bootstrap:
	python3 bootstrap.py

backend:
	python3 -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload

frontend:
	cd frontend && npm run dev

demo: bootstrap
	@echo "Start backend: make backend"
	@echo "Start frontend: make frontend"

test:
	PYTHONPATH=. python3 tests/test_cycle.py
	PYTHONPATH=. python3 tests/test_intent.py
