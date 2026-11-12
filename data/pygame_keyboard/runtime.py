"""Исполнение полных учебных программ по кадрам с настоящей очередью событий."""
import ast
import os

os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
os.environ.setdefault('SDL_AUDIODRIVER', 'dummy')
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')

import pygame


class Program:
    def __init__(self, source):
        tree = ast.parse(source)
        assert isinstance(tree.body[-1], ast.While)
        self.scope = {}
        exec(compile(ast.Module(body=tree.body[:-1], type_ignores=[]), '<init>', 'exec'), self.scope)
        self.body = compile(ast.Module(body=tree.body[-1].body, type_ignores=[]), '<frame>', 'exec')
        pygame.event.clear()
        self.tick()

    def tick(self, *events):
        for event in events:
            pygame.event.post(event)
        exec(self.body, self.scope)
        return self.scope

    def key(self, key, kind=pygame.KEYDOWN):
        return self.tick(pygame.event.Event(kind, key=key))

    @property
    def screen(self):
        return self.scope['screen']
