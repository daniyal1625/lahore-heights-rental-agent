# Local targets. The project targets Python 3.11; this Makefile uses the Python launcher.
# Override on the command line if needed: make PY_ARGS=-3.13 test

PYTHON ?= py
PY_ARGS ?= -3.11
export PYTHONPATH := src

.PHONY: seed run test verify-data rag-build rag-eval rag-test agent-ask agent-run

seed:
	$(PYTHON) $(PY_ARGS) -m mock_api.seed

run: seed
	$(PYTHON) $(PY_ARGS) -m uvicorn mock_api.app:app --host 127.0.0.1 --port 8001

test:
	$(PYTHON) $(PY_ARGS) -m pytest -q

verify-data:
	$(PYTHON) $(PY_ARGS) eval/verify_dataset.py --guide data/local_guide/wikivoyage_lahore.txt

rag-build:
	$(PYTHON) $(PY_ARGS) -m src.rag build

rag-eval:
	$(PYTHON) $(PY_ARGS) -m src.rag.eval_retrieval

rag-test:
	$(PYTHON) $(PY_ARGS) -m pytest -q tests/test_chunking.py tests/test_rag_smoke.py

# make agent-ask MSG="What time is check-in?" SYSTEM=rag
agent-ask:
	$(PYTHON) $(PY_ARGS) -m src.agent ask "$(MSG)" --system $(SYSTEM)

# make agent-run IDS=M-01,A-01 SYSTEMS=llm,rag,agent
agent-run:
	$(PYTHON) $(PY_ARGS) -m src.agent run --systems $(SYSTEMS) --ids $(IDS)
