"""Служебные образцы заданий и GIF из кадров Pygame; решения не входят в степы."""
import math
from pathlib import Path
import random
from unittest.mock import patch

from PIL import Image, ImageDraw, ImageFont
from data.pygame_keyboard.runtime import Program, pygame
from .content import program, IMAGES

ROOT = Path(__file__).resolve().parent
COLOR = '[randint(40, 255), randint(40, 255), randint(40, 255)]'
DRAW = 'for p in particles:\n    pygame.draw.circle(screen, p[2], (p[0], p[1]), p[3])'
MOVE = 'for p in particles:\n    p[0] += p[4]\n    p[1] += p[5]'
CLEAN = '''visible = []
for p in particles:
    if p[0] + p[3] >= 0 and p[0] - p[3] <= 800 and p[1] + p[3] >= 0 and p[1] - p[3] <= 600:
        visible.append(p)
particles = visible'''

CIRCLES = program('particles = []\ntimer = 120', f'''timer -= 1
if timer == 0:
    particles.append([randint(30, 770), randint(30, 570), {COLOR}, 30])
    timer = 120
{DRAW}''')

RAIN = program('squares = []\ntimer = 10', f'''timer -= 1
if timer == 0:
    size = randint(10, 30)
    squares.append([randint(0, 800-size), 0, size, randint(2, 6), {COLOR}])
    timer = 10
visible = []
for square in squares:
    square[1] += square[3]
    if square[1] <= 600:
        visible.append(square)
squares = visible
for square in squares:
    pygame.draw.rect(screen, square[4], (square[0], square[1], square[2], square[2]))''')

FALL = program('particles = []\ntimer = 60', f'''timer -= 1
if timer == 0:
    particles.append([randint(20, 780), 0, {COLOR}, 20, 0, randint(2, 6)])
    timer = 60
{MOVE}
{CLEAN}
{DRAW}''')

TYPES = program('particles = []\ntimer = 30', f'''timer -= 1
if timer == 0:
    if randint(0, 1) == 0:
        particles.append([randint(20, 780), 0, {COLOR}, 20, 0, randint(2, 6), "top"])
    else:
        particles.append([0, randint(20, 580), {COLOR}, 20, randint(2, 6), 0, "side"])
    timer = randint(30, 60)
{MOVE}
{CLEAN}
{DRAW}''')

DOTS = program('points = []', '''for point in points:
    pygame.draw.circle(screen, (255, 255, 255), point, 5)''', '''if event.type == pygame.MOUSEBUTTONDOWN and event.button in (1, 2, 3):
    mx, my = event.pos
    points.append([mx, my])''')

UP = program('particles = []\ntimer = 3', f'''mx, my = pygame.mouse.get_pos()
timer -= 1
if timer == 0:
    if 0 <= mx < 800 and 0 <= my < 600:
        particles.append([mx, my, {COLOR}, randint(3, 12), 0, randint(-5, -2)])
    timer = 3
{MOVE}
{CLEAN}
{DRAW}''')

BALLS = program('balls = []', f'''mx, my = pygame.mouse.get_pos()
if pygame.mouse.get_pressed()[0] and 0 <= mx < 800 and 0 <= my < 600:
    vx = randint(-4, 4)
    vy = randint(-4, 4)
    if vx == 0 and vy == 0:
        vy = -1
    balls.append([mx, my, randint(2, 8), vx, vy, {COLOR}])
visible = []
for ball in balls:
    ball[0] += ball[3]
    ball[1] += ball[4]
    if ball[0]+ball[2] >= 0 and ball[0]-ball[2] <= 800 and ball[1]+ball[2] >= 0 and ball[1]-ball[2] <= 600:
        visible.append(ball)
balls = visible
for ball in balls:
    pygame.draw.circle(screen, ball[5], (ball[0], ball[1]), ball[2])''')

EDITOR = program('shapes = []', '''for shape in shapes:
    pygame.draw.rect(screen, (255, 200, 80), (shape[0], shape[1], 80, 50))
mx, my = pygame.mouse.get_pos()
pygame.draw.rect(screen, (255, 200, 80), (mx, my, 80, 50), 2)''', '''if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
    mx, my = event.pos
    shapes.append([mx, my])''', background=(100, 100, 100))

EDITOR2 = program('shapes = []\ncurrent_type = 1', '''for shape in shapes:
    if shape[2] == 1:
        pygame.draw.rect(screen, (255, 200, 80), (shape[0], shape[1], 80, 50))
    else:
        pygame.draw.circle(screen, (255, 200, 80), (shape[0], shape[1]), 30)
mx, my = pygame.mouse.get_pos()
if current_type == 1:
    pygame.draw.rect(screen, (255, 200, 80), (mx, my, 80, 50), 2)
else:
    pygame.draw.circle(screen, (255, 200, 80), (mx, my), 30, 2)''', '''if event.type == pygame.KEYDOWN:
    if event.key == pygame.K_1:
        current_type = 1
    elif event.key == pygame.K_2:
        current_type = 2
if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
    mx, my = event.pos
    shapes.append([mx, my, current_type])''', background=(100, 100, 100))

