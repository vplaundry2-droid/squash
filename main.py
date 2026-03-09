import math
import random
import sys
from dataclasses import dataclass

import pygame
from pygame.math import Vector2


WIDTH, HEIGHT = 1280, 720
FPS = 120

# Court dimensions in meters (scaled to pixels).
COURT_WIDTH_M = 6.4
COURT_LENGTH_M = 9.75
COURT_HEIGHT_M = 5.64
SCALE = 90  # px per meter

COURT_W = int(COURT_WIDTH_M * SCALE)
COURT_L = int(COURT_LENGTH_M * SCALE)

LEFT_WALL_X = (WIDTH - COURT_W) // 2
RIGHT_WALL_X = LEFT_WALL_X + COURT_W
FRONT_WALL_Y = 80
BACK_WALL_Y = FRONT_WALL_Y + COURT_L
FLOOR_Y = HEIGHT - 70

TIN_HEIGHT_M = 0.48
SERVICE_LINE_M = 1.78
OUT_LINE_M = 4.57

TIN_Y = FLOOR_Y - int(TIN_HEIGHT_M * SCALE)
SERVICE_Y = FLOOR_Y - int(SERVICE_LINE_M * SCALE)
OUT_LINE_Y = FLOOR_Y - int(OUT_LINE_M * SCALE)

GRAVITY = 28.0  # m/s^2
BALL_RADIUS_M = 0.035
BALL_RADIUS = int(BALL_RADIUS_M * SCALE)

PLAYER_RADIUS = 28
PLAYER_SPEED = 6.5  # m/s
PLAYER_ACCEL = 30.0
PLAYER_FRICTION = 12.0
HIT_RANGE = 115


@dataclass
class ScoreState:
    player: int = 0
    ai: int = 0
    server: str = "player"
    game_over: bool = False
    winner: str | None = None


