"""Проверка учебного кода с Pygame/SDL dummy, без решений самостоятельных заданий."""
import contextlib
from collections import defaultdict
from io import StringIO
from math import cos, sin, pi
import os
from random import uniform, randint
from textwrap import indent
from types import SimpleNamespace
from unittest.mock import patch

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
import pygame

from . import examples as ex
from .build import validate, write_json


def console(source, expected):
    output = StringIO()
    with contextlib.redirect_stdout(output):
        exec(source, {})
    assert output.getvalue() == expected


def program(source, frames=3, events=None, pos=(10, 10)):
    """Исполняет полный исходник, подавая события и отключая реальное ожидание."""
    scope, captures = {}, []
    frame = 0

    def get_events():
        nonlocal frame
        frame += 1
        if frame > frames:
            return [pygame.event.Event(pygame.QUIT)]
        return (events or {}).get(frame, [])

    def capture():
        captures.append(dict(frame=frame, count=len(scope.get('sparks', [])),
                             color=tuple(pygame.display.get_surface().get_at(pos))[:3]))

    with patch.object(pygame.time, 'Clock', return_value=SimpleNamespace(tick=lambda fps: 16)), \
            patch.object(pygame.event, 'get', side_effect=get_events), \
            patch.object(pygame.mouse, 'get_pos', return_value=pos), \
            patch.object(pygame.display, 'flip', side_effect=capture):
        exec(source, scope)
    assert frame == frames + 1 and len(captures) == frames
    assert scope['running'] is False and not pygame.get_init()
    return scope, captures