SOURCES = dict(zip([x[2] for x in IMAGES], [CIRCLES, RAIN, FALL, TYPES, DOTS, UP, BALLS, EDITOR, EDITOR2], strict=True))


class Sample:
    def __init__(self, source, seed=14):
        self.rng = random.Random(seed)
        with patch.object(pygame.time, 'Clock'), patch('random.randint', self.rng.randint), \
                patch.object(pygame.mouse, 'get_pos', return_value=(400, 400)), \
                patch.object(pygame.mouse, 'get_pressed', return_value=(False, False, False)):
            self.runner = Program(source)

    def tick(self, *events, pos=(400, 400), held=False):
        with patch.object(pygame.mouse, 'get_pos', return_value=pos), \
                patch.object(pygame.mouse, 'get_pressed', return_value=(held, False, False)):
            return self.runner.tick(*events)

    @property
    def scope(self):
        return self.runner.scope

    @property
    def screen(self):
        return self.runner.screen


def timeline(filename):
    total = 600 if filename in ('circles.gif', 'fall.gif', 'types.gif') else 300
    for frame in range(2, total + 1):
        events, held = [], False
        pos = (int(400 + 200 * math.sin(frame / 45)), 400 + int(60 * math.cos(frame / 60)))
        label = ''
        if filename in ('click.gif', 'editor.gif', 'editor2.gif'):
            positions = [(120, 180), (320, 260), (540, 170), (570, 390)]
            index = min((frame - 1) // 70, 3)
            pos = positions[index]
            if filename == 'editor2.gif' and frame in (70, 210):
                events.append(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_2 if frame == 70 else pygame.K_1))
            if frame in (30, 100, 170, 240):
                events.append(pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=pos, button=1))
            label = ('Клик: фигура сохранена' if frame % 70 >= 30 else 'Предпросмотр следует за мышью')
            if filename == 'click.gif':
                label = 'Клик добавляет точку, движение ничего не добавляет'
            if filename == 'editor2.gif':
                label = ('Выбрано: круг (2)' if 70 <= frame < 210 else 'Выбрано: прямоугольник (1)')
        elif filename == 'balls.gif':
            held = frame < 180
            label = 'ЛКМ удерживается: создаем шарики' if held else 'ЛКМ отпущена: шарики продолжают лететь'
        elif filename == 'up.gif':
            label = 'Курсор движется; новые кружки летят вверх без нажатий'
        elif filename == 'circles.gif':
            label = 'Новый кружок каждые 120 кадров (примерно 2 секунды)'
        elif filename == 'rain.gif':
            label = 'Новый квадрат каждые 10 кадров; у каждого своя скорость'
        elif filename == 'fall.gif':
            label = 'Новый кружок каждые 60 кадров; старые продолжают падать'
        else:
            label = 'Частицы сверху и слева: направление сохраняется'
        yield frame, events, pos, held, label


def frames(filename):
    sample = Sample(SOURCES[filename])
    font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 17)
    for frame, events, pos, held, label in timeline(filename):
        sample.tick(*events, pos=pos, held=held)
        if frame % 6:
            continue
        game = Image.frombytes('RGB', (800, 600), pygame.image.tostring(sample.screen, 'RGB'))
        canvas = Image.new('RGB', (800, 680), (24, 30, 44))
        canvas.paste(game, (0, 80))
        draw = ImageDraw.Draw(canvas)
        draw.text((16, 12), label, font=font, fill='white')
        draw.text((16, 43), f'Кадр {frame} · При повторе GIF программа начинается заново', font=font, fill=(180, 195, 220))
        if filename in ('click.gif', 'up.gif', 'balls.gif', 'editor.gif', 'editor2.gif'):
            mx, my = pos
            draw.line((mx-7, my+80, mx+7, my+80), fill='white', width=1)
            draw.line((mx, my+73, mx, my+87), fill='white', width=1)
        yield canvas, game


def render():
    (ROOT / 'images').mkdir(exist_ok=True)
    # Одна общая палитра на GIF сохраняет цвета неизменными между кадрами.
    for filename in SOURCES:
        sequence = [canvas for canvas, _ in frames(filename)]
        overview = Image.new('RGB', (800, 680 * len(sequence)))
        for index, canvas in enumerate(sequence):
            overview.paste(canvas, (0, 680 * index))
        palette = overview.quantize(colors=256, dither=Image.Dither.NONE)
        encoded = [canvas.quantize(palette=palette, dither=Image.Dither.NONE) for canvas in sequence]
        path = ROOT / 'images' / filename
        encoded[0].save(path, save_all=True, append_images=encoded[1:], duration=100, loop=0, optimize=False, disposal=2)
        print(filename, len(encoded), path.stat().st_size)
    pygame.quit()


if __name__ == '__main__':
    render()
