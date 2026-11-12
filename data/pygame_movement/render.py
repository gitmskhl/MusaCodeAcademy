"""GIF из реальных кадров программ урока. Запуск Python с pygame и Pillow."""
import ast
import os
from pathlib import Path
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
import pygame
from PIL import Image, ImageDraw, ImageFont
from .content import ANIMATIONS

ROOT = Path(__file__).resolve().parent


def render(only=None):
    font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 18)
    for _, filename, _, source, iterations, capture_every in ANIMATIONS:
        if only and filename != only:
            continue
        tree = ast.parse(source)
        loop = tree.body[-1]
        assert isinstance(loop, ast.While)
        namespace = {}
        exec(compile(ast.Module(body=tree.body[:-1], type_ignores=[]), filename, 'exec'), namespace)
        body = compile(ast.Module(body=loop.body, type_ignores=[]), filename, 'exec')
        frames = []
        for tick in range(iterations + 1):
            if tick:
                exec(body, namespace)
            else:
                # Начальное положение до первого изменения координат.
                screen = namespace['screen']
                screen.fill((0, 0, 0))
                pygame.draw.circle(screen, (0, 255, 0),
                                   (namespace.get('x', 400), namespace.get('y', 300)), 20)
            if tick % capture_every:
                continue
            screen = namespace['screen']
            image = Image.new('RGB', (800, 650), '#18212d')
            image.paste(Image.frombytes('RGB', (800, 600), pygame.image.tostring(screen, 'RGB')), (0, 50))
            draw = ImageDraw.Draw(image)
            draw.text((12, 6), f'Проход: {tick}    x = {namespace.get("x", 400):.1f}    y = {namespace.get("y", 300):.1f}', font=font, fill='white')
            draw.text((12, 28), f'800 × 600  |  выбранные кадры, каждые {capture_every} проходов', font=font, fill='#a9bed5')
            if filename == 'jump.gif':
                # Образец результата: только содержимое окна, без счетчиков.
                if tick == iterations:
                    continue  # Начальный кадр повторится при зацикливании GIF.
                image = image.crop((0, 50, 800, 650))
            frames.append(image)
        target = ROOT / 'images' / filename
        frames[0].save(target, save_all=True, append_images=frames[1:], duration=50, loop=0, optimize=True)
        with Image.open(target) as gif:
            assert gif.is_animated and gif.n_frames > 1
        assert target.stat().st_size < 10 * 1024 * 1024
        print(f'{filename}: {len(frames)} кадров; {target.stat().st_size} байт')
    pygame.quit()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--only', choices=[item[1] for item in ANIMATIONS])
    render(parser.parse_args().only)
