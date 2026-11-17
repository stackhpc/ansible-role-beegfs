# T15 — Replace Travis with GitHub Actions

**Files:** delete `.travis.yml`, add `.github/workflows/lint.yml`,
update README badge.

Lint-only job (GitHub runners can't run nested libvirt reliably):
`pip install -r molecule/requirements.txt`,
`ansible-galaxy collection install -r requirements.yml`, `yamllint .`,
`ansible-lint`, `ansible-playbook tests/test.yml -i tests/inventory
--syntax-check` (keep the `stackhpc.beegfs` symlink trick from Travis).

Molecule stays a manual/local run; document it in README.

## Outcome (2026-11-17)

Done (+34, approved ~30 + the 2 extras). `.travis.yml` deleted;
`.github/workflows/lint.yml` runs yamllint, ansible-lint, flake8
(molecule/tests) and the tests/test.yml syntax check on every push and PR.
Extras: removed the T05 spike workflow + script (findings stay in T05;
files in git history); Molecule now also runs on master and on pull
requests (docs-only changes still skipped). README has a lint badge.
