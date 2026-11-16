"""Проверка поведения образцов и точного соответствия GIF кадрам программ."""
from PIL import Image

from .content import TIMER
from .render import DIGITS, TRAFFIC, DIRECTION, SEGMENTS, ROOT, Sample, frames, scenarios, pygame


def event(kind, key):
    return pygame.event.Event(kind, key=key)


def pixel(sample, point):
    return tuple(sample.screen.get_at(point))[:3]


def verify():
    timer = Sample(TIMER)
    assert timer.runner.scope['timer'] == 119
    for frame in range(2, 361):
        expected = (frame // 120) % 2 == 1
        scope = timer.tick(frame)
        assert scope['bright'] is expected
        assert scope['timer'] == 120 - frame % 120
        assert pixel(timer, (400, 300)) == ((0, 255, 0) if expected else (0, 60, 0))
    assert timer.clock.tick.call_args.args == (60,)

    # Независимая таблица ожидаемых сегментов.
    patterns = ['abcdef', 'bc', 'abdeg', 'abcdg', 'bcfg', 'acdfg', 'acdefg', 'abc', 'abcdefg', 'abcdfg']
    digit = Sample(DIGITS)
    for number in list(range(10)) + [8, 1, 0]:
        key = getattr(pygame, f'K_{number}')
        for events in [(event(pygame.KEYDOWN, key),), (event(pygame.KEYUP, key),), (),
                       (event(pygame.KEYDOWN, pygame.K_SPACE),)]:
            scope = digit.tick(0, *events)
            assert scope['digit'] == number
            for name, (x, y, width, height) in SEGMENTS.items():
                assert pixel(digit, (x+width//2, y+height//2)) == (
                    (0, 255, 0) if name in patterns[number] else (0, 50, 0))
    assert digit.tick(0, event(pygame.KEYDOWN, pygame.K_8), event(pygame.KEYDOWN, pygame.K_1))['digit'] == 1

    traffic = Sample(TRAFFIC)
    for frame in range(2, 721):
        cycle = frame % 360
        state = 0 if cycle < 120 else 1 if cycle < 180 else 2 if cycle < 300 else 3
        scope = traffic.tick(frame)
        assert scope['state'] == state
        assert 1 <= scope['timer'] <= (120 if state in (0, 2) else 60)
        assert pixel(traffic, (180, 140)) == ((255, 0, 0) if state in (0, 1) else (60, 0, 0))
        assert pixel(traffic, (180, 270)) == ((255, 255, 0) if state in (1, 3) else (60, 60, 0))
        assert pixel(traffic, (180, 400)) == ((0, 255, 0) if state == 2 else (0, 60, 0))

    moving = Sample(DIRECTION)
    assert moving.screen.get_size() == (800, 600)
    assert pixel(moving, (403, 300)) == (0, 255, 0)
    for key, vx, vy in [(pygame.K_w, 0, -3), (pygame.K_a, -3, 0),
                        (pygame.K_s, 0, 3), (pygame.K_d, 3, 0)]:
        scope = moving.tick(0, event(pygame.KEYDOWN, key))
        assert (scope['vx'], scope['vy']) == (vx, vy)
        for events in [(event(pygame.KEYUP, key),), (), (event(pygame.KEYDOWN, key),),
                       (event(pygame.KEYDOWN, pygame.K_SPACE),), (pygame.event.Event(pygame.MOUSEMOTION),)]:
            x, y = scope['x'], scope['y']
            moving.tick(0, *events)
            assert (scope['x'], scope['y']) == (x+vx, y+vy)
            assert (scope['vx'], scope['vy']) == (vx, vy)
    scope = moving.tick(0, event(pygame.KEYDOWN, pygame.K_w), event(pygame.KEYDOWN, pygame.K_a))
    assert (scope['vx'], scope['vy']) == (-3, 0)
    for _ in range(30):
        moving.tick(0)
    # Все пиксели игрового поля: зеленый круг и черный фон, без следов.
    expected = pygame.Surface((800, 600))
    expected.fill((0, 0, 0))
    pygame.draw.circle(expected, (0, 255, 0), (scope['x'], scope['y']), 20)
    assert pygame.image.tostring(expected, 'RGB') == pygame.image.tostring(moving.screen, 'RGB')
    assert pixel(moving, (scope['x']+19, scope['y'])) == (0, 255, 0)
    assert pixel(moving, (scope['x']+20, scope['y'])) == (0, 0, 0)

    for source in [TIMER, DIGITS, TRAFFIC, DIRECTION]:
        sample = Sample(source)
        try:
            sample.tick(500, pygame.event.Event(pygame.QUIT))
        except SystemExit:
            pass
        else:
            raise AssertionError('QUIT не завершил программу')

    total_frames = 0
    for filename, source, timeline in scenarios():
        width, height = Sample(source).screen.get_size()
        game_rect = ((800-width)//2, 80, (800+width)//2, height+80)
        with Image.open(ROOT / 'images' / filename) as saved:
            expected_sequence = list(frames(source, timeline))
            # GIF может объединять одинаковые соседние кадры: сверяем по времени.
            saved_index, remaining = 0, 0
            for image, duration in expected_sequence:
                if remaining == 0:
                    saved.seek(saved_index)
                    remaining = saved.info['duration']
                    saved_index += 1
                # Сглаженный шрифт плашки квантуется GIF; игровое поле сверяем точно.
                assert saved.convert('RGB').crop(game_rect).tobytes() == image.crop(game_rect).tobytes(), (filename, saved_index)
                remaining -= duration
                assert remaining >= 0
                total_frames += 1
            assert remaining == 0 and saved_index == saved.n_frames
    pygame.quit()
    print(f'Проверены таймер, цифры 0–9, два цикла светофора, WASD, отпускание, QUIT и {total_frames} кадров GIF.')


if __name__ == '__main__':
    verify()
