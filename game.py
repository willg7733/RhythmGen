import os
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
import pygame
import json
import time

LANE_WIDTH = 200
NOTE_WIDTH = 160
NOTE_HEIGHT = 40
NOTE_SPEED = 300  # pixels per second
HIT_LINE_Y = 1000
WINDOW_WIDTH = 800
WINDOW_HEIGHT = 1200

KEYS = [pygame.K_a, pygame.K_s, pygame.K_d, pygame.K_f]
LANE_LABELS = ["A", "S", "D", "F"]

class RhythmGame:
    def __init__(self, beatmap, audio_path, latency_offset=0.0):
        """
        latency_offset: seconds to add/subtract from mixer-reported time to account for audio latency
        (positive -> game thinks audio is later, negative -> game thinks audio is earlier).
        Tune this if hits feel consistently early/late.
        """
        # --- CHANGED ---
        # We must initialize the mixer *before* pygame.init()
        # to ensure our settings (like 44100Hz) are used.
        pygame.mixer.pre_init(frequency=44100, size=-16, channels=2, buffer=512)
        pygame.init()
        # --- END CHANGE ---

        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("AutoBeat")

        self.notes = beatmap[:]  # copy

        # --- CHANGED ---
        # Load the audio as a Sound object, not streaming music.
        # This fixes the WAV/MP3 loading error.
        self.song = pygame.mixer.Sound(audio_path)
        # --- END CHANGE ---

        self.latency_offset = latency_offset
        self.score = 0
        self.combo = 0

        # --- CHANGED ---
        # We need a variable to store when the music started.
        self.start_time = 0
        # --- END CHANGE ---

        # pre-create monospace fonts for ASCII rendering
        mono_candidates = ["couriernew", "courier", "consolas", "lucidaconsole", "menlo", "monospace"]
        font_path = None
        for candidate in mono_candidates:
            match = pygame.font.match_font(candidate)
            if match:
                font_path = match
                break

        base_ascii_size = 28 * 2
        base_ui_size = 22 * 2
        if font_path:
            self.ascii_font = pygame.font.Font(font_path, base_ascii_size)
            self.ui_font = pygame.font.Font(font_path, base_ui_size)
        else:
            self.ascii_font = pygame.font.Font(None, base_ascii_size)
            self.ui_font = pygame.font.Font(None, base_ui_size)

        self.char_width = self.ascii_font.size("M")[0]
        self.char_height = self.ascii_font.get_height()
        self._ascii_cache = {}

    def run(self):
        clock = pygame.time.Clock()

        # --- CHANGED ---
        # Play the Sound object and record the start time.
        self.song.play()
        self.start_time = pygame.time.get_ticks()
        # --- END CHANGE ---

        running = True
        while running:
            dt = clock.tick(60) / 1000.0

            # --- CHANGED ---
            # The game clock is now based on how long it's been
            # since we recorded self.start_time.
            current_time = ((pygame.time.get_ticks() - self.start_time) / 1000.0) + self.latency_offset
            # --- END CHANGE ---

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

                if event.type == pygame.KEYDOWN:
                    if event.key in KEYS:
                        lane = KEYS.index(event.key)
                        self.check_hit(lane, current_time)
            
            # --- NEW ---
            # Check for missed notes
            self.check_misses(current_time)
            # --- END NEW ---

            self.render(current_time)

        pygame.quit()

    def check_hit(self, lane, current_time):
        hit_window = 0.15  # seconds tolerance

        # iterate over a copy so removal doesn't break iteration
        for note in self.notes[:]:
            # Only check notes that are close to the hit line
            time_diff = note["time"] - current_time
            if note["lane"] == lane and abs(time_diff) <= hit_window:
                self.score += 100
                self.combo += 1
                try:
                    self.notes.remove(note)
                except ValueError:
                    pass
                return

        # no hit found
        self.combo = 0
    
    # --- NEW ---
    # Added a function to reset combo on missed notes
    def check_misses(self, current_time):
        # Time after which a note is considered a "miss"
        miss_threshold = 0.2 # seconds *past* the hit time
        
        # Iterate over a copy
        for note in self.notes[:]:
            if current_time > note["time"] + miss_threshold:
                self.combo = 0
                try:
                    self.notes.remove(note)
                except ValueError:
                    pass
    # --- END NEW ---


    def render(self, current_time):
        self.screen.fill((5, 5, 5))

        self._draw_lane_boundaries()
        self._draw_hit_line()
        self._draw_lane_labels()
        self._draw_notes(current_time)
        self._draw_hud()

        pygame.display.flip()

    def _draw_lane_boundaries(self):
        color = (80, 200, 120)
        for lane in range(5):
            x = lane * LANE_WIDTH - self.char_width // 2
            x = max(0, min(WINDOW_WIDTH - self.char_width, x))
            for y in range(0, WINDOW_HEIGHT, self.char_height):
                self._draw_ascii("|", x, y, color)

    def _draw_hit_line(self):
        repeats = WINDOW_WIDTH // self.char_width + 2
        line = "=" * repeats
        y = HIT_LINE_Y - self.char_height // 2
        self._draw_ascii(line, 0, y, (255, 255, 255))

    def _draw_lane_labels(self):
        baseline = WINDOW_HEIGHT - self.char_height * 1.5
        for idx, label in enumerate(LANE_LABELS):
            x_center = idx * LANE_WIDTH + LANE_WIDTH // 2 - self.char_width // 2
            self._draw_ascii(f"[{label}]", x_center - self.char_width // 2, baseline, (200, 200, 200))

    def _draw_notes(self, current_time):
        for note in list(self.notes):
            time_until_hit = note["time"] - current_time
            y = HIT_LINE_Y - time_until_hit * NOTE_SPEED

            if y > WINDOW_HEIGHT + self.char_height * 2:
                continue
            if y < -self.char_height * 2:
                continue

            if abs(time_until_hit) <= 0.08:
                symbol = "<=>"
                color = (255, 230, 120)
            else:
                symbol = "[ ]"
                color = (0, 200, 255)

            text_width = len(symbol) * self.char_width
            x_center = note["lane"] * LANE_WIDTH + LANE_WIDTH // 2 - text_width // 2
            y_offset = y - self.char_height // 2
            self._draw_ascii(symbol, x_center, y_offset, color)

    def _draw_hud(self):
        hud = f"Score: {self.score:06d}  Combo: {self.combo:03d}"
        text_surface = self.ui_font.render(hud, True, (255, 255, 255))
        self.screen.blit(text_surface, (10, 10))

    def _draw_ascii(self, text, x, y, color):
        key = (text, color)
        if key not in self._ascii_cache:
            self._ascii_cache[key] = self.ascii_font.render(text, True, color)
        self.screen.blit(self._ascii_cache[key], (int(x), int(y)))

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        # --- CHANGED ---
        # Updated usage to reflect new .wav file requirement
        print("Usage: python game.py beatmap.json audio.wav") 
        # --- END CHANGE ---
        sys.exit(1)

    beatmap_file = sys.argv[1]
    audio_file = sys.argv[2]
    
    if not os.path.exists(audio_file):
        print(f"Error: Audio file not found at {audio_file}")
        sys.exit(1)
    if not os.path.exists(beatmap_file):
        print(f"Error: Beatmap file not found at {beatmap_file}")
        sys.exit(1)

    with open(beatmap_file, "r") as f:
        beatmap = json.load(f)

    game = RhythmGame(beatmap, audio_file, latency_offset=0.0)
    game.run()