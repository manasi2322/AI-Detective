# Live LLM runs

This folder holds the output of `python -m detective llm-run`: one JSON file per case and a
`SUMMARY.md` table listing, for Claude's proposed events, reasoning steps and answer quotes,
what was accepted and what was rejected (with the reason).

**Status: not run yet.** The run needs Claude API credentials, which were not available on the
machine where this project was built. To produce the results:

```bash
pip install anthropic pydantic
export ANTHROPIC_API_KEY=...      # or: ant auth login
python -m detective llm-run
```

Until then, the LLM code paths are covered offline by tests that use stand-in models which also
send invented quotes (`tests/test_llm_extract.py`, `test_investigator.py`, `test_qa.py`,
`test_llm_run.py`), and by the grounding attack in `python evaluate.py`.
