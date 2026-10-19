# Isolated nREPLs for review agents

Every agent that runs code gets its own nREPL and its own app DB, so that no agent can change another agent's
state. The coordinator assigns the resources in the agent's prompt; the agent never picks them or reuses another's.

How to launch an nREPL against a database of its own, run tests there, and clean up afterwards is the project's
business. The coordinator finds it in the project's skills and instructions (for example a skill for running the
project's REPL, or its `CLAUDE.md` or `AGENTS.md`), and writes the commands into the review's
`reviews/COMMON-CONTEXT.md`. When the project documents none, the coordinator asks the user before agents start.

## Assignment

For agent number `k` in a review of PR `<pr>`:

| Resource | Value |
|---|---|
| Port | `7900 + k` (check first with `lsof -nP -iTCP:<port> -sTCP:LISTEN`; skip a busy port) |
| App DB | `cr<pr>_a<k>`, a database of its own on the local database server |
| Log | `scratch/review-<pr>-<sha>/agents/a<k>/nrepl.log` |
| Work folder | `scratch/review-<pr>-<sha>/agents/a<k>/` |

Run at most 6 nREPLs at once. If more agents need a REPL, start the rest when earlier ones finish.

## Launch

Create the app DB, then start the nREPL in the worktree with the project's command, in the background, with its
output in the log. Read the port from the log line "nREPL server started", never from `.nrepl-port`. Poll for it; do
not sleep a fixed time. Evaluate only against your own port. Initialize the app DB only when the work needs it.

## Running tests in the REPL

```clojure
(require 'some.test-ns :reload)
(let [results (atom {:pass 0 :fail 0 :error 0})]
  (binding [clojure.test/*test-out* (java.io.StringWriter.)
            clojure.test/report (fn [m] (when (#{:pass :fail :error} (:type m)) (swap! results update (:type m) inc)))]
    (clojure.test/test-vars [#'some.test-ns/some-test]))
  @results)
```

Known traps: `:reload` does not remove deleted vars (use `remove-ns`); `test-vars` skips the runner's fixture
setup. The project's own skills list its further traps.

## Clean up after yourself, always, including on failure

An agent that ran code cleans up everything it started, as the project's instructions say: it stops its nREPL, drops
its app DB, and removes any worktree it created. It stops a process by its port, never by its name:

```bash
lsof -nP -iTCP:<port> -sTCP:LISTEN -t | xargs kill
```

It touches nothing that another agent or another review started; it names such processes in its report, so the
user can decide. It states in its final message what it stopped and removed.
