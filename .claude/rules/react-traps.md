---
paths:
  - "**/*.tsx"
  - "**/*.jsx"
---

# React traps that cost a rebuild

Each of these fails silently or intermittently, which is why it survives review.

## Strict Mode double-invocation
Effects that perform a server write run twice in development Strict Mode. Guard with a
ref, and dedup server-side as the other half — the guard alone does not survive a
remount in production:

```tsx
const started = useRef(false);
useEffect(() => {
  if (started.current) return;
  started.current = true;
  void createThing();
}, []);
```

## Key sensor-holding components by step
React reuses a component instance at the same tree position across a step change. A
voice, camera, or file input keeps its in-flight async work and fires the result against
the *next* step's field. Key it by the step:

```tsx
<VoiceInput key={currentStep.key} />
```

## `setState` then submit in the same tick reads stale state
A select-button that sets state and submits in one handler submits the previous value.
Pass the value into the submit handler explicitly rather than reading it back from
state.

## Progressive save
Save after each completed step of a multi-step flow, not at the end. A wizard that only
persists on the final submit loses everything to a refresh, a crash, or a 403.

## A gated submit must preserve the user's input
If a submit can return 403, a paywall, or auth-required: keep the filled form mounted,
snapshot any prior output, and inline the upgrade prompt. Never `router.push(...)` away
from a filled multi-step form — the input is gone and the user will not retype it. If a
sibling flow already has an inline-gate pattern, copy it.

## Every error path offers a next action
No dead-end "Done" after a partial failure. Empty states carry specific copy, not "no
data". Loading states must terminate on a failed fetch — an indefinite spinner reads as
a hung app.

## Resolve every internal link against the route tree
Do not assume a nav target exists. A broken link inside an authenticated app destroys
trust faster than a missing feature.
