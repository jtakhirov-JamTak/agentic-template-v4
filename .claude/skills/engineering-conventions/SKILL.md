---
name: engineering-conventions
description: Non-negotiable engineering rules for migrations, schema defaults, money, authorization, identity, API handler order, webhook receivers, data standards, and test falsifiability. Load before writing any schema, auth, billing, endpoint, webhook, or migration code, and before writing tests for those areas.
---

# Non-Negotiable Engineering Conventions

Apply unless docs/SPEC.md explicitly records a different safe rule (with human
approval noted in docs/DECISIONS.md).

Every rule here exists because of a specific failure. Nothing is here for tidiness.

## Migrations
Forward-only after application. Never edit an already-applied migration; create
a new one. (A PreToolUse hook also blocks edits to existing migration files —
if the hook blocks you, write a NEW migration instead of working around it.)

A structural migration must survive the rows already in the table, not just a clean
local DB:

- **`NOT NULL` on existing data** — backfill in the same migration before adding, or
  add nullable, backfill, then alter in a follow-up.
- **`CHECK` on existing data** — validate or remediate violators in the same
  migration. If the column is being *reused* for a new value, read its current
  constraint (`pg_get_constraintdef`) and widen it in the same migration. Type
  checking and unit tests cannot catch this, because neither performs a live insert.
- **`UNIQUE` indexes fail loudly by default.** `CREATE UNIQUE INDEX` aborts on the
  first duplicate. Pre-flight a `SELECT` for conflicting keys and raise, naming the
  count, so a human picks the resolution. Only dedup automatically when the survivor
  rule is explicit and written into the migration comment, and order by the column
  that encodes it — never a bare `DELETE ... WHERE rn > 1` ordered by `id`, which
  discards production rows on a rule nobody chose.
- **Timestamp pairs** — `>=`, not `>`, on `CHECK (end_at >= start_at)`. Clock
  equality on first write is a real case.

