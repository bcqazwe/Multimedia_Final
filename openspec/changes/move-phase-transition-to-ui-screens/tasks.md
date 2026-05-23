## 1. ui_screens Transition Orchestration API

- [x] 1.1 Add ui_screens transition-begin helper for phase 2->3 entry setup
- [x] 1.2 Add ui_screens transition-update helper for elapsed-time progression and completion
- [x] 1.3 Add ui_screens transition-render helper for glitch frame generation
- [x] 1.4 Add ui_screens transition-active check helper used by main branching

## 2. Main Loop Responsibility Slimming

- [x] 2.1 Keep phase crossing detection in main but delegate transition begin to ui_screens
- [x] 2.2 Replace inline transition timing/state branch logic in main with ui_screens update delegation
- [x] 2.3 Replace inline transition frame composition in main with ui_screens render delegation
- [x] 2.4 Ensure main keeps only minimal state selection and avoids transition detail ownership

## 3. Behavior Consistency and Regression Checks

- [x] 3.1 Verify transition still pauses Boss/player attack updates and collision checks
- [x] 3.2 Verify transition start still clears player bullets and Boss projectile/damage-zone containers once
- [x] 3.3 Verify transition completion resumes normal phase 3 combat and rendering
- [x] 3.4 Regression test START_MENU, FAIL transition, WIN flow, and reset path after refactor
