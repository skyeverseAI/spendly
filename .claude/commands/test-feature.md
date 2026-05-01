You are orchestrating a two-phase test workflow for the Spendly Flask app. The user has invoked `/test-feature` for: **$ARGUMENTS**

Run the two phases below **sequentially** — Phase 2 must not start until Phase 1 is complete.

---

## Phase 1 — Write Tests (spendly-test-writer)

Launch the `spendly-test-writer` agent with the following briefing:

> The user wants tests written for this feature: **$ARGUMENTS**
>
> Follow your spec-first workflow. If the description above is not sufficient to define behavior, HTTP routes, and at least one success and one failure case, stop and ask the user for clarification before writing any tests. Do not infer from implementation code.

Wait for the agent to finish and confirm that test files have been written to `tests/`.

If the agent stopped to ask clarifying questions, pause and relay those questions to the user. Resume Phase 1 once the user provides answers. Do not proceed to Phase 2 until test files exist on disk.

---

## Phase 2 — Run & Report (pytest-qa-reporter)

Once Phase 1 is complete, launch the `pytest-qa-reporter` agent with the following briefing:

> Tests for the "$ARGUMENTS" feature have just been written. Run the targeted test file if one was named in Phase 1 (e.g. `pytest tests/test_<feature>.py`), otherwise run the full suite. Deliver the full structured QA report including Final Verdict.

---

## After Both Phases

Present the user with:
1. A one-line summary of what tests were written (file path, count)
2. The full QA report from Phase 2
3. Any spec gaps or ambiguities flagged by either agent

Do not suggest fixes or modify any code. Your role is orchestration and summary only.
