## TODO-003: Deferred dynamic-needs extensions

- Priority: low
- Category: research
- Area: Homeostatic model and external state integration
- Dependencies: none
- Rationale: Explicitly deferred from the approved dynamic-needs V1; documented in docs/HOMEOSTASIS.md and not implemented in this change.

-Acceptance Criteria:
Future work covers hunger and sleep; automatic time-based accumulation; event-driven state updates and recovery; relationship-specific satisfaction; learned or calibrated personal parameters; and richer deterministic feature-to-need inference. Preserve explicit external ownership of state evolution and document schema/formula changes before each extension.

## TODO-004: Review exhaustion-sensitive rest and aftereffect scoring

- Priority: medium
- Category: research
- Area: Utility model architecture
- Dependencies: none
- Rationale: Latest evaluation exposed inflated aftereffect scale, fixed relief-from-structure proxies, and sleep scoring equally when rested. Personal model v3 mitigates scale via parameters; architectural semantics remain unchanged and require a user design decision.

-Acceptance Criteria:
Discuss and agree on state-dependent rest/exhaustion behavior, the effort-cost cap, and explicit evidence for aftereffects before implementation. Assess unequal-duration comparison and physical-activity dose limits without introducing caller-owned state evolution into Valence. Validate chosen design against exhausted and rested scenarios, preserve historical evaluations, and document versioned contract changes.
