# BAM Known Issues and Future Development Notes

*Initiated: 2026-05-29*
*Author: E. Stabenau / Everglades Foundation*

---

## Issue 1 — Salinity spikes in coastal boundary basins

### Status
Known, pre-existing behavior. Present throughout the full period of record
(1999–2026). Not introduced by the WY2026 extension work.

### Affected basins

| Basin | ID | Direct tidal boundary | Boundary station |
|---|---|---|---|
| Conchie Channel | 42 | Gulf Tide 1 (basin 59) | Cape Sable |
| Sandy Key | 58 | Gulf Tide 2 (basin 60) | Region 2 |
| Ninemile Bank | 43 | Gulf Tide 3 (basin 61) | Region 3 |

These are the **only three interior basins directly connected to Gulf tidal
boundary conditions** via shoals. All other Florida Bay interior basins
receive tidal forcing indirectly — through one or more of these three basins.
First National Bank, Johnson Key, Dildo Key Bank, and other western basins
are buffered by at least one intermediate basin, which is why only these
three show the spike pattern.

### Symptom

When plotted at daily output resolution, these basins show rapid salinity
spikes (40–80+ ppt) that repeat throughout the period of record. The spikes
are correlated with tidal phase at the time of the output snapshot.

### Physical principle (E. Stabenau, 2026-05-29)

> *"Salinity should not increase when water flows out of the coastal basin
> toward the coast, exiting the model grid. Salt budget is important but
> the model should match the physics."*

When water flows OUT of Sandy Key/Ninemile Bank/Conchie Channel through the
shoal connecting them to the Gulf boundary, that water carries its salt with
it. The remaining water in the basin should have the **same salinity** as
before — proportional salt removal means no concentration effect from
outflow alone. The only legitimate driver of salinity increase is net
evaporation exceeding precipitation.

### Root cause in code

**File:** `hydro.py` — `MassTransport()`, lines 311–316

```python
if Basin_A.water_volume < 0 :
    Basin_A.water_volume = 0          # overdrain: clamp to zero
if Basin_B.water_volume < 0 :
    Basin_B.water_volume = 0
if Basin_A.water_volume == 0 or Basin_B.water_volume == 0 :
    continue                          # skip salt transfer  ← BUG LOCATION
```

When a shoal's outflow (`delta_volume`) exceeds the basin's remaining volume,
`water_volume` goes negative and is clamped to zero. The `continue` then
skips salt removal for that shoal. The result:

- Basin has **zero water volume** but **non-zero salt_mass**
- On flood-tide refill, the orphaned salt_mass is present in the new small
  incoming volume
- Salinity = (orphaned_salt + incoming_salt) / new_volume → spike

Over successive tidal cycles, small amounts of salt accumulate in this way,
driving salinity progressively above the physically expected range for these
tidal-front basins.

The original authors were aware of the general hypersalinity tendency in
these basins — all three (plus several others) are in an explicit exemption
list that halves `salt_mass` when salinity exceeds 90 ppt
(`MassTransport()` lines 366–384). This guard manages the worst cases but
does not address the root cause.

### Two contributing mechanisms

**Mechanism 1 — Salt orphaning (code issue):**
As described above. Occurs when any shoal attempts to drain more volume
than a basin holds. The salt corresponding to the overshoot volume is
never removed.

**Mechanism 2 — Tidal aliasing in output (output artifact):**
The model runs at Δt = 360 s. When output is written as daily instantaneous
snapshots, the sample falls at a different tidal phase each day (tidal period
≈ 12–24 h at the Gulf side). Days where the snapshot catches low tide show
concentrated salinity; days where it catches high tide show diluted salinity.
This creates an apparently erratic signal even if the tidal physics are
correct. This mechanism is present even if Mechanism 1 is fixed.

### Proposed fix (Mechanism 1)

When `Basin_A.water_volume` is clamped to 0 (overdrain), also zero
`Basin_A.salt_mass`. An empty basin physically holds no salt. On the next
flood-tide timestep, the refilling water carries Gulf salinity in normally.

```python
if Basin_A.water_volume < 0 :
    Basin_A.water_volume = 0
    if not Basin_A.boundary_basin :
        Basin_A.salt_mass = 0         # empty basin → no salt retained
if Basin_B.water_volume < 0 :
    Basin_B.water_volume = 0
    if not Basin_B.boundary_basin :
        Basin_B.salt_mass = 0
```

**Before implementing:** verify that zeroing `salt_mass` on complete drain
does not adversely affect the salt budget for interior basins that drain
during drought events (where the intent may be to preserve hypersaline
residual). Consider a flag or depth threshold to distinguish tidal-front
basins (should zero on drain) from interior ephemeral ponds (residual salt
may be intentional). Review with original model authors.

### Proposed fix (Mechanism 2)

Change `output_interval` from 24 h to 1 h (or 6 h) for diagnostic runs,
or compute time-averaged output values rather than instantaneous snapshots.
The BAM output routine currently writes instantaneous state at each output
timestep; adding an averaging accumulator would require changes to
`model.py` and the `CopyDataRecord()` / output writing logic.

### References

- `Notes.py` → `ToDo()` — brief entry pointing here
- `hydro.py` lines 309–340 — MassTransport volume and salt transfer
- `hydro.py` lines 360–387 — salinity computation and >90 ppt guard
- `data/Boundary/Basin_Tide_Boundary_2000_2026.csv` — Gulf boundary mappings
- `data/init/Shoal_Parameters.csv` — shoals 22/23/45/370/371 are the
  direct Gulf connections

---
