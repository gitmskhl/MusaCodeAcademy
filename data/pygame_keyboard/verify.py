"""Поведенческая проверка примеров, очереди событий, ДЗ и кадров GIF."""
from contextlib import redirect_stdout
from io import StringIO

from PIL import Image
from . import content
from .render import HOMEWORK, ROOT, scenarios
from .runtime import Program, pygame


def verify():
    count = 0
    for step in content.LESSON['steps']:
        for block in step['content']['blocks']:
            if block['type'] != 'code':
                continue
            with redirect_stdout(StringIO()):
                runner = Program(block['data']['code'])
                assert pygame.key.get_repeat() == (0, 0)
                runner.key(pygame.K_RIGHT)
                for _ in range(20):
                    runner.tick()
                runner.key(pygame.K_RIGHT, pygame.KEYUP)
                runner.tick(pygame.event.Event(pygame.MOUSEMOTION, pos=(1, 1), rel=(1, 1), buttons=(0, 0, 0)))
                try:
                    runner.tick(pygame.event.Event(pygame.QUIT))
                except SystemExit:
                    pass
                else:
                    raise AssertionError('Крестик не завершает программу')
            count += 1
    output = StringIO()
    with redirect_stdout(output):
        runner = Program(content.ANY_KEY)
        runner.key(pygame.K_a)
        runner.tick()
        runner.key(pygame.K_a, pygame.KEYUP)
    assert output.getvalue() == 'Клавиша нажата!\n'
    for source in [content.ONE_COLOR, content.COLORS]:
        runner = Program(source)
        assert runner.screen.get_at((10, 10))[:3] == (0, 0, 0)
        keys = [(pygame.K_r, (255, 0, 0))]
        if source == content.COLORS:
            keys += [(pygame.K_g, (0, 255, 0)), (pygame.K_b, (0, 0, 255)), (pygame.K_SPACE, (0, 0, 0))]
        for key, color in keys:
            runner.key(key)
            runner.key(key, pygame.KEYUP)
            runner.key(pygame.K_z)
            for _ in range(20):
                runner.tick()
            assert runner.screen.get_at((10, 10))[:3] == color
    runner = Program(content.MOVE)
    runner.key(pygame.K_RIGHT)
    for _ in range(100):
        runner.tick()
    assert (runner.scope['x'], runner.scope['y']) == (420, 300)
    assert runner.screen.get_at((390, 300))[:3] == (0, 0, 0)  # Видимая часть старого круга стерта.
    runner.key(pygame.K_RIGHT, pygame.KEYUP)
    assert runner.scope['x'] == 420
    # Несколько событий за один кадр: учитываются все нажатия, но не отпускания.
    runner.tick(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RIGHT),
                pygame.event.Event(pygame.KEYUP, key=pygame.K_RIGHT),
                pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RIGHT))
    assert runner.scope['x'] == 460
    for key, expected in [(pygame.K_DOWN, (460, 320)), (pygame.K_LEFT, (440, 320)),
                          (pygame.K_UP, (440, 300)), (pygame.K_SPACE, (440, 300))]:
        runner.key(key)
        assert (runner.scope['x'], runner.scope['y']) == expected
    runner = Program(HOMEWORK)
    def colors():
        return tuple(runner.screen.get_at(pos)[:3] for pos in [(250, 300), (550, 300)])
    red, blue = (255, 0, 0), (0, 0, 255)
    assert colors() == (red, red)
    for key, expected in [(pygame.K_a, (blue, red)), (pygame.K_d, (red, blue)),
                          (pygame.K_d, (red, blue)), (pygame.K_SPACE, (red, red)),
                          (pygame.K_a, (blue, red)), (pygame.K_SPACE, (red, red)),
                          (pygame.K_d, (red, blue)), (pygame.K_z, (red, blue))]:
        runner.key(key)
        runner.key(key, pygame.KEYUP)
        runner.tick()
        assert colors() == expected
    # Проверяем всю игровую область каждого кадра GIF против исполнения программы.
    for filename, source, timeline in scenarios():
        runner = Program(source)
        with Image.open(ROOT / 'images' / filename) as gif:
            assert gif.size == (800, 680) and gif.info['loop'] == 0
            assert gif.n_frames == len(timeline)
            for index, (kind, key, _, _, duration) in enumerate(timeline):
                runner.tick(*([pygame.event.Event(kind, key=key)] if kind else []))
                gif.seek(index)
                assert gif.info['duration'] == duration
                expected = pygame.image.tostring(runner.screen, 'RGB')
                assert gif.convert('RGB').crop((0, 80, 800, 680)).tobytes() == expected, (filename, index)
    pygame.quit()
    print(f'PASS: {count} программ; KEYDOWN/KEYUP, посторонние события, QUIT; сохранение цвета; шаги и паузы; ДЗ; все игровые кадры четырех GIF.')


if __name__ == '__main__':
    verify()
