## 1. Transition State Integration

- [ ] 1.1 Add dedicated phase-transition runtime state for 2->3 crossing in game loop
- [ ] 1.2 Add one-shot phase crossing detection (prev phase 2, current phase 3) with re-entry guard
- [ ] 1.3 Add transition timing fields and lifecycle hooks (start, update, finish)

## 2. Combat Pause and Bullet Clear

- [ ] 2.1 Pause Boss attack updates and player attack updates while transition state is active
- [ ] 2.2 Pause combat collision checks while transition state is active
- [ ] 2.3 Clear player bullets and Boss projectile/damage-zone containers at transition start
- [ ] 2.4 Ensure transition exit resumes normal phase 3 update order without stale timers

## 3. Glitch Rendering Pipeline

- [ ] 3.1 Add glitch renderer utility that accepts a base frame and elapsed/total transition time
- [ ] 3.2 Implement horizontal slice displacement using random Y-ranges and np.roll
- [ ] 3.3 Implement RGB split with small per-channel offsets and recomposition
- [ ] 3.4 Add subtle screen jitter and clamp rules to avoid out-of-bounds artifacts

## 4. Loop Wiring and Validation

- [ ] 4.1 Route phase-transition state to glitch rendering branch in main frame selection
- [ ] 4.2 Verify no Boss/player attacks occur during transition and bullets are cleared
- [ ] 4.3 Verify transition ends in normal frame and phase 3 combat resumes correctly
- [ ] 4.4 Regression test START_MENU, FAIL flow, WIN flow, and reset behavior remain unchanged
