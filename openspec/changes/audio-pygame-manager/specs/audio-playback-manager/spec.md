## ADDED Requirements

### Requirement: Centralized audio playback manager
The system SHALL provide a centralized audio playback manager for game sound effects.
The audio manager SHALL use `pygame` to load and play audio cues.
The audio manager SHALL allow the game to trigger audio cues without blocking the render loop.

#### Scenario: Audio manager is initialized
- **WHEN** the game starts and the audio manager is created
- **THEN** the system SHALL initialize `pygame.mixer` if an audio device is available
- **AND** the system SHALL keep gameplay running even if audio initialization fails

#### Scenario: Audio cue is played
- **WHEN** the game requests an audio cue through the audio manager
- **THEN** the system SHALL play the cue asynchronously
- **AND** the main game loop SHALL continue updating and rendering normally

### Requirement: Phase 2-to-3 warning sound cue
The system SHALL play a warning sound cue when the Boss transitions from phase 2 to phase 3.
The warning cue SHALL be triggered once per transition.
The warning cue SHALL use the `sfx/phase3_warning.mp3` asset.

#### Scenario: Phase 2 crosses into phase 3
- **WHEN** the Boss HP crosses the phase 2 to phase 3 threshold
- **THEN** the system SHALL trigger `sfx/phase3_warning.mp3` once
- **AND** the sound cue SHALL not block the phase transition or visual glitch effect

#### Scenario: Transition does not retrigger repeatedly
- **WHEN** the phase 2-to-3 transition remains active for multiple frames
- **THEN** the warning cue SHALL not restart on every frame
- **AND** the cue SHALL remain a single transition event
