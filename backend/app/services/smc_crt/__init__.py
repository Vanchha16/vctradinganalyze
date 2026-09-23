"""smc-ict-crt-v1 production path (ADR-183).

`rules.py` here is a byte-for-byte copy of the frozen research module
`research/smc_ict_crt_v1/rules.py`. `tests/test_smc_crt_parity.py` fails if
the two ever differ, so the production path cannot drift from the frozen
specification. Nothing in this package imports BBMA code, and no BBMA code
imports this package.
"""
