## ADDED Requirements

### Requirement: Phase transition orchestration SHALL be owned by ui_screens
The system SHALL centralize phase-transition lifecycle handling in the UI transition module. Transition begin, transition update, transition render, and transition completion logic MUST be implemented through ui_screens orchestration entry points instead of inline main-loop logic.

#### Scenario: Main delegates transition begin
- **WHEN** game loop detects phase crossing from 2 to 3
- **THEN** main MUST call a ui_screens transition-begin entry point and MUST NOT inline transition setup details

#### Scenario: Main delegates transition frame rendering
- **WHEN** phase transition state is active
- **THEN** frame output MUST be produced by ui_screens transition render path

#### Scenario: Main delegates transition state update
- **WHEN** phase transition state is active
- **THEN** transition timing progression and completion checks MUST be executed by ui_screens transition update path

### Requirement: Transition combat behavior SHALL remain consistent after refactor
The refactor to ui_screens ownership SHALL preserve phase-transition combat semantics. During transition, attack updates and collision updates MUST stay paused, and active bullets/damage zones MUST be cleared at transition start.

#### Scenario: Pause semantics remain unchanged
- **WHEN** transition is active after refactor
- **THEN** player attack update, Boss attack update, and combat collision checks remain paused

#### Scenario: Clear semantics remain unchanged
- **WHEN** transition starts after refactor
- **THEN** active player bullets and Boss projectile/damage-zone containers are cleared once before transition rendering proceeds
