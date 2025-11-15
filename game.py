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
    def __init__(self, beatmap, audio_path):
        pygame.init()
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("AutoBeat")

        self.notes = beatmap
        self.audio_path = audio_path
        self.start_time = None
        self.score = 0
        self.combo = 0

    def run(self):
        clock = pygame.time.Clock()

        pygame.mixer.music.load(self.audio_path)
        pygame.mixer.music.play()

        self.start_time = time.time()

        running = True
        while running:
            dt = clock.tick(60) / 1000.0
            current_time = time.time() - self.start_time

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
        hit_window = 0.15

        for note in self.notes:
            if note["lane"] == lane and abs(note["time"] - current_time) < hit_window:
                self.score += 100
                self.combo += 1
                self.notes.remove(note)
                return

        self.combo = 0  # miss

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
        for note in self.notes:
            time_until_hit = note["time"] - current_time
            y = HIT_LINE_Y - time_until_hit * NOTE_SPEED

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
        font = pygame.font.Font(None, 36)
        score_text = font.render(f"Score: {self.score}  Combo: {self.combo}", True, (255, 255, 255))
        self.screen.blit(score_text, (10, 10))

        pygame.display.flip()

