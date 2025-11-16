import os
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
import pygame
import json

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
        pygame.mixer.pre_init(frequency=44100, size=-16, channels=2, buffer=512)
        pygame.init()

        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("RhythmGen")

        self.notes = beatmap[:]  # copy

        self.song = pygame.mixer.Sound(audio_path)

        self.latency_offset = latency_offset
        self.score = 0
        self.combo = 0

        # We need a variable to store when the music started.
        self.start_time = 0

        # pre-create font once
        self.font = pygame.font.Font(None, 36)

    def run(self):
        clock = pygame.time.Clock()

        # Play the Sound object and record the start time.
        self.song.play()
        self.start_time = pygame.time.get_ticks()

        running = True
        while running:

            # The game clock is based on how long it's been since self.start_time.
            current_time = ((pygame.time.get_ticks() - self.start_time) / 1000.0) + self.latency_offset

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

                if event.type == pygame.KEYDOWN:
                    if event.key in KEYS:
                        lane = KEYS.index(event.key)
                        self.check_hit(lane, current_time)
            
            # Check for missed notes
            self.check_misses(current_time)

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
    
    def check_misses(self, current_time):
        # Time after which a note is considered a "miss"
        miss_threshold = 0.2  # seconds past the hit time
        
        # Iterate over a copy
        for note in self.notes[:]:
            if current_time > note["time"] + miss_threshold:
                self.combo = 0
                try:
                    self.notes.remove(note)
                except ValueError:
                    pass

    def render(self, current_time):
        self.screen.fill((0, 0, 0))

        # Draw lanes
        for i in range(4):
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
            if y > WINDOW_HEIGHT + NOTE_HEIGHT:
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