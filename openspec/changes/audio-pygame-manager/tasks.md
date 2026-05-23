## 1. Setup

- [x] 1.1 Add `pygame` as a project dependency for audio playback
- [x] 1.2 Create a new `audio.py` module as the centralized audio entry point

## 2. Core Implementation

- [x] 2.1 Implement `pygame.mixer` initialization and graceful fallback behavior in `audio.py`
- [x] 2.2 Implement loading and one-shot playback for `sfx/phase3_warning.mp3`
- [x] 2.3 Add a small guard so the warning cue triggers only once per phase 2->3 transition

## 3. Game Integration

- [x] 3.1 Wire the phase 2->3 crossing point in `main.py` to call the audio manager
- [x] 3.2 Keep the phase 2->3 glitch transition behavior unchanged while adding sound playback
- [x] 3.3 Ensure audio playback does not block rendering or combat updates

## 4. Verification

- [x] 4.1 Run syntax and import checks for the touched modules
- [x] 4.2 Verify the warning cue plays once when phase 2 becomes phase 3
- [x] 4.3 Verify the game still runs when audio initialization fails
