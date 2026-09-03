# Quasar driver execution-control revision

This note documents the execution-control-only change made after the formal
single-worker parent process disappeared at an atomically written checkpoint of
217 rows. It is not presented as a source patch because the original segment-1
driver was not retained as a separate file. The exact source hashes for both
segments are recorded in `execution_segments.json`.

The segment-2 driver keeps the frozen manifest, Quasar configuration, optimizer
invocation, timeout budget, validation rules, ITT policy, and completed rows
unchanged. It changes only subprocess lifecycle control:

- launch the artifact command with `subprocess.Popen`;
- on an outer timeout, terminate the exact Windows PID tree with
  `taskkill /PID <pid> /T /F` and record the cleanup result;
- remove stale per-attempt output, temporary, and timeline files before a
  pending attempt;
- record the artifact return code in each new result row.

The motivating diagnosis is an inference from the observed wrapper/grandchild
process layout and repeated timeout history: killing only the wrapper may have
left the Miniforge grandchild alive. The disappearance itself did not emit a
traceback, so this mechanism is not asserted as proven.

After segment 2 reached 226 checkpointed rows, its single worker was observed
running later pending inputs while the checkpoint timestamp no longer changed.
The parent and its exact child tree were terminated, leaving the 226-row atomic
file intact. No traceback was available because the parent was terminated while
apparently waiting for executor shutdown. Segment 3 adds a bounded exponential
retry only for `PermissionError` raised by the atomic destination replacement;
the artifact call, optimizer budget, input, and outcome contract are unchanged.
The active checkpoint will no longer be opened for progress monitoring.
