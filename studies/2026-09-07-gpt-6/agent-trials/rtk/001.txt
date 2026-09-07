You are investigating a small Python service before deployment. Answer the following six questions accurately, using commands and files in this directory. Do not edit application code or tests. There is no network requirement.

1. Run tests/test_pass.py and tests/test_failure.py. Report the passing and failing test counts and the root cause of each failed test.
2. Run tests/test_legacy.py. Does its output identify a migration deadline? State the release and replacement adapter, or explicitly state that none was reported.
3. Inspect the latest commit message. State its deployment precondition and rollback requirement.
4. Inspect uncommitted changes to settings.py. Identify every change to a boolean setting and its security implication.
5. Inspect the route definitions. Which roles may access /admin/archive, and does /admin/export require authentication?
6. Inspect deployments.json. List every deployment that is not ready and the stated reason.

Return a JSON answer with keys q1 through q6, and a short explanation of any additional reads you needed after incomplete output. Save the same JSON in answer.json using apply_patch. Do not count information as absent merely because an output was truncated. You may use whichever command flags and follow-up reads you judge appropriate.
