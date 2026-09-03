# Quartz I/O adapter

The archived patch changes only the official `test_optimize` executable's
command-line I/O:

1. default to the repository-provided `Nam_5_3_complete_ECC_set.json`;
2. accept an explicit ECC-set path as argument 3;
3. accept an output-QASM path as argument 4.

The call to `Graph::optimize`, its cost bound (`1.05 * input gate count`),
search arguments, optimizer library, and ECC contents are unchanged. Benchmark
metadata records the artifact commit, patch SHA-256, ECC SHA-256, executable
SHA-256, input manifest SHA-256, and driver SHA-256.

