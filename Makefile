.PHONY: verify test audit setup

setup:
	python -m venv .venv
	.venv/bin/python -m pip install --require-hashes -r requirements.lock.txt

verify:
	python scripts/verify_release.py
	python scripts/security_check.py --strict

test:
	python -m unittest discover -s tests -v

audit:
	python -m pip_audit -r requirements.lock.txt
	bandit -q -r bot.py public_safety.py kalshi_15m_sell_bot.py -ll
