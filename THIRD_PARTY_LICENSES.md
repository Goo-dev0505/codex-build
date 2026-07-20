# Third-party licenses

The codex-build skill itself is MIT-licensed (see [`LICENSE`](LICENSE)). It **bundles no third-party code** — there is nothing vendored into this repository to redistribute.

codex-build *orchestrates* external command-line tools that you install and license separately. They are not included here; each is governed by its own upstream license:

| Tool | Role | Upstream |
| --- | --- | --- |
| OpenAI Codex CLI (`codex`) | the coder | https://github.com/openai/codex |
| Git | version control | https://git-scm.com |
| GitHub CLI (`gh`) — optional | opens the PR | https://github.com/cli/cli |
| GitLab CLI (`glab`) — optional | opens the MR | https://gitlab.com/gitlab-org/cli |
| beads (`bd`) — optional | task tracking | https://github.com/steveyegge/beads |

Use of these tools is subject to their respective licenses and, for hosted services, their terms of service.
