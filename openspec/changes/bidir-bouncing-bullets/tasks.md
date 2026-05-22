# Tasks: Implement bidir-bouncing-bullets

1. Create change scaffolding (this change): proposal.md, design.md, tasks.md. (done)

2. Implement bullet model and spawn
   - File: `boss_attacks.py`
   - Add `bounces`, `max_bounces`, `loss_factor` to bullets created by the new `bidir_bounce` (or extend `cross`).
   - Implement `_spawn_bidir_bounce(boss_x, boss_y, boss_w, boss_h, phase)` which emits bullets left and right with specified speeds and `max_bounces`.
   - Status: done

3. Implement boundary reflection and culling
   - File: `boss_attacks.py`
   - In `BossAttackA.update`, after moving bullets, add boundary checks:
     - If bullet would cross left/right boundary and `bounces < max_bounces`: clamp x, invert vx * loss_factor, increment `bounces`.
     - Else if crosses top/bottom or `bounces >= max_bounces` and out of margin: recycle to pool.
   - Ensure pool size enforcement to avoid memory growth.
   - Status: done

4. Hook into attack sequences and parameters
   - File: `boss_attacks.py`
   - Make all phases cycle through the same attack set so every phase contains every attack method.
   - Keep single-shot bullet counts fixed; map phase to speed, angle, and damage only.
   - Tune `attack_configs` and `phase_interval_scale` so per-second spawn roughly preserved while speed increases.
   - Status: done

5. Optional UI/telemetry
   - File: `main.py`
   - Add on-screen bullet counter and key toggle for `dual_attack_mode` (if not already present) to facilitate stress testing.
   - Status: done

6. Testing and validation
   - Run the game locally, toggle `dual_attack_mode`, verify no infinite growth and observe FPS.
   - Verify collision behavior unchanged (player hit detection still works) and that phase progression behaves as expected.
   - Verify every phase includes every attack method, with only speed/angle/damage changing across phases.
   - Status: pending

7. Documentation
   - Update CHANGELOG or relevant README with the new attack description and how to enable stress test mode.

Estimated effort: 2–4 hours for full implementation + basic testing (depends on iteration on tuning parameters).

