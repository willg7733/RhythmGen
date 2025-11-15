import os
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
import pygame
import json
import time

LANE_WIDTH = 100
NOTE_WIDTH = 80
NOTE_HEIGHT = 20
NOTE_SPEED = 300  # pixels per second
HIT_LINE_Y = 500
WINDOW_WIDTH = 400
WINDOW_HEIGHT = 600

KEYS = [pygame.K_a, pygame.K_s, pygame.K_d, pygame.K_f]

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

        # pre-create font once
        self.font = pygame.font.Font(None, 36)

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
        self.screen.fill((0, 0, 0))

        # Draw lanes
        for i in range(4):
            x = i * LANE_WIDTH + 10
            pygame.draw.rect(
                self.screen,
                (40, 40, 40),
                (i * LANE_WIDTH, 0, LANE_WIDTH, WINDOW_HEIGHT),
                2
            )

        # Draw hit line
        pygame.draw.line(self.screen, (255, 255, 255), (0, HIT_LINE_Y), (WINDOW_WIDTH, HIT_LINE_Y), 2)

        # Draw notes
        for note in list(self.notes):
            time_until_hit = note["time"] - current_time
            y = HIT_LINE_Y - time_until_hit * NOTE_SPEED

            # cull offscreen notes
            if y > WINDOW_HEIGHT + NOTE_HEIGHT: # Adjusted threshold
                continue
            
            # Don't render notes that have already been missed and removed
            if y < -50:
                continue

            pygame.draw.rect(
                self.screen,
                (0, 150, 255),
                (
                    note["lane"] * LANE_WIDTH + (LANE_WIDTH - NOTE_WIDTH) // 2,
                    y,
                    NOTE_WIDTH,
                    NOTE_HEIGHT
                )
            )

        # Score text
        score_text = self.font.render(f"Score: {self.score}  Combo: {self.combo}", True, (255, 255, 255))
        self.screen.blit(score_text, (10, 10))

        pygame.display.flip()

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