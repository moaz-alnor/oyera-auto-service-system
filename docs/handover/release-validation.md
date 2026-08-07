# OYERA Release Validation Record

| Item | Verified result |
| --- | ---: |
| Role-based UAT cases | 32 / 32 PASS |
| Evidence screenshots | 41 |
| CSV evidence exports | 10 |
| Automated project tests | 826 PASS |
| Django system check | No issues |
| Migration drift check | No changes detected |
| Ruff linting | PASS |
| Ruff formatting | PASS |
| Shell-script syntax checks | PASS |
| Release branch | `feature/uat-handover` |
| UAT source commit | `61985a3` |

> The role automation resets the local demonstration database before
> each role. The final local database reflects the last executed role,
> while all verified role outcomes remain preserved in the execution
> ledger and evidence directories.

## Security note

All credentials in these guides are demonstration credentials created by
`reset_demo_data`. They must never be reused for a production deployment.
Production users must receive unique accounts and independently generated
passwords.
