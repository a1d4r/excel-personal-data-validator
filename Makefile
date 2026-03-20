#* Variables
SHELL := /usr/bin/env bash -o pipefail
PYTHON := python3

#* Directories with source code
CODE = excel_personal_data_validator tests
TESTS = tests

#* uv package manager
.PHONY: uv-install
uv-install:
	curl -LsSf https://astral.sh/uv/install.sh | sh

#* Installation
.PHONY: install
install:
	uv sync

.PHONY: pre-commit-install
pre-commit-install:
	uv run pre-commit install

#* Formatters
.PHONY: codestyle
codestyle:
	uv run ruff format $(CODE)
	uv run ruff check $(CODE) --fix-only

.PHONY: format
format: codestyle

#* Test
.PHONY: test
test:
	uv run pytest
	uv run coverage xml

# Validate dependencies
.PHONY: check-uv
check-uv:
	uv lock --check

.PHONY: check-deptry
check-deptry:
	uv run deptry .

.PHONY: check-dependencies
check-dependencies: check-uv check-deptry

#* Static linters

.PHONY: check-ruff
check-ruff:
	uv run ruff check $(CODE) --no-fix

.PHONY: check-codestyle
check-codestyle:
	uv run ruff format $(CODE) --check


.PHONY: check-ruff-github
check-ruff-github:
	uv run ruff check $(CODE) --no-fix --output-format=github


.PHONY: check-mypy
check-mypy:
	uv run mypy --install-types --non-interactive --config-file pyproject.toml $(CODE)

.PHONY: static-lint
static-lint: check-ruff check-mypy

#* Check safety

.PHONY: check-safety
check-safety:
	uv run safety check --full-report

.PHONY: lint
lint: check-dependencies check-codestyle static-lint

# Currently not supported in uv: https://github.com/astral-sh/uv/issues/6794
#.PHONY: update-dev-deps
#update-dev-deps:
#	poetry add -G dev mypy@latest pre-commit@latest pytest@latest deptry@latest \
#										coverage@latest safety@latest typeguard@latest ruff@latest

.PHONY: update
update:
	uv lock --upgrade

#* Build
.PHONY: build
build:
	uv pip install pyinstaller
	uv run pyinstaller --onefile --windowed --name validator \
		--collect-data PySide6 \
		--exclude-module PySide6.Qt3DAnimation \
		--exclude-module PySide6.Qt3DCore \
		--exclude-module PySide6.Qt3DExtras \
		--exclude-module PySide6.Qt3DInput \
		--exclude-module PySide6.Qt3DLogic \
		--exclude-module PySide6.Qt3DRender \
		--exclude-module PySide6.QtBluetooth \
		--exclude-module PySide6.QtCharts \
		--exclude-module PySide6.QtDataVisualization \
		--exclude-module PySide6.QtDesigner \
		--exclude-module PySide6.QtGraphs \
		--exclude-module PySide6.QtHttpServer \
		--exclude-module PySide6.QtLocation \
		--exclude-module PySide6.QtMultimedia \
		--exclude-module PySide6.QtMultimediaWidgets \
		--exclude-module PySide6.QtNfc \
		--exclude-module PySide6.QtPdf \
		--exclude-module PySide6.QtPdfWidgets \
		--exclude-module PySide6.QtPositioning \
		--exclude-module PySide6.QtQuick \
		--exclude-module PySide6.QtQuick3D \
		--exclude-module PySide6.QtQuickWidgets \
		--exclude-module PySide6.QtRemoteObjects \
		--exclude-module PySide6.QtScxml \
		--exclude-module PySide6.QtSensors \
		--exclude-module PySide6.QtSerialBus \
		--exclude-module PySide6.QtSerialPort \
		--exclude-module PySide6.QtSpatialAudio \
		--exclude-module PySide6.QtStateMachine \
		--exclude-module PySide6.QtTextToSpeech \
		--exclude-module PySide6.QtVirtualKeyboard \
		--exclude-module PySide6.QtWebChannel \
		--exclude-module PySide6.QtWebEngine \
		--exclude-module PySide6.QtWebEngineCore \
		--exclude-module PySide6.QtWebEngineWidgets \
		--exclude-module PySide6.QtWebSockets \
		excel_personal_data_validator/__main__.py

#* Cleaning
.PHONY: pycache-remove
pycache-remove:
	find . | grep -E "(__pycache__|\.pyc|\.pyo$$)" | xargs rm -rf || true

.PHONY: dsstore-remove
dsstore-remove:
	find . | grep -E ".DS_Store" | xargs rm -rf || true

.PHONY: mypycache-remove
mypycache-remove:
	find . | grep -E ".mypy_cache" | xargs rm -rf || true

.PHONY: ipynbcheckpoints-remove
ipynbcheckpoints-remove:
	find . | grep -E ".ipynb_checkpoints" | xargs rm -rf || true

.PHONY: pytestcache-remove
pytestcache-remove:
	find . | grep -E ".pytest_cache" | xargs rm -rf || true

.PHONY: ruffcache-remove
ruffcache-remove:
	find . | grep -E ".ruff_cache" | xargs rm -rf || true

.PHONY: build-remove
build-remove:
	rm -rf build/

.PHONY: reports-remove
reports-remove:
	rm -rf reports/

.PHONY: cleanup
cleanup: pycache-remove dsstore-remove mypycache-remove ruffcache-remove \
ipynbcheckpoints-remove pytestcache-remove reports-remove
