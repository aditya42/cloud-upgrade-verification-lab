.PHONY: install lint unit build kind-up e2e verify clean

install:
	python -m pip install -e '.[dev]'

lint:
	ruff check app tests

unit:
	pytest -q tests/unit

build:
	./scripts/build-releases.sh

kind-up: build
	./scripts/kind-up.sh

e2e:
	pytest -m e2e -v tests/e2e

verify:
	./scripts/run-upgrade-verification.sh

clean:
	./scripts/kind-down.sh || true
	docker compose down -v || true