## Schema defaults for user-scoped tables
- **Owner FK** — `user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE`
  (or the project's equivalent). Without the cascade, account deletion leaves orphans.
- **`created_at`** — `TIMESTAMPTZ NOT NULL DEFAULT now()`.
- **`updated_at`** — `TIMESTAMPTZ NOT NULL DEFAULT now()`, kept current by the
  canonical trigger, not by application code:
  `CREATE TRIGGER <table>_set_updated_at BEFORE UPDATE ON public.<table> FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();`
  **Ordering dependency:** confirm `public.set_updated_at()` is defined in an earlier
  migration. A fresh-DB apply fails if the trigger runs before the function exists —
  and a fresh-DB apply is exactly what CI and a restore drill do.
- **`archived_at`** — `TIMESTAMPTZ` nullable, for soft delete. Include it whenever
  archive or delete semantics exist for the entity. It is not free: **if
  `archived_at` exists, every list query, every RLS SELECT policy, and every export or
  account-deletion walk must filter on it** — otherwise archived rows leak into lists,
  or survive a deletion request. State the choice in the migration comment.
- **Indexes** on every filterable or sortable column, at minimum the owner FK.
- **Data classification** — comment sensitive columns at creation
  (`email TEXT NOT NULL, -- PII: email`) so a privacy audit can find them by grep
  instead of inferring from names.

## Money
Persist monetary amounts as integers in the currency's minor unit, plus the
currency code. Never floating point for persisted money. Convert at the edge.

## Authorization
Default deny at the data layer. Supabase/Postgres: enable RLS and define policies
BEFORE a table holds real user data. **Every new table with user data gets its
policies in the same migration that creates it** — not a follow-up, because the
window between them is a window where the table is readable.

- **SELECT** — `USING (auth.uid() = user_id)`. Never `USING (true)`.
- **INSERT** — `WITH CHECK (auth.uid() = user_id)`.
- **UPDATE** — `USING (auth.uid() = user_id)`, and restrict which columns can change.
  Never let a user update an anchor column: a free-window start, a status with
  transition rules, a role.
- **DELETE** — only if user-initiated delete is supported. For anchor-bearing tables,
  having no DELETE policy is correct.

If the project authorizes at the route layer instead of with RLS, the same four rules
apply there.

## Identity
Derive user identity from the verified server session. Never authorize from a
client-supplied user ID alone.

## API handler order
Same order, every time. Each step assumes the previous one ran.

1. **Origin / CSRF check** — mutating endpoints only (`POST`/`PATCH`/`PUT`/`DELETE`).
   Do not add it to read GETs: it 403s same-origin downloads where `Origin` is absent,
   and cross-site `fetch()` cannot read the response anyway. Where a mutating flow
   legitimately arrives without `Origin`, accept `Sec-Fetch-Site: same-origin|none`.
2. **Authentication** — from the server-side session. Never read `userId` from the
   request.
3. **Rate limit** — per-minute burst AND per-day cap. The per-day cap is what stops a
   compromised session scraping.
4. **Schema validation** of the parsed body. 400 with field-level errors, values
   omitted. `.trim().min(1)` on every required string — whitespace passes a truthy
   check.
5. **Access gate** — a centralized helper, never inlined. Drift between inlined checks
   is exactly what the helper prevents. **Routes that must NOT carry it:** the auth
   callback / session refresh, the endpoint that *creates* the subscription,
   onboarding writes that run before the user can pay, webhook receivers, and admin
   routes (admin helper, not the paid gate). Gating one of those is a scaffolding bug,
   not a judgement call.
6. **Idempotency check** if the operation is non-idempotent and retryable.
7. **Business logic.** Every DB query filters by the authenticated user id.

**Raw before derived.** Insert the raw row first, then the derived row with its
computed field `null`, then call the model or compute, then UPDATE. Recoverable when
the model call fails.

**Inspect `.error` on every DB call.** `{ data, error }` returns do not throw on RLS
denial, schema drift, or an outage, so a `try/catch` will not catch them. Same for
`Promise.all` over writes — collect the results and inspect each one.

## Webhook receivers
A provider callback is **not** a normal endpoint. There is no session, no `Origin`, no
CSRF, and it must not be paywall-gated. Its security model is the signature.

Order: **raw body → verify signature → parse → replay defense → dispatch → mutate →
ack**.

1. **Read the raw body as text.** Do not parse yet.
2. **Verify the signature** against those raw bytes with the provider's SDK. Invalid
   or missing → `400`, log nothing sensitive, stop. This replaces auth + origin + CSRF.
3. **Parse** the now-trusted body. Never `req.json()` before verifying — it destroys
   the bytes the signature covers.
4. **Replay defense.** Providers retry and duplicate. Dedup on the provider's event id;
   if seen, ack `200` and do nothing. The same event twice must never double-grant
   entitlement.
5. **Dispatch on event type.** Unknown types ack `200` — a 4xx makes the provider retry
   forever.
6. **Mutate** with the privileged client, inspecting `.error` on every write. This is
   the only place allowed to grant entitlement; a user-callable route must never do it.
7. **Ack fast**, but only after the state that makes the event safe to replay is
   committed.

## Data standards
Global rules (`~/.claude/CLAUDE.md`) also apply: UTC times, `archived_at`
instead of delete, and falsifiable verification.

- Enums as text columns with CHECK constraints, not native enum types.
- Cursor pagination needs a unique tie-breaker column in the ordering.
- **Uniqueness on a table with `archived_at`** — filter the index rather than adding a
  plain constraint, or an archived row reserves its value forever and users read that
  as a bug:
  `CREATE UNIQUE INDEX ... ON things (user_id, lower(name)) WHERE archived_at IS NULL;`

## Test falsifiability
- Ordinary behavior: per feature, take at least one representative new test,
  intentionally break the protected behavior, confirm the test FAILS, restore,
  confirm it passes.
- High-stakes controls — authentication, authorization/RLS, money/billing,
  destructive or data-transforming migrations: do the break-and-confirm check
  INDIVIDUALLY for every distinct control. Sampling is not allowed here.

## Secrets
Never in source, docs, logs, prompts, or output. `.env` only; reference by
env-var NAME. (A hook scans writes for common secret patterns; a block means
remove the secret, not obfuscate it.)

Never log a request body, an AI prompt, or any user-text field. Error-tracker payloads
count as logs: SDK error messages are built from the *response* body, so a PostgREST
conflict carries the offending column values inside `error.details`. Scrub before it
reaches the sink.
