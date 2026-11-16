"""Воспроизводимые демонстрации заданий. Этот код не включается в уроки."""
from collections import defaultdict
from hashlib import sha256
import json
from math import cos, sin, pi
import os
from pathlib import Path
import random

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
import pygame
from PIL import Image, ImageDraw, ImageFont

from . import examples as ex

ROOT = Path(__file__).resolve().parent
BACKGROUND = (20, 24, 32)
FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'


class Particle:
    def __init__(self, x, y, rng, shape='circle', color=(255, 220, 80), size=3, vy=None):
        self.x, self.y = x, y
        self.vx = rng.randint(-3, 3)
        self.vy = rng.randint(-3, 3) if vy is None else vy
        self.shape, self.color, self.size, self.life = shape, color, size, 45

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.life -= 1

    def draw(self, surface):
        if self.shape == 'square':
            pygame.draw.rect(surface, self.color, (round(self.x) - self.size // 2,
                             round(self.y) - self.size // 2, self.size, self.size))
        else:
            pygame.draw.circle(surface, self.color, (round(self.x), round(self.y)), self.size)


class Scene:
    def __init__(self, number):
        self.number, self.frame = number, 0
        self.rng = random.Random(100 + number)
        self.scope = dict(pygame=pygame, uniform=self.rng.uniform, randint=self.rng.randint,
                          sin=sin, cos=cos, pi=pi)
        for source in [ex.POINT_CLASS, ex.WAVE, ex.BALL, ex.SPARK, ex.CANNON,
                       ex.PLAYER, ex.PLATFORM, ex.TORCH]:
            exec(source, self.scope)
        exec('def bounce(self, platforms):\n' + '\n'.join('    ' + line for line in ex.BOUNCE.splitlines()), self.scope)
        self.points, self.waves, self.balls, self.particles, self.platforms = [], [], [], [], []
        self.player = self.scope['Player'](50 if number >= 11 else 100, 520 if number >= 11 else 100)
        self.cannon = self.scope['Cannon']()
        self.torches = [self.scope['Torch'](x, 500) for x in (200, 400, 600)]
        self.coin = pygame.Rect(330, 260, 20, 20)
        self.key = pygame.Rect(250, 540, 20, 20)
        self.chest = pygame.Rect(600, 520, 60, 40)
        self.crystal = pygame.Rect(300, 540, 20, 20)
        self.hp, self.damage_ms, self.phase, self.phase_frame = 100, 0, 0, 0
        self.has_key = self.opened = self.carried = False
        self.on_ground = True
        self.started = False
        self.mouse, self.action = None, ''
        self.font = pygame.font.Font(FONT, 23)
        self.stats = dict(clicks=0, impacts=0, wall_types=[], particles_created=0,
                          collected=0, ignited=0, bounces=0, picked=0, dropped=0,
                          locked=0, opened=0, closed=0, damage=0, left_zone=False)

    def color(self):
        return tuple(self.rng.randint(40, 255) for _ in range(3))

    def ball(self, x, y, speed=4, radius=8, vector=None):
        if vector is None:
            angle = self.rng.uniform(0, 2 * pi)
            vector = (cos(angle) * speed, sin(angle) * speed)
        obj = self.scope['Ball'](x, y, *vector)
        obj.radius = radius
        self.balls.append(obj)

    def spark(self, x, y, trail=False):
        obj = self.scope['Spark'](x, y)
        if trail:
            angle = self.rng.uniform(0, 2 * pi)
            speed = self.rng.uniform(.2, 1)
            obj.vx, obj.vy = cos(angle) * speed, sin(angle) * speed
            obj.radius = self.rng.randint(1, 3)
        self.particles.append(obj)
        self.stats['particles_created'] += 1

    def label(self, surface, value, pos=(15, 15)):
        surface.blit(self.font.render(value, True, (255, 255, 255)), pos)

    def move_towards(self, center):
        diff = center - self.player.get_hitbox().centerx
        self.player.x += max(-4, min(4, diff))
        self.player.x = max(0, min(760, self.player.x))
        return abs(diff) <= 4

    def next_phase(self):
        self.phase += 1
        self.phase_frame = self.frame

    def tick(self):
        self.frame += 1
        f, n = self.frame, self.number
        self.action = ''
        if n in (1, 2):
            positions = [(130, 160), (310, 280), (530, 180), (650, 400)]
            i = min(max(0, (f - 30) // 45), 3)
            self.mouse = positions[i]
            if f in (30, 75, 120, 165):
                p = self.scope['Point'](*self.mouse, (255, 255, 255) if n == 1 else self.color())
                self.points.append(p)
                self.action = 'Клик'
                self.stats['clicks'] += 1
        elif n == 3:
            schedule = {30: (180, 220), 55: (370, 320), 80: (560, 220), 110: (400, 180)}
            if f in schedule:
                self.mouse = schedule[f]
                self.waves.append(self.scope['Wave'](*self.mouse))
                self.action = 'Левый клик'
                self.stats['clicks'] += 1
            for wave in self.waves:
                wave.update()
            self.waves = [w for w in self.waves if w.is_alive()]
        elif n in (4, 5, 7, 8):
            if n in (4, 5):
                schedule = {30: (100, 230, (-4, 0)), 100: (380, 100, (0, -4)),
                            170: (700, 330, (4, 0)), 240: (420, 500, (0, 4))}
                if f in schedule:
                    x, y, vector = schedule[f]
                    self.mouse = (x, y)
                    self.ball(x, y, vector=vector)
                    self.stats['clicks'] += 1
                    self.action = 'Левый клик'
            elif f in ((30, 90) if n == 7 else (30, 100, 160)):
                self.mouse = (250, 300) if f == 30 else (550, 250)
                for _ in range(8 if n == 7 else 1):
                    self.ball(*self.mouse, speed=5 if n == 7 else 4, radius=5)
                self.stats['clicks'] += 1
                self.action = 'Левый клик'
            alive = []
            for ball in self.balls:
                old = ball.x, ball.y
                ball.update()
                wall = ball.wall(800, 600)
                if wall:
                    self.stats['impacts'] += 1
                    self.stats['wall_types'].append(wall)
                    x, y = max(0, min(799, ball.x)), max(0, min(599, ball.y))
                    if wall in ('left', 'right'):
                        x = 0 if wall == 'left' else 799
                    else:
                        y = 0 if wall == 'top' else 599
                    for _ in range(12 if n == 7 else (0 if n == 8 else 7)):
                        if n == 7:
                            self.spark(x, y)
                        else:
                            shape, color, size = 'circle', (255, 220, 80), 3
                            if n == 5:
                                shape = 'square' if wall == 'top' else 'circle'
                                color = {'left': (255, 50, 50), 'right': (50, 100, 255)}.get(wall, self.color())
                                size = self.rng.randint(1, 10 if shape == 'square' else 8)
                            self.particles.append(Particle(x, y, self.rng, shape, color, size))
                            self.stats['particles_created'] += 1
                else:
                    alive.append(ball)
                    if n == 8:
                        for _ in range(2):
                            self.spark(*old, trail=True)
            self.balls = alive
        elif n == 6:
            self.mouse = (int(400 + 200 * sin(f / 35)), int(300 + 100 * cos(f / 30)))
            if 30 <= f < 180:
                for _ in range(3):
                    self.spark(*self.mouse)
                self.action = 'ЛКМ удерживается'
            else:
                self.action = 'Кнопка отпущена'
        elif n == 9:
            keys = defaultdict(bool)
            keys[pygame.K_RIGHT if f < 100 else pygame.K_LEFT] = 30 <= f < 190
            self.cannon.update(keys)
            if f in (45, 90, 135):
                x, y = self.cannon.muzzle()
                self.ball(x, y - 5, radius=5, vector=(0, -6))
                self.action = 'Пробел — выстрел'
                self.stats['clicks'] += 1
            alive = []
            for ball in self.balls:
                ball.update()
                if ball.wall(800, 600):
                    self.stats['impacts'] += 1
                    for _ in range(10):
                        self.particles.append(Particle(ball.x, 0, self.rng, color=self.color(),
                                                      size=self.rng.randint(2, 4), vy=self.rng.randint(1, 4)))
                        self.stats['particles_created'] += 1
                else:
                    alive.append(ball)
            self.balls = alive
        elif n == 10:
            if f >= 30:
                keys = defaultdict(bool)
                px, py = self.player.get_hitbox().center
                cx, cy = self.coin.center
                keys[pygame.K_RIGHT], keys[pygame.K_LEFT] = cx - px > 2, cx - px < -2
                keys[pygame.K_DOWN], keys[pygame.K_UP] = cy - py > 2, cy - py < -2
                self.player.update(keys)
                if self.player.get_hitbox().colliderect(self.coin):
                    self.stats['collected'] += 1
                    while True:
                        self.coin.center = (self.rng.randint(10, 790), self.rng.randint(10, 590))
                        if not self.player.get_hitbox().colliderect(self.coin):
                            break
        elif n in (11, 12):
            positions = [(100, 480), (250, 380), (400, 280), (550, 180), (650, 100)]
            if f in (30, 60, 90, 120, 150):
                self.mouse = positions[len(self.platforms)]
                self.platforms.append(self.scope['Platform'](*self.mouse))
                self.action = 'Левый клик'
                self.stats['clicks'] += 1
            if n == 12 and len(self.platforms) == 5:
                if not hasattr(self, 'moving_ball'):
                    self.moving_ball = type('BallBody', (), {})()
                    self.moving_ball.rect = pygame.Rect(20, 560, 20, 20)
                    self.moving_ball.vx, self.moving_ball.vy = 4, -3
                if f == 180:
                    self.started = True
                    self.action = 'Пробел — запуск'
                if self.started:
                    ball = self.moving_ball
                    # Как в задании: стены до проверки платформ.
                    if ball.rect.left + ball.vx < 0:
                        ball.rect.left, ball.vx = 0, abs(ball.vx)
                    if ball.rect.right + ball.vx > 800:
                        ball.rect.right, ball.vx = 800, -abs(ball.vx)
                    if ball.rect.top + ball.vy < 0:
                        ball.rect.top, ball.vy = 0, abs(ball.vy)
                    if ball.rect.bottom + ball.vy > 600:
                        ball.rect.bottom, ball.vy = 600, -abs(ball.vy)
                    vy = ball.vy
                    self.scope['bounce'](ball, self.platforms)
                    if ball.vy != vy:
                        self.stats['bounces'] += 1
        elif n == 13:
            if f >= 30:
                self.move_towards(710)
                choices = [t for t in self.torches if not t.lit and t.is_near(self.player)]
                if choices:
                    target = min(choices, key=lambda t: abs(t.rect.centerx - self.player.get_hitbox().centerx))
                    if abs(target.rect.centerx - self.player.get_hitbox().centerx) < 4:
                        target.ignite()
                        self.stats['ignited'] += 1
                        self.action = 'E — зажечь'
        elif n == 14:
            if self.hp > 0:
                if f < 30:
                    pass
                elif f < 230:
                    self.move_towards(410)
                elif f < 300:
                    self.move_towards(200)
                else:
                    self.move_towards(410)
                near = pygame.Rect(390, 520, 40, 40).inflate(120, 0).colliderect(self.player.get_hitbox())
                if near:
                    self.damage_ms += 16 if f % 3 == 1 else 17
                    while self.damage_ms >= 1000:
                        self.hp = max(0, self.hp - 10)
                        self.stats['damage'] += 1
                        self.damage_ms -= 1000
                else:
                    self.damage_ms = 0
                    if f > 230:
                        self.stats['left_zone'] = True
        elif n == 15:
            if f >= 30:
                if self.phase == 0 and self.move_towards(self.chest.centerx):
                    self.stats['locked'] += 1
                    self.action = 'E — сундук пока заперт'
                    self.next_phase()
                elif self.phase == 1 and f - self.phase_frame > 40:
                    self.next_phase()
                elif self.phase == 2 and self.move_towards(self.key.centerx):
                    self.has_key = True
                    self.action = 'E — подобрать ключ'
                    self.stats['picked'] += 1
                    self.next_phase()
                elif self.phase == 3 and self.move_towards(self.chest.centerx):
                    self.opened = True
                    self.stats['opened'] += 1
                    self.action = 'E — открыть сундук'
                    self.next_phase()
                elif self.phase == 4 and f - self.phase_frame >= 60:
                    self.opened = False
                    self.stats['closed'] += 1
                    self.action = 'E — закрыть сундук'
                    self.next_phase()
        elif n == 16 and f >= 30:
            if self.phase == 0 and self.move_towards(self.crystal.centerx):
                self.carried, self.on_ground = True, False
                self.action = 'E — подобрать'
                self.stats['picked'] += 1
                self.next_phase()
            elif self.phase == 1 and self.move_towards(650):
                self.crystal.centerx = self.player.get_hitbox().centerx
                self.crystal.bottom = self.player.get_hitbox().bottom
                self.carried, self.on_ground = False, True
                self.action = 'F — положить'
                self.stats['dropped'] += 1
                self.next_phase()
            elif self.phase == 2 and self.move_towards(350):
                self.next_phase()
            elif self.phase == 3 and self.move_towards(self.crystal.centerx):
                self.carried, self.on_ground = True, False
                self.action = 'E — снова подобрать'
                self.stats['picked'] += 1
                self.next_phase()
            elif self.phase == 4 and self.move_towards(420):
                self.crystal.centerx = self.player.get_hitbox().centerx
                self.crystal.bottom = self.player.get_hitbox().bottom
                self.carried, self.on_ground = False, True
                self.stats['dropped'] += 1
                self.action = 'F — снова положить'
                self.next_phase()

        alive = []
        for particle in self.particles:
            particle.update()
            if (particle.life > 0 if isinstance(particle, Particle) else particle.is_alive()):
                alive.append(particle)
        self.particles = alive

    def draw(self):
        screen = pygame.Surface((800, 600))
        screen.fill((100, 100, 100) if self.number in (11, 12) else ((0, 0, 0) if self.number in (1, 2, 3, 4, 5) else BACKGROUND))
        for point in self.points:
            pygame.draw.circle(screen, point.color, (point.x, point.y), 5)
        for obj in [*self.waves, *self.balls, *self.particles, *self.platforms]:
            obj.draw(screen)
        if self.number == 9:
            self.cannon.draw(screen)
        if self.number == 10:
            self.player.render(screen)
            pygame.draw.circle(screen, (255, 215, 45), self.coin.center, 10)
        if self.number in (11, 12):
            self.label(screen, f'Осталось платформ: {5 - len(self.platforms)}')
            if self.number == 12 and hasattr(self, 'moving_ball'):
                pygame.draw.circle(screen, (255, 200, 70), self.moving_ball.rect.center, 10)
                self.label(screen, 'Мяч запущен' if self.started else 'Пробел — запуск', (15, 50))
        if self.number >= 13:
            self.player.render(screen)
            px, py = self.player.x, self.player.y
            for eye in (10, 26):
                pygame.draw.rect(screen, (255, 255, 255), (px + eye, py + 10, 5, 6))
        if self.number == 13:
            for torch in self.torches:
                torch.draw(screen)
            if any(not t.lit and t.is_near(self.player) for t in self.torches):
                self.label(screen, 'Нажмите E', (max(10, self.player.x - 20), 470))
        elif self.number == 14:
            pygame.draw.rect(screen, (190, 190, 140), (400, 540, 20, 20))
            pygame.draw.ellipse(screen, (150, 65, 185), (380, 520, 60, 25))
            self.label(screen, f'Здоровье: {self.hp}')
            if self.hp == 0:
                self.label(screen, 'Здоровье 0 — окно игры закрывается', (100, 250))
        elif self.number == 15:
            if not self.has_key:
                pygame.draw.circle(screen, (255, 220, 60), self.key.center, 7, 3)
                pygame.draw.line(screen, (255, 220, 60), self.key.center, (self.key.right + 10, self.key.centery), 3)
            pygame.draw.rect(screen, (160, 100, 45), self.chest)
            pygame.draw.rect(screen, (250, 190, 75), self.chest, 3)
            if self.opened:
                pygame.draw.rect(screen, (70, 45, 30), self.chest.inflate(-8, -8))
                pygame.draw.rect(screen, (200, 140, 50), (600, 505, 60, 12))
            if self.chest.inflate(120, 0).colliderect(self.player.get_hitbox()):
                message = ('Нажмите E, чтобы закрыть сундук' if self.opened else 'Нажмите E, чтобы открыть сундук') if self.has_key else 'Сундук заперт. Найдите ключ'
                self.label(screen, message, (210, 460))
            elif not self.has_key and self.key.inflate(120, 0).colliderect(self.player.get_hitbox()):
                self.label(screen, 'Нажмите E, чтобы подобрать ключ', (120, 460))
        elif self.number == 16:
            if self.on_ground:
                x, y = self.crystal.center
                pygame.draw.polygon(screen, (110, 220, 255), [(x, y-10), (x+10, y), (x, y+10), (x-10, y)])
                if self.crystal.inflate(120, 0).colliderect(self.player.get_hitbox()):
                    self.label(screen, 'Нажмите E', (max(10, self.player.x - 15), 470))
        return screen


LENGTHS = {1: 240, 2: 240, 3: 210, 4: 360, 5: 360, 6: 270, 7: 360, 8: 420,
           9: 360, 10: 600, 11: 240, 12: 600, 13: 240, 14: 960, 15: 600, 16: 600}
TITLES = ['Точки остаются после клика', 'У каждой точки свой цвет', 'Клик создает растущую волну',
          'Удар о стену — семь частиц', 'Разные стены — разные частицы', 'Искры при удержании ЛКМ',
          'Один клик — залп из восьми снарядов', 'За каждой пулей остается след',
          'Стрелки — движение, пробел — выстрел', 'Стрелки — движение и сбор монеток',
          'Левый клик — поставить платформу', 'Пять платформ, затем пробел — запуск',
          'Подойди и нажми E — факел загорится', 'Рядом с грибом: −10 здоровья в секунду',
          'Найди ключ, затем открой сундук', 'E — подобрать, F — положить']


def palette():
    colors = [(r, g, b) for r in (0, 51, 102, 153, 204, 255)
              for g in (0, 51, 102, 153, 204, 255) for b in (0, 51, 102, 153, 204, 255)]
    colors += [(i, i, i) for i in range(0, 256, 8)]
    colors += [BACKGROUND, (24, 30, 44), (100, 200, 255), (255, 200, 70), (255, 220, 80), (20, 24, 32), (100, 100, 100), (90, 80, 70)]
    image = Image.new('P', (1, 1))
    image.putpalette([component for color in colors for component in color])
    return image


def frames(number):
    scene = Scene(number)
    font = ImageFont.truetype(FONT, 19)
    last_action, action_frame = '', 0
    for frame in range(1, LENGTHS[number] + 1):
        scene.tick()
        if scene.action:
            last_action, action_frame = scene.action, frame
        if frame % 6:
            continue
        screen = scene.draw()
        game = Image.frombytes('RGB', (800, 600), pygame.image.tobytes(screen, 'RGB'))
        canvas = Image.new('RGB', (800, 680), (24, 30, 44))
        canvas.paste(game, (0, 80))
        draw = ImageDraw.Draw(canvas)
        draw.text((15, 10), TITLES[number - 1], font=font, fill='white')
        action = last_action if frame - action_frame < 35 else 'Наблюдаем результат'
        draw.text((15, 43), action + ' · при повторе начинаем заново', font=font, fill=(190, 205, 225))
        if scene.mouse is not None:
            x, y = scene.mouse
            draw.line((x-7, y+80, x+7, y+80), fill='white', width=1)
            draw.line((x, y+73, x, y+87), fill='white', width=1)
        yield canvas, scene


def check(number, scene):
    s = scene.stats
    if number in (1, 2):
        assert len(scene.points) == 4 and s['clicks'] == 4
    elif number == 3:
        assert not scene.waves and s['clicks'] == 4
    elif number in (4, 5):
        assert s['impacts'] == 4 and set(s['wall_types']) == {'top', 'left', 'right', 'bottom'}
        assert s['particles_created'] == 28 and not scene.balls and not scene.particles
    elif number == 6:
        assert s['particles_created'] == 450 and not scene.particles
    elif number == 7:
        assert s['impacts'] == 16 and s['particles_created'] == 192 and not scene.particles
    elif number == 8:
        assert s['impacts'] == 3 and not scene.particles
    elif number == 9:
        assert s['impacts'] == 3 and s['particles_created'] == 30
    elif number == 10:
        assert s['collected'] >= 3 and not scene.player.get_hitbox().colliderect(scene.coin)
    elif number in (11, 12):
        assert len(scene.platforms) == 5
        if number == 12:
            assert scene.started and s['bounces'] >= 1
    elif number == 13:
        assert s['ignited'] == 3 and all(t.lit for t in scene.torches)
    elif number == 14:
        assert scene.hp == 0 and s['damage'] == 10 and s['left_zone']
    elif number == 15:
        assert scene.has_key and s['locked'] == s['opened'] == s['closed'] == 1
    elif number == 16:
        assert s['picked'] == s['dropped'] == 2 and scene.on_ground and not scene.carried


def main():
    pygame.init()
    (ROOT / 'images').mkdir(exist_ok=True)
    shared_palette = palette()
    report = {}
    for number in range(1, 17):
        sequence, states = [], []
        for frame, scene in frames(number):
            sequence.append(frame.quantize(palette=shared_palette, dither=Image.Dither.NONE))
            states.append(dict(frame=scene.frame, hp=scene.hp, particles=len(scene.particles),
                               crystal=list(scene.crystal), player_x=scene.player.x, carried=scene.carried))
        check(number, scene)
        path = ROOT / 'images' / f'task-{number:02}.gif'
        sequence[0].save(path, save_all=True, append_images=sequence[1:], duration=100,
                         loop=0, disposal=2, optimize=False)
        assert path.stat().st_size < 10 * 1024 * 1024
        report[path.name] = dict(sha256=sha256(path.read_bytes()).hexdigest(),
                                 size=path.stat().st_size, frames=len(sequence), duration_ms=100,
                                 stats=scene.stats, states=states)
        print(path.name, len(sequence), path.stat().st_size, flush=True)
    (ROOT / 'render-verification.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    pygame.quit()


if __name__ == '__main__':
    main()
