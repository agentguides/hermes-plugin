# db-ops

A worked example of a **book** — a single plugin whose root contains *multiple* Guide directories. Demonstrates:

- One `BOOK.md` (authoritative metadata + narrative) and one `plugin.json` at the top, three Guides inside.
- Cross-Guide bare-name references that resolve within the book (per SPEC §15).
- The same loader/validator/runner tooling works on individual Guides inside the book (`guide validate --root db-restore`).

## Contents

```
db-ops/
├── BOOK.md                           # authoritative book metadata + narrative
├── plugin.json                       # generated from BOOK.md at pack time
├── README.md                         # this file
├── db-backup/                        # take a fresh backup; no recovery, no rescue
│   ├── SKILL.md
│   ├── GUIDE.md
│   └── steps/
├── db-restore/                       # restore from a chosen backup; rescue on failure
│   ├── SKILL.md
│   ├── GUIDE.md
│   └── steps/
└── db-rollback/                      # the sibling rescue Guide that db-restore delegates to
    ├── SKILL.md
    ├── GUIDE.md
    └── steps/
```

## Cross-Guide reference

`db-restore`'s `020-apply-restore` step declares:

```yaml
on_failure:
  strategy: recover
  recover_with: "guide:db-rollback"
  resume_after_recovery: false
```

The bare-name `guide:db-rollback` resolves to the sibling `db-rollback/` directory because both Guides live in the same book root (this directory). This works *without* qualified scoping; SPEC §15 reserves `guide:plugin-x/name` for cross-plugin references.

## Running

Each Guide can be validated independently:

```bash
just validate                       # validates everything guide knows about
uv run guide validate --root examples/books/db-ops/db-restore \
                   --book examples/books/db-ops
```

Headless smoke (script actions only):

```bash
uv run python -m adapters.cli.run \
    --root examples/books/db-ops/db-backup \
    --state-path /tmp/db-backup-test
```

## Authoring layout

Use a book when several Guides share a domain (db ops, deploy ops, oncall runbooks) and you want them discoverable + distributed as one unit. Otherwise, use plugin-per-guide.

