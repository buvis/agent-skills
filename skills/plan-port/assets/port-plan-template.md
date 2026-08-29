# Port Plan: {{TARGET}}

_Freshness: generated {{DATE}} from {{SOURCE_REF}} - regenerate if the source has moved on since._

## Inventory Matrix

| row | classification | reason | code-only |
|-----|-----------------|--------|-----------|
| {{ITEM}} | keep / adapt / drop | {{WHY}} | yes / no |

Classification legend:

- **keep** - ports unchanged.
- **adapt** - ports with modification; the `reason` column explains what changes and why.
- **drop** - does not port; the `reason` column explains why it stays behind.

`code-only` marks a row whose port is code alone, with no accompanying test, doc, or config change required.

## Consumer Cutover

| consumer | current reference | new reference | cutover step |
|----------|--------------------|----------------|---------------|
| {{CONSUMER}} | {{OLD_PATH}} | {{NEW_PATH}} | {{STEP}} |

Every consumer must appear in this table before the retirement block below can be checked off.

## Phases (dependency order)

1. {{PHASE_1}} - no dependencies.
2. {{PHASE_2}} - depends on Phase 1 landing and its exit criteria holding.
3. {{PHASE_3}} - depends on Phase 2 landing and its exit criteria holding.

Do not start a phase until the phase before it has landed and its exit criteria hold.

## Retirement

Retire {{OLD_LOCATION}} once every criterion below holds:

- [ ] Every row in the Inventory Matrix is classified, and every row with `code-only` = no has its test/doc/config follow-up landed.
- [ ] Every consumer listed in the Consumer Cutover table now points at `new reference`, and no code still references `current reference`.
- [ ] CI is green on the branch that removes {{OLD_LOCATION}}.
- [ ] {{ADDITIONAL_CRITERION}}

Hand off to {{OWNER}} for final deletion of {{OLD_LOCATION}} once all criteria above are checked.
