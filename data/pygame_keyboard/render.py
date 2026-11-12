"""GIF из настоящих кадров Pygame; подписи клавиш добавлены над окном."""
from pathlib import Path

from .runtime import Program, pygame
from .content import COLORS, RIGHT, MOVE, program
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent

# Служебный образец только для отрисовки и проверки ДЗ, не входит в материал ученика.
HOMEWORK = program('left_color = (255, 0, 0)\nright_color = (255, 0, 0)', '''if event.type == pygame.KEYDOWN:
    if event.key == pygame.K_a:
        left_color = (0, 0, 255)
        right_color = (255, 0, 0)
    elif event.key == pygame.K_d:
        left_color = (255, 0, 0)
        right_color = (0, 0, 255)
    elif event.key == pygame.K_SPACE:
        left_color = (255, 0, 0)
        right_color = (255, 0, 0)''', '''screen.fill((0, 0, 0))
pygame.draw.rect(screen, left_color, (200, 250, 100, 100))
pygame.draw.rect(screen, right_color, (500, 250, 100, 100))''')


def taps(keys):
    result = []
    for key, name in keys:
        result.extend([(pygame.KEYDOWN, key, name, 'Нажатие: один KEYDOWN', 300),
                       (pygame.KEYUP, key, name, 'Клавиша отпущена — состояние сохраняется', 350)])
    return result


def scenarios():
    idle = [(None, None, '—', 'Начальное состояние', 900)]
    right = idle + taps([(pygame.K_RIGHT, '→')])
    right += [(pygame.KEYDOWN, pygame.K_RIGHT, '→', 'Нажатие: один KEYDOWN', 300),
              (None, None, '→', 'Удерживаем: новых KEYDOWN нет, круг стоит', 1500),
              (pygame.KEYUP, pygame.K_RIGHT, '→', 'Клавиша отпущена', 500)]
    right += taps([(pygame.K_RIGHT, '→')] * 4)
    right += [(None, None, '—', 'Пауза: круг стоит. Далее GIF начнется заново', 1200)]
    route = [(pygame.K_RIGHT, '→')] * 4 + [(pygame.K_DOWN, '↓')] * 3
    route += [(pygame.K_LEFT, '←')] * 4 + [(pygame.K_UP, '↑')] * 3
    return [
        ('colors.gif', COLORS, idle + taps([(pygame.K_r, 'R'), (pygame.K_g, 'G'),
                                          (pygame.K_b, 'B'), (pygame.K_SPACE, 'ПРОБЕЛ')]) + idle_pause()),
        ('right.gif', RIGHT, right),
        ('movement.gif', MOVE, idle + taps(route) + idle_pause()),
        ('homework.gif', HOMEWORK, idle + taps([(pygame.K_a, 'A'), (pygame.K_d, 'D'),
                                              (pygame.K_d, 'D'), (pygame.K_SPACE, 'ПРОБЕЛ'),
                                              (pygame.K_a, 'A'), (pygame.K_SPACE, 'ПРОБЕЛ'),
                                              (pygame.K_d, 'D'), (pygame.K_SPACE, 'ПРОБЕЛ')]) + idle_pause()),
    ]


def idle_pause():
    return [(None, None, '—', 'Пауза: новых нажатий нет', 1000)]


def render():
    (ROOT / 'images').mkdir(exist_ok=True)
    font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 18)
    key_font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 23)
    for filename, source, timeline in scenarios():
        runner = Program(source)
        frames, durations = [], []
        for kind, key, name, label, duration in timeline:
            runner.tick(*([pygame.event.Event(kind, key=key)] if kind else []))
            frame = Image.new('RGB', (800, 680), '#18212d')
            frame.paste(Image.frombytes('RGB', (800, 600), pygame.image.tostring(runner.screen, 'RGB')), (0, 80))
            draw = ImageDraw.Draw(frame)
            active = kind == pygame.KEYDOWN or label.startswith('Удерживаем')
            draw.rounded_rectangle((12, 10, 158, 69), radius=8, fill='#ffe082' if active else '#334155')
            draw.text((85, 39), name, anchor='mm', font=key_font, fill='#18212d' if active else 'white')
            draw.text((175, 12), label, font=font, fill='white')
            coords = (f"x = {runner.scope['x']}  |  y = {runner.scope.get('y', 300)}"
                      if 'x' in runner.scope else 'Окно 800 × 600  |  подписи добавлены для демонстрации')
            draw.text((175, 43), coords, font=font, fill='#bdcce0')
            frames.append(frame)
            durations.append(duration)
        path = ROOT / 'images' / filename
        frames[0].save(path, save_all=True, append_images=frames[1:], duration=durations,
                       loop=0, optimize=True, disposal=1)
        print(f'{filename}: {len(frames)} кадров, {path.stat().st_size} байт')
    pygame.quit()


if __name__ == '__main__':
    render()
