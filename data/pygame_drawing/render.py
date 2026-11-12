"""Учебные схемы: реальные круги Pygame с подписями за пределами области окна.

Запуск: SDL_VIDEODRIVER=dummy python -m data.pygame_drawing.render
Нужен Pygame; для русских подписей используется системный DejaVu Sans.
"""
from pathlib import Path
import pygame

ROOT = Path(__file__).resolve().parent
INK = (30, 43, 60)
PAPER = (244, 247, 251)
BLUE = (135, 206, 235)
ACCENT = (177, 35, 55)


def render_extreme_points(root, font, heading):
    """Увеличенная геометрическая схема для примера (400, 300), r = 50."""
    canvas = pygame.Surface((1000, 740))
    canvas.fill(PAPER)

    def label(value, position, color=INK, centered=False):
        surface = font.render(value, True, color)
        rect = surface.get_rect(midtop=position) if centered else surface.get_rect(topleft=position)
        canvas.blit(surface, rect)

    canvas.blit(heading.render("Центр, радиус и четыре крайние точки круга", True, INK), (40, 25))
    label("Пример из урока: центр (400, 300), радиус 50", (40, 68))
    center = (500, 370)
    radius = 150
    pygame.draw.circle(canvas, (255, 255, 255), center, radius)
    pygame.draw.circle(canvas, INK, center, radius, 2)
    pygame.draw.line(canvas, (180, 190, 200), (350, 370), (650, 370), 2)
    pygame.draw.line(canvas, (180, 190, 200), (500, 220), (500, 520), 2)
    pygame.draw.line(canvas, (220, 110, 10), center, (650, 370), 4)
    label("r = 50", (545, 333), (160, 75, 0))

    for point in [(350, 370), (650, 370), (500, 220), (500, 520), center]:
        pygame.draw.circle(canvas, ACCENT, point, 6)
    label("Центр (400, 300)", (500, 407), ACCENT, centered=True)

    for position, lines, centered in [
        ((500, 112), ["Верхняя точка", "(x, y − r)", "(400, 250)"], True),
        ((500, 550), ["Нижняя точка", "(x, y + r)", "(400, 350)"], True),
        ((65, 326), ["Левая точка", "(x − r, y)", "(350, 300)"], False),
        ((725, 326), ["Правая точка", "(x + r, y)", "(450, 300)"], False),
    ]:
        for index, value in enumerate(lines):
            label(value, (position[0], position[1] + index * 30), centered=centered)
    label("Схема увеличена в 3 раза; подписи — координаты в окне игры.", (40, 680))
    pygame.image.save(canvas, root / "extreme-points.png")


def render():
    pygame.font.init()
    font_path = pygame.font.match_font("dejavusans")
    if font_path is None:
        raise RuntimeError("Для подписей установите DejaVu Sans")
    font = pygame.font.Font(font_path, 20)
    heading = pygame.font.Font(font_path, 25)
    root = ROOT / "images"
    root.mkdir(exist_ok=True)
    for filename, center, title, formula in [
        ("coordinates.png", (400, 300), "Координаты в окне 800×600", "x — вправо, y — вниз. Отмечен центр круга."),
        ("left-wall.png", (50, 300), "Касание левой стенки: центр (50, 300), радиус 50", "Левый край: x − r = 50 − 50 = 0"),
        ("right-wall.png", (750, 300), "Касание правой стенки: центр (750, 300), радиус 50", "Правый край: x + r = 750 + 50 = 800"),
        ("bottom-right.png", (750, 550), "Касание правой и нижней стенок: центр (750, 550)", "750 + 50 = 800; 550 + 50 = 600"),
    ]:
        canvas = pygame.Surface((1000, 800))
        canvas.fill(PAPER)
        # Здесь фигура рисуется в исходных координатах окна, без масштабирования.
        screen = pygame.Surface((800, 600))
        screen.fill(BLUE)
        pygame.draw.circle(screen, (255, 255, 255), center, 50)
        pygame.draw.line(screen, (72, 137, 164), (0, center[1]), center, 1)
        pygame.draw.line(screen, (72, 137, 164), (center[0], 0), center, 1)
        pygame.draw.circle(screen, ACCENT, center, 4)
        canvas.blit(screen, (100, 105))
        pygame.draw.rect(canvas, INK, (99, 104, 802, 602), 1)
        pygame.draw.line(canvas, INK, (100, 84), (900, 84), 2)
        pygame.draw.polygon(canvas, INK, [(900, 84), (889, 78), (889, 90)])
        pygame.draw.line(canvas, INK, (80, 105), (80, 705), 2)
        pygame.draw.polygon(canvas, INK, [(80, 705), (74, 694), (86, 694)])
        canvas.blit(heading.render(title, True, INK), (30, 20))
        canvas.blit(font.render("(0, 0)", True, INK), (100, 57))
        canvas.blit(font.render("x", True, INK), (920, 68))
        canvas.blit(font.render("y", True, INK), (45, 680))
        canvas.blit(font.render("800", True, INK), (866, 57))
        canvas.blit(font.render("600", True, INK), (25, 715))
        # Подпись отодвинута влево у правой стенки, чтобы не обрезаться.
        label_x = min(center[0] + 112, 715)
        canvas.blit(font.render(str(center), True, ACCENT), (label_x, center[1] + 113))
        canvas.blit(heading.render(formula, True, INK), (100, 742))
        pygame.image.save(canvas, root / filename)
    render_extreme_points(root, font, heading)
    pygame.quit()


if __name__ == "__main__":
    render()
