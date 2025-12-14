.PHONY: install index serve token
install:
	python -m venv .venv && .venv/bin/pip install -e .
index:
	python -m support.kb
serve:
	uvicorn support.api:app --port 8020
token:
	@python -m support.session $(or $(C),cus_001)