def main():
    validate()
    from .content import SECTIONS
    intro = {s['title']: s for s in SECTIONS[0]['lessons'][0]['steps']}
    scope = {}
    for title, expected in [('Создаем первую точку без Pygame', '100\n200\n'),
                            ('__init__, self и два независимых экземпляра', '100 200\n300 400\n'),
                            ('Что означает self', '500\n300\n')]:
        output = StringIO()
        with contextlib.redirect_stdout(output):
            for block in intro[title]['content']['blocks']:
                if block['type'] == 'code':
                    exec(block['data']['code'], scope)
        assert output.getvalue() == expected
    console(ex.POINT, '110 195\n300 400\n')
    console(ex.INVENTORY, 'True\nFalse\n')
    console(ex.CHEST, 'False\nTrue\nFalse\n')
    _, static = program(ex.POINT_DEMO, pos=(200, 250))
    assert all(c['color'] == (255, 180, 70) for c in static)
    _, spark_frames = program(ex.SPARK_DEMO, frames=60, events={
        1: [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE)]})
    assert spark_frames[0]['count'] == 1 and spark_frames[49]['count'] == 1
    assert all(c['count'] == 0 for c in spark_frames[50:])
    _, hit = program(ex.HITBOX_DEMO, pos=(310, 240))
    _, miss = program(ex.HITBOX_DEMO, pos=(10, 10))
    assert hit[-1]['color'] == (255, 100, 80)
    assert miss[-1]['color'] == (100, 210, 130)

    pygame.init()
    scope = dict(pygame=pygame, cos=cos, sin=sin, pi=pi, uniform=uniform, randint=randint)
    for source in [ex.WAVE, ex.BALL, ex.SPARK, ex.CANNON, ex.INHERITANCE, ex.PLAYER, ex.PLATFORM, ex.TORCH]:
        exec(source, scope)
    Wave, Ball, Spark = (scope[k] for k in ['Wave', 'Ball', 'Spark'])
    wave, other = Wave(100, 200), Wave(300, 400)
    for _ in range(49):
        wave.update()
    assert wave.radius == 100 and wave.is_alive()
    wave.update()
    assert not wave.is_alive() and other.radius == 2

    ball = Ball(400, 300, 3, -2)
    ball.update()
    assert (ball.x, ball.y) == (403, 298) and ball.wall(800, 600) is None
    for x, y, expected in [(400, 8, 'top'), (8, 300, 'left'), (792, 300, 'right'),
                            (400, 592, 'bottom'), (8, 8, 'top')]:
        assert Ball(x, y, 0, 0).wall(800, 600) == expected

    spark = Spark(100, 100)
    speed = (spark.vx ** 2 + spark.vy ** 2) ** .5
    assert 1 <= speed <= 4
    spark.vx = spark.vy = 0
    surface = pygame.Surface((800, 600))
    surface.fill((20, 24, 32))
    spark.alpha = 128
    spark.render(surface)
    blended = tuple(surface.get_at((100, 100)))[:3]
    assert 120 < blended[0] < 160 and blended != (255, 190, 70)
    assert tuple(surface.get_at((0, 0)))[:3] == (20, 24, 32)
    for _ in range(100):
        spark.update()
    assert spark.alpha == 0 and not spark.is_alive()

    keys = defaultdict(bool)
    player = scope['Player'](100, 100)
    keys[pygame.K_RIGHT] = True
    player.update(keys)
    assert player.x == 104 and player.get_hitbox().x == 104
    player.x = 760
    player.update(keys)
    assert player.x == 760
    player.y = -10
    player.update(defaultdict(bool))
    assert player.y == 0
    assert not pygame.Rect(0, 0, 40, 40).colliderect(pygame.Rect(40, 0, 20, 20))

    cannon = scope['Cannon']()
    keys = defaultdict(bool, {pygame.K_LEFT: True})
    for _ in range(100):
        cannon.update(keys)
    assert cannon.x == 0 and cannon.muzzle() == (20, 550)
    keys = defaultdict(bool, {pygame.K_RIGHT: True})
    for _ in range(200):
        cannon.update(keys)
    assert cannon.x == 760 and cannon.muzzle() == (780, 550)

    circle = scope['Particle'](100, 100, 2, -1)
    square = scope['SquareParticle'](200, 100, -1, 2, 10)
    for obj in [circle, square]:
        obj.update()
        obj.render(surface)
    assert (circle.x, circle.y) == (102, 99) and (square.x, square.y) == (199, 102)
    assert tuple(surface.get_at((102, 99)))[:3] == (255, 100, 70)
    assert tuple(surface.get_at((199, 102)))[:3] == (90, 180, 255)

    exec('def bounce(self, platforms):\n' + indent(ex.BOUNCE, '    '), scope)
    platform = scope['Platform'](100, 200)
    falling = SimpleNamespace(rect=pygame.Rect(110, 179, 20, 20), vx=0, vy=3)
    scope['bounce'](falling, [platform, platform])
    assert falling.rect.bottom == 200 and falling.vy == -3
    scope['bounce'](falling, [platform])
    assert falling.rect.bottom == 197 and falling.vy == -3
    rising = SimpleNamespace(rect=pygame.Rect(110, 213, 20, 20), vx=0, vy=-3)
    scope['bounce'](rising, [platform])
    assert rising.rect.top == 212 and rising.vy == 3

    torch, torch2 = scope['Torch'](200, 500), scope['Torch'](400, 500)
    player.x, player.y = 180, 520
    assert torch.is_near(player) and not torch2.is_near(player)
    original = torch.rect.copy()
    torch.ignite()
    torch.ignite()
    assert torch.lit and not torch2.lit and torch.rect == original

    exec('class Health:\n    def __init__(self):\n        self.hp = 100\n' + indent(ex.HEALTH, '    '), scope)
    health = scope['Health']()
    state = dict(player=health, mushroom=SimpleNamespace(is_near=lambda p: True), damage_ms=0, running=True)
    for elapsed in [400, 300, 300]:
        state['elapsed_ms'] = elapsed
        exec(ex.DAMAGE_TIMER, state)
    assert health.hp == 90 and state['damage_ms'] == 0
    state['elapsed_ms'] = 2500
    exec(ex.DAMAGE_TIMER, state)
    assert health.hp == 70 and state['damage_ms'] == 500
    state['mushroom'] = SimpleNamespace(is_near=lambda p: False)
    exec(ex.DAMAGE_TIMER, state)
    assert health.hp == 70 and state['damage_ms'] == 0
    health.take_damage(-10)
    assert health.hp == 70
    health.take_damage(100)
    assert health.hp == 0 and not health.is_alive()
    exec(ex.DAMAGE_TIMER, state)
    assert not state['running']
    pygame.quit()
    report = dict(schema=True, console_programs=5, continued_console_fragments=1, graphical_programs=3,
                  quit_verified=True, independent_instances=True, wave_lifetime=True,
                  walls_and_corner_priority=True, alpha_blending=True,
                  player_and_cannon_bounds=True, polymorphic_drawing=True,
                  platform_bounce_both_sides=True, torch_state=True,
                  damage_timer_and_death=True, pygame=pygame.version.ver)
    write_json('verification.json', report)
    print(report)


if __name__ == '__main__':
    main()
