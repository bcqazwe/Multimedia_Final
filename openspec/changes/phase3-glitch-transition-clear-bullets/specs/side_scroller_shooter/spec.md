## ADDED Requirements

### Requirement: Phase 2 to Phase 3 transition SHALL pause combat and clear bullets
The system SHALL trigger a dedicated transition state exactly once when the Boss phase crosses from 2 to 3. During this transition state, the system MUST pause Boss attack updates and player attack updates, and MUST clear active player bullets and Boss projectile/damage-zone objects before resuming combat.

#### Scenario: Enter transition on phase crossing
- **WHEN** the game is in RUNNING and the computed phase changes from 2 to 3
- **THEN** the system enters a dedicated phase-transition state and marks transition as active

#### Scenario: Stop combat updates during transition
- **WHEN** the game is in the phase-transition state
- **THEN** the system MUST NOT execute Boss attack update logic, player bullet spawn/update logic, or combat collision resolution

#### Scenario: Clear bullet objects at transition start
- **WHEN** the phase-transition state starts
- **THEN** the system clears active player bullets and active Boss attack bullets/damage zones before rendering transition effects

### Requirement: Transition rendering SHALL apply glitch effect before phase 3 resumes
The system SHALL render a glitch transition effect during the phase-transition state. The glitch effect MUST include horizontal slice displacement and RGB channel split, and SHALL end in a normal frame before entering phase 3 combat.

#### Scenario: Horizontal slice displacement is visible
- **WHEN** rendering any frame during the phase-transition state
- **THEN** the system applies random horizontal slice offsets to multiple Y-axis ranges of the frame

#### Scenario: RGB split is visible
- **WHEN** rendering any frame during the phase-transition state
- **THEN** the system applies slight per-channel X/Y offset so color-edge ghosting is visible

#### Scenario: Return to normal rendering after transition
- **WHEN** the transition duration reaches the configured end time
- **THEN** the system exits phase-transition state and resumes normal phase 3 rendering and combat updates
