# Chapter 05: Script Breakdown & Scheduling

**Billable unit:** Billable unit: one breakdown + schedule

**Tension function:** Tension: 0 — production work, but it prevents tension from collapsing on set (or in generation).

Inputs: script. Outputs: prop list, costume list, location list, VFX shot list, cast list, day-out-of-days, generation batch plan. Gates: every script element appears in a list; every shot is assigned to a batch of <=6 clips. Cost drivers: unique locations, unique costumes, VFX shots. See pipeline/movie.py breakdown. Storyboard mapping: the breakdown is the shopping list for the panels — if a panel needs a prop that is not listed, the panel cannot be generated consistently.
