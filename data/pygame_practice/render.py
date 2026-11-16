"""Служебные образцы и GIF из кадров Pygame; решения не входят в степы."""
from pathlib import Path
from unittest.mock import patch

from PIL import Image, ImageDraw, ImageFont
from data.pygame_keyboard.runtime import Program, pygame

ROOT = Path(__file__).resolve().parent
SEGMENTS = {
    'a': (110, 70, 180, 24), 'b': (290, 94, 24, 180),
    'c': (290, 298, 24, 180), 'd': (110, 478, 180, 24),
    'e': (86, 298, 24, 180), 'f': (86, 94, 24, 180),
    'g': (110, 274, 180, 24),
}


def program(initial, bovy, handler='', size=(800, 600)):
    from textwrap import indent
    return ('import pygame\npygame.init()\n'
            f'screen = pygame.display.set_mode({size!r})\n'
            'clock = pygame.time.Clock()\n' + initial + '\n\nwhile True:\n'
            '    events = pygame.event.get()\n    for event in events:\n'
            '        if event.type == pygame.QUIT:\n            exit()\n'
            + (indent(handler, '        ') + '\n' if handler else '')
            + indent(bovy, '    ') + '\n    pygame.display.update()\n    clock.tick(60)\n')


DIGITS = program(
    'digit = 0\nsegments = ' + repr(SEGMENTS) + '\n'
    "patterns = ['abcdef', 'bc', 'abdeg', 'abcdg', 'bcfg', 'acdfg', 'acdefg', 'abc', 'abcdefg', 'abcdfg']",
    "screen.fill((0, 0, 0))\nfor name, rect in segments.items():\n"
    "    color = (0, 255, 0) if name in patterns[digit] else (0, 50, 0)\n"
    "    pygame.draw.rect(screen, color, rect)",
    'if event.type == pygame.KEYDOWN:\n'
    '    if pygame.K_0 <= event.key <= pygame.K_9:\n'
    '        digit = event.key - pygame.K_0', size=(400, 600))

TRAFFIC = program('state = 0\ntimer = 120', '''timer -= 1
if timer == 0:
    state = (state + 1) % 4
    timer = 120 if state == 0 or state == 2 else 60
screen.fill((0, 0, 0))
pygame.draw.rect(screen, (35, 35, 35), (90, 50, 180, 440))
red = (255, 0, 0) if state == 0 or state == 1 else (60, 0, 0)
yellow = (255, 255, 0) if state == 1 or state == 3 else (60, 60, 0)
green = (0, 255, 0) if state == 2 else (0, 60, 0)
pygame.draw.circle(screen, red, (180, 140), 55)
pygame.draw.circle(screen, yellow, (180, 270), 55)
pygame.draw.circle(screen, green, (180, 400), 55)''', size=(360, 540))

DIRECTION = program('x = 400\ny = 300\nvx = 3\nvy = 0', '''x += vx
y += vy
screen.fill((0, 0, 0))
pygame.draw.circle(screen, (0, 255, 0), (x, y), 20)''', '''if event.type == pygame.KEYDOWN:
    if event.key == pygame.K_w:
        vx = 0
        vy = -3
    elif event.key == pygame.K_a:
        vx = -3
        vy = 0
    elif event.key == pygame.K_s:
        vx = 0
        vy = 3
    elif event.key == pygame.K_d:
        vx = 3
        vy = 0''')


class Sample:
    """Исполняет исходный код по кадрам без реального ожидания."""
    def __init__(self, source):
        with patch.object(pygame.time, 'Clock') as clock:
            self.runner = Program(source)
            self.clock = clock.return_value

    def tick(self, frame, *events):
        # frame — отметка сценария; сама программа считает вызовы игрового цикла.
        return self.runner.tick(*events)

    @property
    def screen(self):
        return self.runner.screen


