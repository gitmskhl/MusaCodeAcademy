"""Учебные примеры. Полные программы и явно подписанные фрагменты."""
from textwrap import dedent


def clean(value):
    return dedent(value).strip() + '\n'


POINT = clean('''
class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def move(self, dx, dy):
        self.x += dx
        self.y += dy

first = Point(100, 200)
second = Point(300, 400)
first.move(10, -5)
print(first.x, first.y)    # 110 195
print(second.x, second.y)  # 300 400
''')

POINT_CLASS = clean('''
class Point:
    def __init__(self, x, y, color):
        self.x = x
        self.y = y
        self.color = color

    def draw(self, surface):
        pygame.draw.circle(surface, self.color, (self.x, self.y), 6)
''')

POINT_DEMO = 'import pygame\n\n' + POINT_CLASS + clean('''
pygame.init()
screen = pygame.display.set_mode((800, 600))
clock = pygame.time.Clock()
points = [Point(200, 250, (255, 180, 70)), Point(500, 350, (80, 180, 255))]
running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
    if not running:
        break
    screen.fill((20, 24, 32))
    for point in points:
        point.draw(screen)
    pygame.display.flip()
    clock.tick(60)
pygame.quit()
''')

WAVE = clean('''
class Wave:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.radius = 2

    def update(self):
        self.radius += 2

    def is_alive(self):
        return self.radius <= 100

    def draw(self, surface):
        pygame.draw.circle(surface, (100, 190, 255),
                           (self.x, self.y), self.radius, 2)
''')

BALL = clean('''
class Ball:
    def __init__(self, x, y, vx, vy):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.radius = 8

    def update(self):
        self.x += self.vx
        self.y += self.vy

    def wall(self, width, height):
        if self.y - self.radius <= 0:
            return "top"
        if self.x - self.radius <= 0:
            return "left"
        if self.x + self.radius >= width:
            return "right"
        if self.y + self.radius >= height:
            return "bottom"
        return None

    def draw(self, surface):
        pygame.draw.circle(surface, (180, 180, 180),
                           (round(self.x), round(self.y)), self.radius)
''')

SPARK = clean('''
class Spark:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        angle = uniform(0, 2 * pi)
        speed = uniform(1, 4)
        self.vx = cos(angle) * speed
        self.vy = sin(angle) * speed
        self.radius = randint(2, 5)
        self.alpha = 255

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.alpha = max(0, self.alpha - 5)

    def is_alive(self):
        return self.alpha > 0

    def draw(self, surface):
        size = self.radius * 2 + 2
        image = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.circle(image, (255, 190, 70, self.alpha),
                           (self.radius + 1, self.radius + 1), self.radius)
        surface.blit(image, (round(self.x) - self.radius - 1,
                             round(self.y) - self.radius - 1))
''')

SPARK_DEMO = ('import pygame\nfrom random import uniform, randint\n'
              'from math import cos, sin, pi\n\n' + SPARK + clean('''
pygame.init()
screen = pygame.display.set_mode((800, 600))
clock = pygame.time.Clock()
sparks = []
running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
            sparks.append(Spark(400, 300))
    if not running:
        break
    alive = []
    for spark in sparks:
        spark.update()
        if spark.is_alive():
            alive.append(spark)
    sparks = alive
    screen.fill((20, 24, 32))
    for spark in sparks:
        spark.draw(screen)
    pygame.display.flip()
    clock.tick(60)
pygame.quit()
'''))

CANNON = clean('''
class Cannon:
    def __init__(self):
        self.x = 380
        self.y = 550
        self.width = 40
        self.height = 30
        self.speed = 5

    def update(self, keys):
        if keys[pygame.K_LEFT]:
            self.x -= self.speed
        if keys[pygame.K_RIGHT]:
            self.x += self.speed
        self.x = max(0, min(self.x, 800 - self.width))

    def muzzle(self):
        return self.x + self.width // 2, self.y

    def draw(self, surface):
        pygame.draw.rect(surface, (90, 190, 130),
                         (self.x, self.y, self.width, self.height))
''')

INHERITANCE = clean('''
class Particle:
    def __init__(self, x, y, vx, vy):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy

    def update(self):
        self.x += self.vx
        self.y += self.vy

    def draw(self, surface):
        pygame.draw.circle(surface, (255, 100, 70),
                           (round(self.x), round(self.y)), 4)

class SquareParticle(Particle):
    def __init__(self, x, y, vx, vy, size):
        super().__init__(x, y, vx, vy)
        self.size = size

    def draw(self, surface):
        pygame.draw.rect(surface, (90, 180, 255),
                         (round(self.x) - self.size // 2,
                          round(self.y) - self.size // 2,
                          self.size, self.size))
''')

