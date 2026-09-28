# Team

Who works on {NAME}, who runs the human gates, and who reviews which paths. Edit it in place: it states today only. `.github/CODEOWNERS` is generated from the Ownership table, so change owners here, then re-run project-init.

## Roster

| Name | Role | GitHub |
|---|---|---|
{TEAM_ROWS}

## Human gates

A person with the Lead role runs `mise run approve`, `merge`, `abandon` and `release`, in a terminal or with the `!` prefix. An agent never runs them (`specs/README.md#gates`). With a remote, merge waits for an approving review on the pull request.

## Ownership

One row per path, owners as `@login`, `@org/team` or an email. The first row covers everything else.

| Path | Owner |
|---|---|
| `*` | {LEAD_OWNER} |
