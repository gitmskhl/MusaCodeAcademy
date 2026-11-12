"""Снимки только окон примеров Pygame в работающей X11-сессии.

Запуск из корня проекта: DISPLAY=:0 python -m data.pygame_intro.capture
Требуются pygame и ImageMagick (import). Мышь и клавиатура не используются.
"""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

from .content import FINAL, LOOP

ROOT = Path(__file__).resolve().parent
CAPTURES = {
    "window-800x600": LOOP,
    "window-1000x400": LOOP.replace("(800, 600)", "(1000, 400)"),
    "blue-background": FINAL.replace("(0, 0, 0)", "(30, 60, 120)"),
    "practice-result": FINAL.replace("(800, 600)", "(960, 540)").replace("(0, 0, 0)", "(40, 100, 160)"),
}


def main():
    output = ROOT / "images"
    output.mkdir(exist_ok=True)
    env = dict(os.environ, DISPLAY=os.environ.get("DISPLAY", ":0"), SDL_VIDEODRIVER="x11",
               SDL_AUDIODRIVER="dummy", PYGAME_HIDE_SUPPORT_PROMPT="1")
    with tempfile.TemporaryDirectory(prefix="mca-lesson-capture-") as directory:
        for name, source in CAPTURES.items():
            marker = Path(directory) / name
            # Получаем ID именно созданного окна. Код самого примера не меняется.
            hook = f'''
import pygame
from pathlib import Path
original_set_mode = pygame.display.set_mode
def capture_window_id(*args, **kwargs):
    surface = original_set_mode(*args, **kwargs)
    Path({str(marker)!r}).write_text(str(pygame.display.get_wm_info()['window']))
    return surface
pygame.display.set_mode = capture_window_id
'''
            process = subprocess.Popen([sys.executable, "-c", hook + source], env=env,
                                       stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            try:
                deadline = time.monotonic() + 5
                while not marker.exists():
                    if process.poll() is not None:
                        raise RuntimeError(process.stderr.read().decode())
                    if time.monotonic() > deadline:
                        raise TimeoutError("Окно не появилось")
                    time.sleep(0.05)
                time.sleep(0.5)
                target = output / (name + ".png")
                subprocess.run(["import", "-display", env["DISPLAY"], "-frame", "-window",
                                marker.read_text(), str(target)], check=True, timeout=5)
                print(target)
            finally:
                process.terminate()
                try:
                    process.communicate(timeout=1)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.communicate()


if __name__ == "__main__":
    main()