PLAYER = clean('''
class Player:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.size = 40
        self.speed = 4
        self.color = (100, 200, 255)

    def update(self, keys):
        if keys[pygame.K_LEFT]:
            self.x -= self.speed
        if keys[pygame.K_RIGHT]:
            self.x += self.speed
        if keys[pygame.K_UP]:
            self.y -= self.speed
        if keys[pygame.K_DOWN]:
            self.y += self.speed
        self.x = max(0, min(self.x, 800 - self.size))
        self.y = max(0, min(self.y, 600 - self.size))

    def get_hitbox(self):
        return pygame.Rect(self.x, self.y, self.size, self.size)

    def render(self, surface):
        pygame.draw.rect(surface, self.color, self.get_hitbox())
''')

HITBOX_DEMO = clean('''
import pygame

pygame.init()
screen = pygame.display.set_mode((800, 600))
clock = pygame.time.Clock()
fixed = pygame.Rect(300, 230, 180, 100)
running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
    if not running:
        break
    mx, my = pygame.mouse.get_pos()
    moving = pygame.Rect(mx, my, 40, 40)
    color = (255, 100, 80) if moving.colliderect(fixed) else (100, 210, 130)
    screen.fill((20, 24, 32))
    pygame.draw.rect(screen, (130, 140, 170), fixed, 2)
    pygame.draw.rect(screen, color, moving)
    pygame.display.flip()
    clock.tick(60)
pygame.quit()
''')

PLATFORM = clean('''
class Platform:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, 100, 12)

    def get_hitbox(self):
        return self.rect

    def draw(self, surface):
        pygame.draw.rect(surface, (220, 220, 235), self.rect)
''')

BOUNCE = clean('''
# Фрагмент метода update(self, platforms) класса мяча.
# self.rect — квадратная область мяча 20 × 20; скорости целые.
old = self.rect.copy()
self.rect.x += self.vx
self.rect.y += self.vy
for platform in platforms:
    target = platform.get_hitbox()
    if self.rect.colliderect(target):
        if self.vy > 0 and old.bottom <= target.top:
            self.rect.bottom = target.top
            self.vy = -abs(self.vy)
            break
        elif self.vy < 0 and old.top >= target.bottom:
            self.rect.top = target.bottom
            self.vy = abs(self.vy)
            break
''')

TORCH = clean('''
class Torch:
    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, 20, 60)
        self.lit = False

    def is_near(self, player):
        zone = self.rect.inflate(120, 0)
        return zone.colliderect(player.get_hitbox())

    def ignite(self):
        self.lit = True

    def draw(self, surface):
        color = (255, 170, 50) if self.lit else (90, 80, 70)
        pygame.draw.rect(surface, color, self.rect)
''')

HEALTH = clean('''
# Эти методы добавь ВНУТРЬ класса Player.
# В __init__ также добавь: self.hp = 100
def take_damage(self, amount):
    self.hp = max(0, self.hp - max(0, amount))

def is_alive(self):
    return self.hp > 0
''')

DAMAGE_TIMER = clean('''
# Фрагмент игрового цикла после обновления игрока.
# elapsed_ms получен в начале кадра через clock.tick(60).
# damage_ms = 0 задается ОДИН раз перед while.
if mushroom.is_near(player):
    damage_ms += elapsed_ms
    while damage_ms >= 1000:
        player.take_damage(10)
        damage_ms -= 1000
else:
    damage_ms = 0
if not player.is_alive():
    running = False
''')

INVENTORY = clean('''
class Inventory:
    def __init__(self):
        self.has_key = False
        self.has_crystal = False

class Explorer:
    def __init__(self):
        self.inventory = Inventory()

first = Explorer()
second = Explorer()
first.inventory.has_key = True
print(first.inventory.has_key)   # True
print(second.inventory.has_key)  # False
''')

CHEST = clean('''
class Chest:
    def __init__(self):
        self.opened = False

    def interact(self, has_key):
        if has_key:
            self.opened = not self.opened

chest = Chest()
chest.interact(False)
print(chest.opened)  # False
chest.interact(True)
print(chest.opened)  # True
chest.interact(True)
print(chest.opened)  # False
''')
