---
name: engineering-conventions
description: Non-negotiable engineering rules for migrations, money, authorization, identity, data standards, and test falsifiability. Load before writing any schema, auth, billing, or migration code, and before writing tests for those areas.
---

# Non-Negotiable Engineering Conventions

Apply unless docs/SPEC.md explicitly records a different safe rule (with human
approval noted in docs/DECISIONS.md).

## Migrations
Forward-only after application. Never edit an already-applied migration; create
a new one. (A PreToolUse hook also blocks edits to existing migration files —
if the hook blocks you, write a NEW migration instead of working around it.)

## Money
Persist monetary amounts as integers in the currency's minor unit, plus the
currency code. Never floating point for persisted money. Convert at the edge.

## Authorization
Default deny at the data layer. Supabase/Postgres: enable RLS and define
policies BEFORE a table holds real user data. Every new table with user data
needs its policies in the same migration or an immediately following one.

## Identity
Derive user identity from the verified server session. Never authorize from a
client-supplied user ID alone.

## Data standards
- Times are UTC in the database; convert at the edge.
- Never hard-delete data with history value: use `archived_at`; only an
  explicit human request removes a row.
- Enums as text columns with CHECK constraints, not native enum types.
- Cursor pagination needs a unique tie-breaker column in the ordering.

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