def scenarios():
    digits = [(0, [], 'Старт: цифра 0', 700)]
    now = 700
    for digit in list(range(1, 10)) + [8, 1, 0]:
        digits += [(now, [pygame.event.Event(pygame.KEYDOWN, key=getattr(pygame, f'K_{digit}'))], f'Нажатие: {digit}', 350),
                   (now + 350, [pygame.event.Event(pygame.KEYUP, key=getattr(pygame, f'K_{digit}'))], f'Клавиша отпущена: остается {digit}', 450)]
        now += 800
    traffic = []
    # Sample исполняет первый кадр при создании. Далее проигрываем каждый кадр
    # счетчика, сохраняя только начало каждой стадии для компактного GIF.
    captures = {2: ('Красный: 2 секунды', 2000),
                120: ('Красный + желтый: 1 секунда', 1000),
                180: ('Зеленый: 2 секунды', 2000),
                300: ('Желтый: 1 секунда', 1000)}
    for frame in range(2, 301):
        label, duration = captures.get(frame, ('', 0))
        traffic.append((frame, [], label, duration))
    direction = []
    # 240 кадров по 1/60 с: замкнутый маршрут, по 60 кадров на сторону.
    # Sample уже исполнил первый кадр: второй сегмент начинается после 59.
    turns = {59: (pygame.K_s, 'S'), 119: (pygame.K_a, 'A'),
             179: (pygame.K_w, 'W'), 239: (pygame.K_d, 'D')}
    current, turn = 'D (начальное направление)', -100
    for frame in range(240):
        events = []
        if frame in turns:
            key, current = turns[frame]
            events = [pygame.event.Event(pygame.KEYDOWN, key=key)]
            turn = frame
        elif frame - 1 in turns:
            events = [pygame.event.Event(pygame.KEYUP, key=turns[frame-1][0])]
        if frame - turn < 6:
            label = f'Нажатие {current}: новое направление'
        else:
            label = f'Клавиши отпущены: движение продолжается ({current})'
        # 10 кадров GIF в секунду, каждый показывает 6 кадров программы.
        duration = 100 if frame % 6 == 5 else 0
        direction.append((round(frame * 1000 / 60), events, label, duration))
    # Показать короткое финальное D и отпускание перед повтором.
    for frame in range(240, 252):
        events = [pygame.event.Event(pygame.KEYUP, key=pygame.K_d)] if frame == 240 else []
        label = 'D отпущена: круг продолжает идти вправо'
        if frame >= 246:
            label = 'Далее GIF повторится с начальной позиции'
        direction.append((round(frame * 1000 / 60), events, label, 100 if frame % 6 == 5 else 0))
    return [('digits.gif', DIGITS, digits), ('traffic.gif', TRAFFIC, traffic),
            ('direction.gif', DIRECTION, direction)]


def frames(source, timeline):
    runner = Sample(source)
    font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 18)
    for now, events, label, duration in timeline:
        runner.tick(now, *events)
        if not duration:
            continue
        width, height = runner.screen.get_size()
        image = Image.new('RGB', (800, height + 80), '#18212d')
        image.paste(Image.frombytes('RGB', (width, height), pygame.image.tostring(runner.screen, 'RGB')), ((800-width)//2, 80))
        draw = ImageDraw.Draw(image)
        draw.text((16, 12), label, fill='white', font=font)
        draw.text((16, 43), f'Игровое поле {width} × {height}  |  плашка добавлена для пояснения', fill='#bdcce0', font=font)
        yield image, duration


def render():
    (ROOT / 'images').mkdir(exist_ok=True)
    for filename, source, timeline in scenarios():
        sequence = list(frames(source, timeline))
        path = ROOT / 'images' / filename
        sequence[0][0].save(path, save_all=True, append_images=[x[0] for x in sequence[1:]],
                            duration=[x[1] for x in sequence], loop=0, optimize=True, disposal=1)
        print(f'{filename}: {len(sequence)} кадров, {path.stat().st_size} байт')
    pygame.quit()


if __name__ == '__main__':
    render()
