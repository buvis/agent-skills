# Port Plan: {{TARGET}}

_Freshness: generated {{DATE}} from {{SOURCE_REF}} - regenerate if the source has moved on since._

## Inventory Matrix

| row | classification | reason | code-only |
|-----|-----------------|--------|-----------|
| {{ITEM}} | port / redesign / drop | {{WHY}} | yes / no |

Classification legend:

- **port** - ports unchanged.
- **redesign** - ports with modification; the `reason` column explains what changes and why.
- **drop** - does not port; the `reason` column explains why it stays behind.

`code-only` marks a row discovered only in code, absent from docs/SKILL.md/README, and therefore not yet judged by anyone.

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

The retirement PRD belongs to {{SOURCE_REPO}} (the repo where the code dies), and is written alongside the final port phase rather than remembered later.

Retire {{OLD_LOCATION}} once every criterion below holds:

| row | classification | reason | code-only |
|-----|-----------------|--------|-----------|
| {{ITEM}} | port / redesign / drop | {{WHY}} | yes / no |

- [ ] Every row above is classified, and every row with `code-only` = no has its test/doc/config follow-up landed.
- [ ] {{PORT_ROW}} ports cleanly: {{PORT_ROW_ACCEPTANCE_CRITERION}} (repeat this line once per `port`-classified row above).
- [ ] Every consumer listed in the Consumer Cutover table now points at `new reference`, and no code still references `current reference`.
- [ ] CI is green on the branch that removes {{OLD_LOCATION}}.
- [ ] {{ADDITIONAL_CRITERION}}

Hand this Retirement block to `create-prd` to lift verbatim into the retirement PRD once all criteria above are checked.
