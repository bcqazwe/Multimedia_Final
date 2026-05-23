## 1. Transition Scaffolding

- [x] 1.1 Add a dedicated phase 1-to-2 transition state and lifecycle helpers in `ui_screens.py`
- [x] 1.2 Add single-trigger phase crossing detection for phase 1 -> phase 2 in the main game loop
- [x] 1.3 Ensure the transition duration is fixed at 5 seconds and can be queried consistently

## 2. Combat Freeze and Bullet Clear

- [x] 2.1 Pause player firing and Boss attack updates while the transition is active
- [x] 2.2 Clear player bullets, Boss bullets, and active projectile hazard structures when the transition begins
- [x] 2.3 Reset attack state/timers so gameplay resumes cleanly in phase 2

## 3. Soft Pulse Presentation

- [x] 3.1 Implement a low-intensity soft pulse visual effect for the phase 1 -> phase 2 transition
- [x] 3.2 Keep the visual effect lighter than the existing phase 2 -> phase 3 glitch transition
- [x] 3.3 Render the transition effect through `ui_screens.py` so the main loop stays focused on combat flow

## 4. Verification

- [x] 4.1 Run syntax and import checks for the touched modules
- [x] 4.2 Verify phase 1 -> phase 2 clears bullets and pauses actions for the full 5-second transition
- [x] 4.3 Verify phase 2 -> phase 3 glitch behavior remains unchanged
