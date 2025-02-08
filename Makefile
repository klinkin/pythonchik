
VERSION = $(shell poetry version -s)
PROJECT_PATH := pythonchik

help:
	@echo "make build 		- Build a docker image"
	@echo "make lint 		- Syntax check"
	@echo "make test 		- Test this project"
	@echo "make format 		- Format project with ruff and black"
	@echo "make upload 		- Upload this project to the docker-registry"
	@echo "make clean 		- Remove files which creates by distutils"
	@echo "make purge 		- Complete cleanup the project"
	@echo "make exe 		- Build Windows executable"
	@echo "make app 		- Build macOS application"
	@exit 0

wheel:
	poetry build -f wheel
	poetry export -f requirements.txt -o dist/requirements.txt

build: clean wheel
	docker build -t $(CI_REGISTRY_IMAGE):$(DOCKER_TAG) --target release .

clean:
	rm -fr dist build *.spec

clean-pyc:
	find . -iname '*.pyc' -delete

lint:
	poetry run mypy $(PROJECT_PATH)
	poetry run ruff check $(PROJECT_PATH) tests
	poetry run black --check $(PROJECT_PATH)

format:
	poetry run black $(PROJECT_PATH) tests
	poetry run ruff format $(PROJECT_PATH) tests
	poetry run ruff check --fix --select I $(PROJECT_PATH) tests

purge: clean
	rm -rf ./.venv

test:
	poetry run pytest

local:
	docker-compose -f docker-compose.dev.yml up --force-recreate --renew-anon-volumes --build

pytest-ci:
	poetry run pytest -v --cov $(PROJECT_PATH) --cov-report term-missing --disable-warnings --junitxml=report.xml
	poetry run coverage xml

upload: build
	docker push $(CI_REGISTRY_IMAGE):$(DOCKER_TAG)

run_original:
	poetry run python -m pythonchik.main_original

run:
	poetry run python -m pythonchik.main

develop: clean
	poetry -V
	poetry install
	poetry run pre-commit install
	poetry add --group dev pyinstaller

exe:
	poetry run pyinstaller --clean --onefile --name pythonchik --add-data "$(PROJECT_PATH):$(PROJECT_PATH)" $(PROJECT_PATH)/main.py

app:
	poetry run pyinstaller --clean --onefile --name pythonchik --add-data "$(PROJECT_PATH):$(PROJECT_PATH)" --noconsole $(PROJECT_PATH)/main.py

bump-doc: clean
	rm -rf docs/build
	mkdir docs/build
	echo version: `poetry version -s | tr '+' '-'` > docs/build/version.yaml

lint-doc: bump-doc
	docker run -v `pwd`/docs:/mnt -w /mnt --rm registry.edadeal.yandex-team.ru/dockers/redoc:latest lint api.yaml

lint-doc-ci:
	redoc-cli lint docs/api.yaml
