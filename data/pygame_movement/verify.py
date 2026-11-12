"""Проверка исполнимости примеров и поведения движения с SDL dummy."""
import ast
import os
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
import pygame
from . import content


def run(source, count, invariant=None):
    tree = ast.parse(source)
    scope = {}
    exec(compile(ast.Module(body=tree.body[:-1], type_ignores=[]), '<init>', 'exec'), scope)
    loop = compile(ast.Module(body=tree.body[-1].body, type_ignores=[]), '<frame>', 'exec')
    for _ in range(count):
        exec(loop, scope)
        if invariant:
            assert invariant(scope)
    return scope


def verify():
    for item in content.LESSON['steps']:
        for block in item['content']['blocks']:
            if block['type'] == 'code':
                scope = run(block['data']['code'], 30)
                assert scope['screen'].get_size() == (800, 600)
    assert run(content.VARIABLE, 100)['x'] == 400
    assert run(content.RIGHT, 600)['x'] == 1000
    assert abs(run(content.SLOW, 600)['x'] - 460) < 1e-7
    for source, axis, low, high in [
        (content.WRAP, 'x', -20, 820), (content.LEFT, 'x', -20, 820),
        (content.DOWN, 'y', -20, 620), (content.UP, 'y', -20, 620),
    ]:
        state = run(source, 15000, lambda s: low <= s[axis] <= high)
        assert low <= state[axis] <= high
    for source in [content.DIAGONAL, content.OTHER_DIAGONAL]:
        run(source, 15000, lambda s: -20 <= s['x'] <= 820 and -20 <= s['y'] <= 620)
    signs = set()
    def bounce(s):
        signs.add(s['speed_x'])
        return 20 <= s['x'] <= 780
    run(content.BOUNCE, 16000, bounce)
    assert signs == {-0.1, 0.1}
    moving = run(content.SLOW, 1000)['screen'].copy()
    trail = run(content.TRAIL, 1000)['screen'].copy()
    assert moving.get_at((400, 300))[:3] == (0, 0, 0)
    assert trail.get_at((400, 300))[:3] == (0, 255, 0)
    pygame.quit()
    print('PASS: 12 программ; шаги 1 и 0.1; перенос по четырем границам; диагонали; оба отскока; очистка и след.')


if __name__ == '__main__':
    verify()
