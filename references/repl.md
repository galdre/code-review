# Isolated nREPLs for review agents

Every agent that runs code gets its own nREPL and its own app DB, so that no agent can change another agent's
state. The coordinator assigns the resources in the agent's prompt; the agent never picks them or reuses another's.

The coordinator also writes the project's launch, app-DB and teardown commands into the review's
`reviews/COMMON-CONTEXT.md`: those of the project section below when there is one, else the commands the project
documents for a development nREPL against a database of its own.

## Assignment

For agent number `k` in a review of PR `<pr>`:

| Resource | Value |
|---|---|
| Port | `7900 + k` (check first with `lsof -nP -iTCP:<port> -sTCP:LISTEN`; skip a busy port) |
| App DB | `cr<pr>_a<k>`, a database of its own on the local database server |
| Log | `scratch/review-<pr>-<sha>/agents/a<k>/nrepl.log` |
| Work folder | `scratch/review-<pr>-<sha>/agents/a<k>/` |

Run at most 6 JVMs at once. If more agents need a REPL, start the rest when earlier ones finish.

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
setup.

## Teardown, always, including on failure

```bash
lsof -nP -iTCP:<port> -sTCP:LISTEN -t | xargs kill
```

Then drop the app DB. Kill by port, never by process name. Drop only your own database. Report teardown in your
final message.

## Project: Metabase

App DB on the local Postgres:

```bash
psql -h localhost -p 5432 -d postgres -c 'create database cr<pr>_a<k>'
cd <worktree>
MB_DB_TYPE=postgres MB_DB_DBNAME=cr<pr>_a<k> MB_DB_HOST=localhost MB_DB_PORT=5432 MB_DB_USER=$(whoami) \
  clojure -M:dev:ee:ee-dev -m nrepl.cmdline -p <port> > <log> 2>&1 &
```

Initialize the app DB: `(require 'metabase.test.initialize) (metabase.test.initialize/initialize-if-needed! :db)`.

Teardown: `psql -h localhost -p 5432 -d postgres -c 'drop database cr<pr>_a<k>'`.

Known traps: the test HTTP handler is cached per JVM; driver-gated tests need `metabase.test.data.env/*test-drivers*`
bound; a local premium token with `:library` makes some fixtures fail (restrict features with
`mt/with-premium-features`). Run tests in the REPL, not with `./bin/test-agent`, unless a fresh JVM is the point of the
test.
