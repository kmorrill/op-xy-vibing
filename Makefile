PY := python3

.PHONY: validate validate-fixtures hash-fixtures

validate:
	@$(PY) -m conductor.validator $(FILE)

validate-fixtures:
	@set -e; \
	for f in conductor/tests/fixtures/*.json; do \
		echo "==> $$f"; \
		$(PY) -m conductor.validator $$f --print-hash || exit $$?; \
	done

canonicalize-fixtures:
	@set -e; \
	for f in conductor/tests/fixtures/*.json; do \
		echo "==> canon $$f"; \
		$(PY) -m conductor.validator $$f --write; \
	done

