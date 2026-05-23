## ADDED Requirements

### Requirement: Soft pulse phase 1-to-2 transition
The system SHALL trigger a lightweight phase transition when the Boss crosses from phase 1 into phase 2.
The transition SHALL last for 5 seconds.
The transition SHALL present a soft pulse visual treatment that is clearly lighter than the existing phase 2-to-3 glitch transition.

#### Scenario: Phase 1 crosses into phase 2
- **WHEN** the Boss HP crosses the phase 1 to phase 2 threshold
- **THEN** the system SHALL enter a dedicated transition state for 5 seconds
- **AND** the visual treatment SHALL be a soft pulse effect rather than a glitch effect

#### Scenario: Transition finishes
- **WHEN** the 5-second transition duration elapses
- **THEN** the system SHALL resume normal gameplay in phase 2

### Requirement: Transition freezes combat and clears bullets
During the phase 1-to-2 transition, the system SHALL pause both player and Boss action updates.
During the same transition, the system SHALL clear visible bullets and active projectile hazards from the screen.

#### Scenario: Transition starts
- **WHEN** the phase 1-to-2 transition begins
- **THEN** player firing and Boss attack updates SHALL be paused
- **AND** active bullets and on-screen projectile hazards SHALL be cleared

#### Scenario: Transition remains active
- **WHEN** the transition is still active
- **THEN** no new bullets or projectile hazards SHALL be spawned until phase 2 resumes
