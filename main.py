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
AIR_DRAG = 0.08
SPIN_DECAY = 0.92

PLAYER_RADIUS = 28
PLAYER_SPEED = 6.5  # m/s
PLAYER_ACCEL = 30.0
PLAYER_FRICTION = 12.0
HIT_RANGE = 115
MAX_CHARGE = 1.0


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
        self.spin = 0.0

    def reset_for_serve(self, server: str):
        x = WIDTH * 0.42 if server == "player" else WIDTH * 0.58
        self.pos = Vector2(x, FLOOR_Y - 120)
        self.vel = Vector2(0, 0)
        self.in_play = False
        self.floor_bounces = 0
        self.hit_by = None
        self.last_front_wall_hit = False
        self.spin = 0.0

    def serve(self, direction: float):
        speed = random.uniform(16.0, 20.0)
        vx = math.cos(direction) * speed
        vy = -math.sin(direction) * speed
        self.vel = Vector2(vx, vy)
        self.in_play = True
        self.floor_bounces = 0
        self.last_front_wall_hit = False
        self.spin = random.uniform(-1.0, 1.0)

    def update(self, dt: float):
        if not self.in_play:
            return

        self.vel.y += GRAVITY * dt
        self.vel *= max(0.0, 1.0 - AIR_DRAG * dt)
        self.vel.x += self.spin * 6.0 * dt
        self.pos += self.vel * SCALE * dt
        self.spin *= max(0.0, 1.0 - SPIN_DECAY * dt)

        # Side wall collisions
        if self.pos.x - BALL_RADIUS < LEFT_WALL_X:
            self.pos.x = LEFT_WALL_X + BALL_RADIUS
            self.vel.x *= -0.92
            self.spin *= -0.7
        elif self.pos.x + BALL_RADIUS > RIGHT_WALL_X:
            self.pos.x = RIGHT_WALL_X - BALL_RADIUS
            self.vel.x *= -0.92
            self.spin *= -0.7

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
            self.vel.x = self.vel.x * 0.94 + self.spin * 1.8
            self.floor_bounces += 1
            self.spin *= 0.75

            # Kill tiny bounces to avoid jitter
            if abs(self.vel.y) < 1.6:
                self.vel.y = 0


class Player:
    def __init__(self):
        self.pos = Vector2(WIDTH * 0.44, FLOOR_Y - PLAYER_RADIUS)
        self.vel = Vector2(0, 0)
        self.stamina = 1.0

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

        sprint = (keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]) and self.stamina > 0.08
        top_speed = PLAYER_SPEED * (1.28 if sprint else 1.0)

        if sprint and desired.length_squared() > 0:
            self.stamina = max(0.0, self.stamina - 0.55 * dt)
        else:
            self.stamina = min(1.0, self.stamina + 0.22 * dt)

        if desired.length_squared() > 0:
            desired = desired.normalize() * top_speed * SCALE
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
        self.player_charge = 0.0
        self.ball.reset_for_serve(self.score.server)

    def swing(self, hitter: str, shot_type: str = "drive", charge: float = 0.0):
        actor = self.player if hitter == "player" else self.ai
        to_ball = self.ball.pos - actor.pos
        if to_ball.length() > HIT_RANGE:
            return False

        timing_window = abs(self.ball.pos.y - (FLOOR_Y - 120))
        timing_quality = max(0.25, 1.0 - timing_window / 260)
        distance_quality = max(0.2, 1.0 - to_ball.length() / HIT_RANGE)
        quality = 0.55 * timing_quality + 0.45 * distance_quality

        if shot_type == "drop":
            base_power = random.uniform(10, 13)
            side = random.uniform(-0.25, 0.25)
            lift = -random.uniform(2.0, 4.0)
        elif shot_type == "lob":
            base_power = random.uniform(15, 18)
            side = random.uniform(-0.35, 0.35)
            lift = -random.uniform(9.0, 12.0)
        else:
            base_power = random.uniform(18, 23)
            side = random.uniform(-0.65, 0.65)
            lift = -random.uniform(3.5, 6.5)

        power = base_power + charge * 7.5
        hit_vec = Vector2(side, -1).normalize() * power
        hit_vec.y += lift

        if quality < 0.38:
            # Mishits happen often unless timing and position are good.
            hit_vec.x *= random.uniform(0.4, 1.5)
            hit_vec.y += random.uniform(1.2, 3.0)

        if hitter == "ai":
            hit_vec.x += random.uniform(-0.18, 0.18)
        else:
            hit_vec.x += random.uniform(-0.08, 0.08)

        if self.ball.pos.y > FLOOR_Y - 140:
            hit_vec.y -= random.uniform(3.0, 5.5)

        self.ball.vel = hit_vec
        self.ball.in_play = True
        self.ball.floor_bounces = 0
        self.ball.hit_by = hitter
        self.ball.last_front_wall_hit = False
        self.ball.spin = side * 4.0 + charge * (1.4 if hitter == "player" else 0.8)
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

        if keys[pygame.K_k]:
            self.player_charge = min(MAX_CHARGE, self.player_charge + 1.7 * dt)
        else:
            self.player_charge = max(0.0, self.player_charge - 1.4 * dt)

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
                self.swing("player", "drive", self.player_charge)
                self.player_charge = 0.0
            if keys[pygame.K_u]:
                self.swing("player", "drop", self.player_charge * 0.5)
                self.player_charge = 0.0
            if keys[pygame.K_i]:
                self.swing("player", "lob", self.player_charge)
                self.player_charge = 0.0

            # AI swing when close and ball on its side
            if self.ball.in_play and (self.ball.pos - self.ai.pos).length() < HIT_RANGE * 0.9 and self.ball.pos.y > FRONT_WALL_Y + 140:
                if random.random() < 0.18:
                    ai_shot = "drive"
                    if self.ball.pos.y < FRONT_WALL_Y + 260:
                        ai_shot = "lob"
                    elif random.random() < 0.22:
                        ai_shot = "drop"
                    self.swing("ai", ai_shot, random.uniform(0.0, 0.6))

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

        help_txt = "Move: WASD/Arrows (+SHIFT sprint) | J drive | U drop | I lob | Hold K charge | SPACE serve"
        self.screen.blit(self.font.render(help_txt, True, (220, 220, 220)), (40, HEIGHT - 40))

        server_text = self.font.render(f"Server: {self.score.server.upper()}", True, (200, 220, 255))
        self.screen.blit(server_text, (40, 70))

        stamina_w = 210
        pygame.draw.rect(self.screen, (55, 55, 65), (40, 102, stamina_w, 12), border_radius=4)
        pygame.draw.rect(self.screen, (90, 220, 120), (40, 102, int(stamina_w * self.player.stamina), 12), border_radius=4)
        self.screen.blit(self.font.render("Stamina", True, (210, 225, 210)), (260, 96))

        pygame.draw.rect(self.screen, (55, 55, 65), (40, 122, stamina_w, 10), border_radius=4)
        pygame.draw.rect(self.screen, (250, 205, 90), (40, 122, int(stamina_w * self.player_charge), 10), border_radius=4)
        self.screen.blit(self.font.render("Charge", True, (235, 215, 170)), (260, 116))

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
