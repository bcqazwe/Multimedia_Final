import os
import time


class AudioManager:
    def __init__(self, base_dir=None):
        self.base_dir = base_dir or os.path.dirname(os.path.abspath(__file__))
        self.menu_music_path = os.path.join(self.base_dir, "sfx", "main.mp3")
        self.stage1_music_path = os.path.join(self.base_dir, "sfx", "stage1.mp3")
        self.stage2_music_path = os.path.join(self.base_dir, "sfx", "stage2.mp3")
        self.stage3_music_path = os.path.join(self.base_dir, "sfx", "stage3.mp3")
        self.fail_music_path = os.path.join(self.base_dir, "sfx", "fail.mp3")
        self.win_music_path = os.path.join(self.base_dir, "sfx", "win.mp3")
        self.warning_sound_path = os.path.join(self.base_dir, "sfx", "phase3_warning.mp3")
        self.get_item_sound_path = os.path.join(self.base_dir, "sfx", "get_item.mp3")
        self.menu_music_volume = 0.28
        self.stage1_music_volume = 0.26
        self.stage2_music_volume = 0.26
        self.stage3_music_volume = 0.26
        self.fail_music_volume = 0.26
        self.win_music_volume = 0.26
        self.warning_sound_volume = 0.30
        self.get_item_sound_volume = 0.36
        self.audio_channel_limit = 4
        self.sfx_cooldown_ms = 180
        self._pygame = None
        self._mixer_ready = False
        self._warning_sound = None
        self._get_item_sound = None
        self._phase3_warning_played = False
        self._menu_music_playing = False
        self._menu_music_loaded_path = None
        self._stage1_music_playing = False
        self._stage1_music_loaded_path = None
        self._stage2_music_playing = False
        self._stage2_music_loaded_path = None
        self._stage3_music_playing = False
        self._stage3_music_loaded_path = None
        self._fail_music_playing = False
        self._fail_music_loaded_path = None
        self._win_music_playing = False
        self._win_music_loaded_path = None
        self._warning_sound_channel = None
        self._get_item_sound_channel = None
        self._last_sfx_play_ms = 0
        self._last_error = None
        self._ensure_mixer()

    def _set_music_state(self, active_track=None):
        self._menu_music_playing = active_track == "menu"
        self._stage1_music_playing = active_track == "stage1"
        self._stage2_music_playing = active_track == "stage2"
        self._stage3_music_playing = active_track == "stage3"
        self._fail_music_playing = active_track == "fail"
        self._win_music_playing = active_track == "win"

    def _load_pygame(self):
        if self._pygame is not None:
            return self._pygame

        try:
            import pygame as pygame_module
        except Exception as exc:
            self._last_error = exc
            return None

        self._pygame = pygame_module
        return self._pygame

    def _ensure_mixer(self):
        if self._mixer_ready:
            return True

        pygame_module = self._load_pygame()
        if pygame_module is None:
            return False

        try:
            if not pygame_module.mixer.get_init():
                pygame_module.mixer.init()
            try:
                pygame_module.mixer.set_num_channels(self.audio_channel_limit)
            except Exception:
                pass
            self._mixer_ready = True
            return True
        except Exception as exc:
            self._last_error = exc
            self._mixer_ready = False
            return False

    def _load_warning_sound(self):
        if self._warning_sound is not None:
            return self._warning_sound

        if not self._ensure_mixer():
            return None

        if not os.path.exists(self.warning_sound_path):
            self._last_error = FileNotFoundError(self.warning_sound_path)
            return None

        try:
            self._warning_sound = self._pygame.mixer.Sound(self.warning_sound_path)
            self._warning_sound.set_volume(self.warning_sound_volume)
        except Exception as exc:
            self._last_error = exc
            self._warning_sound = None

        return self._warning_sound

    def _play_warning_sound_without_stacking(self):
        warning_sound = self._load_warning_sound()
        if warning_sound is None:
            return False

        now_ms = int(time.time() * 1000)
        if now_ms - self._last_sfx_play_ms < self.sfx_cooldown_ms:
            return False

        if self._warning_sound_channel is None:
            try:
                self._warning_sound_channel = self._pygame.mixer.find_channel(False)
            except Exception as exc:
                self._last_error = exc
                return False

        if self._warning_sound_channel is None or self._warning_sound_channel.get_busy():
            return False

        try:
            self._warning_sound_channel.play(warning_sound)
            self._last_sfx_play_ms = now_ms
            return True
        except Exception as exc:
            self._last_error = exc
            return False

    def _load_get_item_sound(self):
        if self._get_item_sound is not None:
            return self._get_item_sound

        if not self._ensure_mixer():
            return None

        if not os.path.exists(self.get_item_sound_path):
            self._last_error = FileNotFoundError(self.get_item_sound_path)
            return None

        try:
            self._get_item_sound = self._pygame.mixer.Sound(self.get_item_sound_path)
            self._get_item_sound.set_volume(self.get_item_sound_volume)
        except Exception as exc:
            self._last_error = exc
            self._get_item_sound = None

        return self._get_item_sound

    def play_get_item_sound_once(self):
        get_item_sound = self._load_get_item_sound()
        if get_item_sound is None:
            return False

        if self._get_item_sound_channel is None:
            try:
                self._get_item_sound_channel = self._pygame.mixer.find_channel(True)
            except Exception as exc:
                self._last_error = exc
                return False

        if self._get_item_sound_channel is None:
            return False

        try:
            self._get_item_sound_channel.play(get_item_sound)
            return True
        except Exception as exc:
            self._last_error = exc
            return False

    def play_phase3_warning_once(self):
        if self._phase3_warning_played:
            return False

        self._phase3_warning_played = True
        return self._play_warning_sound_without_stacking()

    def play_menu_music(self, fade_ms=1200):
        if self._menu_music_playing:
            return True

        if not self._ensure_mixer():
            return False

        if not os.path.exists(self.menu_music_path):
            self._last_error = FileNotFoundError(self.menu_music_path)
            return False

        try:
            if self._menu_music_loaded_path != self.menu_music_path:
                self._pygame.mixer.music.load(self.menu_music_path)
                self._menu_music_loaded_path = self.menu_music_path
            self._pygame.mixer.music.set_volume(self.menu_music_volume)
            self._pygame.mixer.music.play(loops=-1, fade_ms=max(0, int(fade_ms)))
            self._set_music_state("menu")
            return True
        except Exception as exc:
            self._last_error = exc
            self._set_music_state(None)
            return False

    def play_stage1_music(self, fade_ms=1200):
        if self._stage1_music_playing:
            return True

        if not self._ensure_mixer():
            return False

        if not os.path.exists(self.stage1_music_path):
            self._last_error = FileNotFoundError(self.stage1_music_path)
            return False

        try:
            if self._stage1_music_loaded_path != self.stage1_music_path:
                self._pygame.mixer.music.load(self.stage1_music_path)
                self._stage1_music_loaded_path = self.stage1_music_path
            self._pygame.mixer.music.set_volume(self.stage1_music_volume)
            self._pygame.mixer.music.play(loops=-1, fade_ms=max(0, int(fade_ms)))
            self._set_music_state("stage1")
            return True
        except Exception as exc:
            self._last_error = exc
            self._set_music_state(None)
            return False

    def play_stage2_music(self, fade_ms=1200):
        if self._stage2_music_playing:
            return True

        if not self._ensure_mixer():
            return False

        if not os.path.exists(self.stage2_music_path):
            self._last_error = FileNotFoundError(self.stage2_music_path)
            return False

        try:
            if self._stage2_music_loaded_path != self.stage2_music_path:
                self._pygame.mixer.music.load(self.stage2_music_path)
                self._stage2_music_loaded_path = self.stage2_music_path
            self._pygame.mixer.music.set_volume(self.stage2_music_volume)
            self._pygame.mixer.music.play(loops=-1, fade_ms=max(0, int(fade_ms)))
            self._set_music_state("stage2")
            return True
        except Exception as exc:
            self._last_error = exc
            self._set_music_state(None)
            return False

    def play_stage3_music(self, fade_ms=1200):
        if self._stage3_music_playing:
            return True

        if not self._ensure_mixer():
            return False

        if not os.path.exists(self.stage3_music_path):
            self._last_error = FileNotFoundError(self.stage3_music_path)
            return False

        try:
            if self._stage3_music_loaded_path != self.stage3_music_path:
                self._pygame.mixer.music.load(self.stage3_music_path)
                self._stage3_music_loaded_path = self.stage3_music_path
            self._pygame.mixer.music.set_volume(self.stage3_music_volume)
            self._pygame.mixer.music.play(loops=-1, fade_ms=max(0, int(fade_ms)))
            self._set_music_state("stage3")
            return True
        except Exception as exc:
            self._last_error = exc
            self._set_music_state(None)
            return False

    def play_fail_music(self, fade_ms=1200):
        if self._fail_music_playing:
            return True

        if not self._ensure_mixer():
            return False

        if not os.path.exists(self.fail_music_path):
            self._last_error = FileNotFoundError(self.fail_music_path)
            return False

        try:
            if self._fail_music_loaded_path != self.fail_music_path:
                self._pygame.mixer.music.load(self.fail_music_path)
                self._fail_music_loaded_path = self.fail_music_path
            self._pygame.mixer.music.set_volume(self.fail_music_volume)
            self._pygame.mixer.music.play(loops=-1, fade_ms=max(0, int(fade_ms)))
            self._set_music_state("fail")
            return True
        except Exception as exc:
            self._last_error = exc
            self._set_music_state(None)
            return False

    def play_win_music(self, fade_ms=1200):
        if self._win_music_playing:
            return True

        if not self._ensure_mixer():
            return False

        if not os.path.exists(self.win_music_path):
            self._last_error = FileNotFoundError(self.win_music_path)
            return False

        try:
            if self._win_music_loaded_path != self.win_music_path:
                self._pygame.mixer.music.load(self.win_music_path)
                self._win_music_loaded_path = self.win_music_path
            self._pygame.mixer.music.set_volume(self.win_music_volume)
            self._pygame.mixer.music.play(loops=-1, fade_ms=max(0, int(fade_ms)))
            self._set_music_state("win")
            return True
        except Exception as exc:
            self._last_error = exc
            self._set_music_state(None)
            return False

    def fadeout_menu_music(self, fade_ms=1200):
        if not self._menu_music_playing:
            return False

        try:
            if self._pygame is not None:
                self._pygame.mixer.music.fadeout(max(0, int(fade_ms)))
        except Exception as exc:
            self._last_error = exc
            return False
        finally:
            self._set_music_state(None)

        return True

    def fadeout_stage1_music(self, fade_ms=1200):
        if not self._stage1_music_playing:
            return False

        try:
            if self._pygame is not None:
                self._pygame.mixer.music.fadeout(max(0, int(fade_ms)))
        except Exception as exc:
            self._last_error = exc
            return False
        finally:
            self._set_music_state(None)

        return True

    def fadeout_stage2_music(self, fade_ms=1200):
        if not self._stage2_music_playing:
            return False

        try:
            if self._pygame is not None:
                self._pygame.mixer.music.fadeout(max(0, int(fade_ms)))
        except Exception as exc:
            self._last_error = exc
            return False
        finally:
            self._set_music_state(None)

        return True

    def fadeout_stage3_music(self, fade_ms=1200):
        if not self._stage3_music_playing:
            return False

        try:
            if self._pygame is not None:
                self._pygame.mixer.music.fadeout(max(0, int(fade_ms)))
        except Exception as exc:
            self._last_error = exc
            return False
        finally:
            self._set_music_state(None)

        return True

    def stop_all_music(self):
        stopped = False

        try:
            if self._pygame is not None and self._pygame.mixer.get_init():
                self._pygame.mixer.music.stop()
                stopped = True
                if self._warning_sound_channel is not None:
                    self._warning_sound_channel.stop()
                if self._get_item_sound_channel is not None:
                    self._get_item_sound_channel.stop()
        except Exception as exc:
            self._last_error = exc
        finally:
            self._set_music_state(None)
            self._warning_sound_channel = None
            self._get_item_sound_channel = None

        return stopped

    def stop_bgm(self):
        stopped = False

        try:
            if self._pygame is not None and self._pygame.mixer.get_init():
                self._pygame.mixer.music.stop()
                stopped = True
        except Exception as exc:
            self._last_error = exc
        finally:
            self._set_music_state(None)

        return stopped

    def reset_phase3_warning_guard(self):
        self._phase3_warning_played = False

    @property
    def mixer_ready(self):
        return self._mixer_ready

    @property
    def last_error(self):
        return self._last_error