class Ball:
    def __init__(self):
        self.pos = Vector2(WIDTH // 2, FLOOR_Y - 180)
        self.vel = Vector2(0, 0)
        self.in_play = False
        self.floor_bounces = 0
        self.hit_by = None
        self.last_front_wall_hit = False

    def reset_for_serve(self, server: str):
        x = WIDTH * 0.42 if server == "player" else WIDTH * 0.58
        self.pos = Vector2(x, FLOOR_Y - 120)
        self.vel = Vector2(0, 0)
        self.in_play = False
        self.floor_bounces = 0
        self.hit_by = None
        self.last_front_wall_hit = False

    def serve(self, direction: float):
        speed = random.uniform(16.0, 20.0)
        vx = math.cos(direction) * speed
        vy = -math.sin(direction) * speed
        self.vel = Vector2(vx, vy)
        self.in_play = True
        self.floor_bounces = 0
        self.last_front_wall_hit = False

    def update(self, dt: float):
        if not self.in_play:
            return

        self.vel.y += GRAVITY * dt
        self.pos += self.vel * SCALE * dt

        # Side wall collisions
        if self.pos.x - BALL_RADIUS < LEFT_WALL_X:
            self.pos.x = LEFT_WALL_X + BALL_RADIUS
            self.vel.x *= -0.92
        elif self.pos.x + BALL_RADIUS > RIGHT_WALL_X:
            self.pos.x = RIGHT_WALL_X - BALL_RADIUS
            self.vel.x *= -0.92

        # Front wall collision (must be above tin)
        if self.pos.y - BALL_RADIUS < FRONT_WALL_Y:
            self.pos.y = FRONT_WALL_Y + BALL_RADIUS
            self.vel.y *= -0.96
            self.last_front_wall_hit = True

        # Back wall collision
        if self.pos.y + BALL_RADIUS > BACK_WALL_Y:
            self.pos.y = BACK_WALL_Y - BALL_RADIUS
            self.vel.y *= -0.85

        # Floor collision/bounce
        if self.pos.y + BALL_RADIUS >= FLOOR_Y:
            self.pos.y = FLOOR_Y - BALL_RADIUS
            self.vel.y *= -0.68
            self.vel.x *= 0.96
            self.floor_bounces += 1

            # Kill tiny bounces to avoid jitter
            if abs(self.vel.y) < 1.6:
                self.vel.y = 0


class Player:
    def __init__(self):
        self.pos = Vector2(WIDTH * 0.44, FLOOR_Y - PLAYER_RADIUS)
        self.vel = Vector2(0, 0)

    def update(self, dt: float, keys):
        desired = Vector2(0, 0)
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            desired.x -= 1
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            desired.x += 1
        if keys[pygame.K_w] or keys[pygame.K_UP]:
            desired.y -= 1
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:
            desired.y += 1

        if desired.length_squared() > 0:
            desired = desired.normalize() * PLAYER_SPEED * SCALE
            accel = (desired - self.vel) * min(1.0, PLAYER_ACCEL * dt)
            self.vel += accel
        else:
            self.vel *= max(0.0, 1.0 - PLAYER_FRICTION * dt)

        self.pos += self.vel * dt

        self.pos.x = max(LEFT_WALL_X + PLAYER_RADIUS, min(RIGHT_WALL_X - PLAYER_RADIUS, self.pos.x))
        self.pos.y = max(FRONT_WALL_Y + 230, min(BACK_WALL_Y - PLAYER_RADIUS, self.pos.y))


class AIPlayer:
    def __init__(self):
        self.pos = Vector2(WIDTH * 0.56, FLOOR_Y - PLAYER_RADIUS)
        self.vel = Vector2(0, 0)

    def update(self, dt: float, ball: Ball):
        target = Vector2(WIDTH * 0.56, FRONT_WALL_Y + COURT_L * 0.42)
        if ball.in_play:
            # Move toward expected interception point near back half.
            target = Vector2(
                max(LEFT_WALL_X + PLAYER_RADIUS, min(RIGHT_WALL_X - PLAYER_RADIUS, ball.pos.x + random.uniform(-20, 20))),
                max(FRONT_WALL_Y + 230, min(BACK_WALL_Y - PLAYER_RADIUS, ball.pos.y + 120)),
            )

        desired = target - self.pos
        if desired.length_squared() > 15:
            desired = desired.normalize() * PLAYER_SPEED * 0.86 * SCALE
            self.vel += (desired - self.vel) * min(1.0, PLAYER_ACCEL * 0.8 * dt)
        else:
            self.vel *= max(0.0, 1.0 - PLAYER_FRICTION * dt)

        self.pos += self.vel * dt
        self.pos.x = max(LEFT_WALL_X + PLAYER_RADIUS, min(RIGHT_WALL_X - PLAYER_RADIUS, self.pos.x))
        self.pos.y = max(FRONT_WALL_Y + 230, min(BACK_WALL_Y - PLAYER_RADIUS, self.pos.y))


class Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Squash Sim")
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("consolas", 22)
        self.big = pygame.font.SysFont("consolas", 38, bold=True)

        self.player = Player()
        self.ai = AIPlayer()
        self.ball = Ball()
        self.score = ScoreState()
        self.ball.reset_for_serve(self.score.server)

    def swing(self, hitter: str):
        actor = self.player if hitter == "player" else self.ai
        to_ball = self.ball.pos - actor.pos
        if to_ball.length() > HIT_RANGE:
            return False

        toward_front = Vector2(0, -1)
        side = random.uniform(-0.6, 0.6)
        power = random.uniform(18, 24)
        hit_vec = Vector2(side, toward_front.y).normalize() * power

        # add lift if ball is low
        if self.ball.pos.y > FLOOR_Y - 140:
            hit_vec.y -= random.uniform(4.0, 7.0)

        self.ball.vel = hit_vec
        self.ball.in_play = True
        self.ball.floor_bounces = 0
        self.ball.hit_by = hitter
        self.ball.last_front_wall_hit = False
        return True

    def rule_fault(self):
        # Ball must hit front wall above tin and bounce at most once
        if self.ball.floor_bounces > 1:
            return True
        if self.ball.pos.y <= TIN_Y and self.ball.last_front_wall_hit:
            return False
        # If ball reaches back dead area too low without front-wall hit since last shot
        if self.ball.pos.y > BACK_WALL_Y - 4 and not self.ball.last_front_wall_hit:
            return True
        return False

    def award_point(self, winner: str):
        if winner == "player":
            self.score.player += 1
        else:
            self.score.ai += 1

        self.score.server = winner

        if (self.score.player >= 11 or self.score.ai >= 11) and abs(self.score.player - self.score.ai) >= 2:
            self.score.game_over = True
            self.score.winner = winner

        self.ball.reset_for_serve(self.score.server)

    def update(self, dt: float):
        keys = pygame.key.get_pressed()
        self.player.update(dt, keys)
        self.ai.update(dt, self.ball)
        self.ball.update(dt)

        if not self.score.game_over:
            # Serve controls
            if not self.ball.in_play:
                if self.score.server == "player" and keys[pygame.K_SPACE]:
                    self.ball.serve(direction=math.radians(80))
                    self.ball.hit_by = "player"
                elif self.score.server == "ai":
                    self.ball.serve(direction=math.radians(100))
                    self.ball.hit_by = "ai"

            # Player swing
            if keys[pygame.K_j]:
                self.swing("player")

            # AI swing when close and ball on its side
            if self.ball.in_play and (self.ball.pos - self.ai.pos).length() < HIT_RANGE * 0.9 and self.ball.pos.y > FRONT_WALL_Y + 140:
                if random.random() < 0.18:
                    self.swing("ai")

            # Rule checks
            if self.rule_fault():
                winner = "ai" if self.ball.hit_by == "player" else "player"
                self.award_point(winner)

            # Out of bounds by side/top (approx)
            if self.ball.pos.y < OUT_LINE_Y - 15:
                winner = "ai" if self.ball.hit_by == "player" else "player"
                self.award_point(winner)

    def draw_court(self):
        s = self.screen
        s.fill((18, 22, 28))

        # Glass/back area
        pygame.draw.rect(s, (35, 45, 60), (LEFT_WALL_X, FRONT_WALL_Y, COURT_W, COURT_L))
        pygame.draw.rect(s, (90, 100, 120), (LEFT_WALL_X, FLOOR_Y, COURT_W, HEIGHT - FLOOR_Y))

        # Court lines
        pygame.draw.rect(s, (220, 220, 220), (LEFT_WALL_X, FRONT_WALL_Y, COURT_W, COURT_L), 2)
        pygame.draw.line(s, (230, 70, 70), (LEFT_WALL_X, TIN_Y), (RIGHT_WALL_X, TIN_Y), 2)
        pygame.draw.line(s, (250, 250, 250), (LEFT_WALL_X, SERVICE_Y), (RIGHT_WALL_X, SERVICE_Y), 2)
        pygame.draw.line(s, (220, 220, 220), (LEFT_WALL_X, OUT_LINE_Y), (RIGHT_WALL_X, OUT_LINE_Y), 2)
        pygame.draw.line(s, (200, 200, 200), (WIDTH // 2, FLOOR_Y), (WIDTH // 2, BACK_WALL_Y), 1)

        # Front wall shading for depth cue
        pygame.draw.rect(s, (210, 210, 215), (LEFT_WALL_X, FRONT_WALL_Y - 14, COURT_W, 14))

    def draw(self):
        self.draw_court()

        # Ball shadow
        shadow_y = FLOOR_Y
        shadow_x = self.ball.pos.x
        pygame.draw.circle(self.screen, (30, 30, 30), (int(shadow_x), int(shadow_y - 2)), BALL_RADIUS + 4)

        # Ball
        pygame.draw.circle(self.screen, (255, 245, 90), (int(self.ball.pos.x), int(self.ball.pos.y)), BALL_RADIUS)

        # Players
        pygame.draw.circle(self.screen, (80, 200, 255), (int(self.player.pos.x), int(self.player.pos.y)), PLAYER_RADIUS)
        pygame.draw.circle(self.screen, (255, 120, 120), (int(self.ai.pos.x), int(self.ai.pos.y)), PLAYER_RADIUS)

        # UI
        score = self.big.render(f"You {self.score.player}  -  {self.score.ai} AI", True, (245, 245, 245))
        self.screen.blit(score, (40, 20))

        help_txt = "Move: WASD/Arrows | Swing: J | Serve: SPACE"
        self.screen.blit(self.font.render(help_txt, True, (220, 220, 220)), (40, HEIGHT - 40))

        server_text = self.font.render(f"Server: {self.score.server.upper()}", True, (200, 220, 255))
        self.screen.blit(server_text, (40, 70))

        if self.score.game_over:
            msg = self.big.render(f"{self.score.winner.upper()} WINS! Press R to restart", True, (255, 230, 120))
            self.screen.blit(msg, (WIDTH // 2 - msg.get_width() // 2, 120))

        pygame.display.flip()

    def restart(self):
        self.player = Player()
        self.ai = AIPlayer()
        self.ball = Ball()
        self.score = ScoreState()
        self.ball.reset_for_serve(self.score.server)

    def run(self):
        while True:
            dt = self.clock.tick(FPS) / 1000.0

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit(0)
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        pygame.quit()
                        sys.exit(0)
                    if event.key == pygame.K_r and self.score.game_over:
                        self.restart()

            self.update(dt)
            self.draw()


if __name__ == "__main__":
    Game().run()
