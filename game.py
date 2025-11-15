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
        pygame.init()
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("AutoBeat")

        self.notes = beatmap[:]  # copy
        self.audio_path = audio_path
        self.latency_offset = latency_offset
        self.score = 0
        self.combo = 0

        # pre-create font once
        self.font = pygame.font.Font(None, 36)

    def run(self):
        clock = pygame.time.Clock()

        pygame.mixer.music.load(self.audio_path)
        pygame.mixer.music.play()

        # We'll compute current_time from mixer.get_pos() every frame.
        # mixer.get_pos() -> milliseconds since music.play() began (may be -1 on some backends)
        running = True
        while running:
            dt = clock.tick(60) / 1000.0

            # Prefer audio device clock for sync; fallback to pygame time if get_pos() is unavailable
            pos_ms = pygame.mixer.music.get_pos()  # milliseconds
            if pos_ms is not None and pos_ms >= 0:
                current_time = pos_ms / 1000.0 + self.latency_offset
            else:
                # fallback: use pygame time since start of run (less accurate for strict audio sync)
                current_time = pygame.time.get_ticks() / 1000.0 + self.latency_offset

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

                if event.type == pygame.KEYDOWN:
                    if event.key in KEYS:
                        lane = KEYS.index(event.key)
                        self.check_hit(lane, current_time)

            self.render(current_time)

        pygame.quit()

    def check_hit(self, lane, current_time):
        hit_window = 0.15  # seconds tolerance

        # iterate over a copy so removal doesn't break iteration
        for note in self.notes[:]:
            if note["lane"] == lane and abs(note["time"] - current_time) <= hit_window:
                self.score += 100
                self.combo += 1
                try:
                    self.notes.remove(note)
                except ValueError:
                    pass
                return

        # no hit found
        self.combo = 0

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
            if y > WINDOW_HEIGHT or y < -50:
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
        score_text = self.font.render(f"Score: {self.score}  Combo: {self.combo}  Notes left: {len(self.notes)}", True, (255, 255, 255))
        self.screen.blit(score_text, (10, 10))

        pygame.display.flip()

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: python game.py beatmap.json audio.mp3")
        sys.exit(1)

    beatmap_file = sys.argv[1]
    audio_file = sys.argv[2]

    with open(beatmap_file, "r") as f:
        beatmap = json.load(f)

    game = RhythmGame(beatmap, audio_file, latency_offset=0.0)
    game.run()
