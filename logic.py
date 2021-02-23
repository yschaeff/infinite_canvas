#!/usr/bin/env python3
import time, pickle
import tkinter as tk
import numpy as np
from tkinter import colorchooser, Button
from functools import partial

def pairs(l, loop=False):
    if not l: return
    first = l[0]
    for i in l[1:]:
        second = i
        yield (first, second)
        first = second
    if loop:
        yield (first, l[0])

class Viewport:
    def __init__(self, viewport=None):
        if viewport:
            self.p1 = viewport.p1.copy()
            self.p2 = viewport.p2.copy()
        else:
            self.p1 = np.array([-1.0, -1.0])
            self.p2 = np.array([1.0, 1.0])
    def __eq__(self, other):
        return np.all(self.p1 == other.p1) and np.all(self.p2 == other.p2)
    def world_to_screen(p, context):
        screen_dim = context.bottomright - context.topleft
        vp_dim = context.viewport.p2 - context.viewport.p1
        pos = (p - context.viewport.p1)/vp_dim * screen_dim +\
            context.topleft
        return pos
    def screen_to_world(self, context, cursor_pos):
        screen_dim = context.bottomright - context.topleft
        vp_dim = context.viewport.p2 - context.viewport.p1

        pos = (cursor_pos - context.topleft)/screen_dim * vp_dim +\
            context.viewport.p1
        return pos
    def pan(self, context, pixel_delta):
        """ Pan this viewport by pixel_delta. Calculate world shift
            with global viewport """
        screen_dim = context.bottomright - context.topleft
        vp_dim = context.viewport.p2 - context.viewport.p1
        d = pixel_delta/screen_dim * vp_dim
        self.p1 += d
        self.p2 += d
    def zoom(self, context, cursor_pos, zoomin):
        origin = self.screen_to_world(context, cursor_pos)
        zoomfactor = 0.1
        if zoomin:
            self.p1 += (origin - self.p1) * zoomfactor
            self.p2 += (origin - self.p2) * zoomfactor
        else:
            self.p1 -= (origin - self.p1) * zoomfactor
            self.p2 -= (origin - self.p2) * zoomfactor
    def zoomlevel(self, context):
        vp_dim = context.viewport.p2 - context.viewport.p1
        my_dim = self.p2 - self.p1
        return (my_dim / vp_dim)[0]


    def visible(self, context):
        """True if self is visible from viewport"""
        screen_dim = context.bottomright - context.topleft
        vp_dim = context.viewport.p2 - context.viewport.p1
        margin = context.margin/screen_dim * vp_dim
        #margin = context.viewport.screen_to_world(context, context.margin)
        #print(context.margin, margin, screen_dim, vp_dim)
        my_dim = self.p2 - self.p1

        if np.any(self.p1-margin > context.viewport.p2+margin): return False
        if np.any(self.p2+margin < context.viewport.p1-margin): return False
        ratio = my_dim/vp_dim
        ## Don't render if it will be less than one pixel
        if np.any(ratio > screen_dim): return False
        if np.any(ratio < 1/screen_dim): return False
        return True
    def __str__(self):
        return f"<vp: {self.p1}, {self.p2}>"

class Stroke:
    def __init__(self, path, color, style=None, width=10):
        self.path = path
        self.color = color
        self.style = style
        self.width = width
    def render(self, canvas, mapper, zoom, draft=False):
        radius = 10;
        if draft and self.path:
            p1 = mapper(self.path[0]) + np.array([-radius, -radius])
            p2 = mapper(self.path[0]) + np.array([radius, radius])
            (x1, y1), (x2, y2) = p1, p2
            obj_id = canvas.create_oval(x1, y1, x2, y2, fill="#BC347F", width=self.width*3)
            p1 = mapper(self.path[-1]) + np.array([-radius, -radius])
            p2 = mapper(self.path[-1]) + np.array([radius, radius])
            (x1, y1), (x2, y2) = p1, p2
            obj_id = canvas.create_oval(x1, y1, x2, y2, fill="#BC347F", width=self.width*3)
        for p1, p2 in pairs(self.path, loop=False):
            (x1, y1) = mapper(p1)
            (x2, y2) = mapper(p2)
            obj_id = canvas.create_line(x1, y1, x2, y2, fill=self.color, width=self.width*zoom)

class Frame:
    def __init__(self, viewport):
        self.viewport = Viewport(viewport)
        self.create_time = time.time()
        self.modify_time = self.create_time
        self.drawables = []
        print("new frame")
    def pop_stroke(self):
        if not self.drawables: return None
        return self.drawables.pop()
    def render(self, context):
        f = partial(Viewport.world_to_screen, context=context)
        for drawable in self.drawables:
            drawable.render(context.canvas, f, self.viewport.zoomlevel(context))

class Data:
    def __init__(self):
        """Only exec when starting fresh"""
        print("created")
        self.frames = []
        self.frame_lru = []
    def initialize(self):
        """exec always"""
        print("init")
        self.resolution = 500
    def push_sketch(self, context):
        if not self.frame_lru or self.frame_lru[-1].viewport != context.viewport:
            frame = Frame(context.viewport)
            self.frames.append(frame)
            self.frame_lru.append(frame)
        else:
            frame = self.frame_lru[-1]
        context.sketch.blit(frame)
    def pop_frame(self):
        if not self.frames: return None
        frame = self.frame_lru.pop()
        self.frames.remove(frame)
        return frame
    def pop_stroke(self):
        if not self.frames: return None
        frame = self.frame_lru[-1]
        return frame.pop_stroke()

    def render(self, context):
        drawn = 0
        hidden = 0
        for frame in self.frames:
            if frame.viewport.visible(context): ## maybe calculate this only on move
                drawn += 1
                frame.render(context)
            else:
                hidden += 1
        print(f"drawn {drawn} hidden {hidden}")

class Sketch:
    width = 3
    def __init__(self):
        self.color = "#BCB534"
        self.stroke = Stroke([], self.color, width=Sketch.width)
    def set_color(self, color):
        self.color = color
        self.stroke.color = color
    def push(self, p):
        self.stroke.path.append( p )
    def blit(self, frame):
        print(f"Adding stroke {id(self.stroke)} to frame {id(frame)}. len: {len(self.stroke.path)}")
        frame.drawables.append(self.stroke)
        self.stroke = Stroke([], self.color, width=Sketch.width)
    def render(self, context):
        f = partial(Viewport.world_to_screen, context=context)
        self.stroke.render(context.canvas, f, 1, draft=True)

## TODO
# display colors on screen
# move between frames (animate)
# line thicknes compensation
# do not draw frames off screen
#do not draw frames that are x times bigger than current
# curves
# shapes, text
# tutorial
