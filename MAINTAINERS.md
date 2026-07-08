# Maintainers

## Current maintainers

| Name | GitHub | Areas |
|---|---|---|
| Wes Jackson | [@rdwj](https://github.com/rdwj) | All (interim — see bus factor note) |

Maintainers have merge rights, deploy access to the shared demo cluster, and own project-board triage. `.github/CODEOWNERS` mirrors this list and must be updated in the same PR as any change here.

## Review and merge rules

- Every PR requires approval from at least **one maintainer** who is not the PR author, plus green CI (`.github/workflows/test.yml`, version-check, secret scanning).
- **Maintainer self-merge:** while the project has a single maintainer, maintainer-authored PRs may be self-merged after CI passes, with a minimum 24-hour open window for non-trivial changes so contributors can comment. Once a second maintainer joins, self-merge is retired and maintainer PRs require review from another maintainer like everyone else's.
- Trivial changes (typos, doc formatting, CI config fixes) may be merged by any maintainer without the waiting period.
- Disagreements are resolved by discussion on the PR/issue; if consensus isn't reached, the maintainer who owns the affected area decides. Design-level disputes should go through a `design_proposal` issue rather than being settled in a PR thread.

## Becoming a maintainer

There is no fixed quota. A contributor is nominated by an existing maintainer after a track record of:

- Several merged PRs of substantial scope, including at least one that required design-doc work
- Constructive review participation on other people's PRs
- Demonstrated familiarity with the project conventions (CLAUDE.md / CONTRIBUTING.md), especially the same-commit consumer audit and mock-vs-real discipline

Nomination happens in a GitHub Discussion; existing maintainers decide by consensus. New maintainers are added to this file, to CODEOWNERS, and to the GitHub team in one PR.

## Stepping down / removal

Maintainers may step down at any time by PR to this file. A maintainer inactive for 6+ months may be moved to an "emeritus" section by consensus of the remaining maintainers. Conduct-related removal follows the [Code of Conduct](CODE_OF_CONDUCT.md) enforcement process.

## Bus factor note

The project currently has one maintainer. Growing this list is an explicit goal — if you're a regular contributor and interested, say so in a Discussion.
