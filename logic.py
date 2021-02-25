import time, pickle
import tkinter as tk
import numpy as np
from functools import partial, reduce

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
    def interpolate(self, viewport, steps, step):
        vp = Viewport()
        vp.p1 = self.p1 + (viewport.p1-self.p1)/steps * step
        vp.p2 = self.p2 + (viewport.p2-self.p2)/steps * step
        return vp
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
        if not self.path or len(self.path) < 2: return
        p = np.concatenate(list(map(mapper, self.path)))
        obj_id = canvas.create_line(*p, fill=self.color,
            width=self.width*zoom, cap=tk.ROUND, smooth=True, splinesteps=12)
    def boundingbox(self):
        path = np.stack(self.path)
        p1 = path.min(axis=0)
        p2 = path.max(axis=0)
        return p1, p2

class Frame:
    def __init__(self, viewport):
        self.viewport = Viewport(viewport)
        self.create_time = time.time()
        self.modify_time = self.create_time
        self.drawables = []
        self.bb1 = np.array([-1.0, -1.0])
        self.bb2 = np.array([1.0, 1.0])
        print("new frame")
    def pop_stroke(self):
        if not self.drawables: return None
        self.recalc_bounding_box()
        return self.drawables.pop()
    def push_stroke(self, stroke):
        self.drawables.append(stroke)
        self.recalc_bounding_box()
    def recalc_bounding_box(self):
        P1, P2 = zip(*map(lambda d: d.boundingbox(), self.drawables))
        self.bb1 = np.stack(P1).min(axis=0)
        self.bb2 = np.stack(P2).max(axis=0)
    def visible(self, context):
        """True if self is visible from viewport"""
        screen_dim = context.bottomright - context.topleft
        vp_dim = context.viewport.p2 - context.viewport.p1
        margin = context.margin/screen_dim * vp_dim

        if np.any(self.bb1 > context.viewport.p2+margin): return False
        if np.any(self.bb2 < context.viewport.p1-margin): return False
        ratio = (self.bb2 - self.bb1)/vp_dim
        ## Don't render if it will be less than one pixel
        if np.any(ratio > screen_dim): return False
        if np.any(ratio < 1/screen_dim): return False
        return True
    def used_colors(self):
        return set(map(lambda d: d.color, self.drawables))
    def render(self, context):
        f = partial(Viewport.world_to_screen, context=context)
        for drawable in self.drawables:
            drawable.render(context.canvas, f, self.viewport.zoomlevel(context))
        if context.debug:
            (x1, y1) = f(self.viewport.p1)
            (x2, y2) = f(self.viewport.p2)
            obj_id = context.canvas.create_rectangle(x1, y1, x2, y2, outline="#FF0000", width=1)
            (x1, y1) = f(self.bb1)
            (x2, y2) = f(self.bb2)
            obj_id = context.canvas.create_rectangle(x1, y1, x2, y2, outline="#0000FF", width=1)

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
    def previous(self, frame):
        if not frame:
            return self.frame_lru[-1]
        i = self.frame_lru.index(frame)
        if i == 0:
            return self.frame_lru[-1]
        return self.frame_lru[i-1]
    def next(self, frame):
        if not frame:
            return self.frame_lru[-1]
        i = self.frame_lru.index(frame)
        if i == len(self.frames)-1:
            return self.frame_lru[0]
        return self.frame_lru[i+1]
    def push_sketch(self, context):
        if not self.frame_lru or self.frame_lru[-1].viewport != context.viewport:
            frame = Frame(context.viewport)
            self.frames.append(frame)
            self.frame_lru.append(frame)
        else:
            frame = self.frame_lru[-1]
        context.sketch.blit(frame)
    def pop_frame(self, context):
        if not self.frames: return None
        frame = self.frame_lru.pop()
        self.frames.remove(frame)
        return frame
    def pop_stroke(self, context):
        if not self.frames: return None
        frame = self.frame_lru[-1]
        return frame.pop_stroke()
    def update(self, context):
        context.visible_frames = list(
            filter(lambda frame: frame.visible(context), self.frames))
        context.visible_colors = reduce(set.union,
            map(lambda f: f.used_colors(), context.visible_frames), set())
        if context.debug:
            print(f"Visible frames: {len(context.visible_frames)}/{len(self.frames)}")
            print(f"Colors: {context.visible_colors}")
    def render(self, context):
        if context.dirty:
            self.update(context)
            context.dirty = False
        for frame in context.visible_frames:
            frame.render(context)
        ## render color palette
        p1, p2 = context.color_picker_location()
        obj_id = context.canvas.create_oval(*p1, *p2, fill=context.sketch.color, outline="#FFFFFF", activewidth=2, activedash=(3,5))
        for i, color in enumerate(context.visible_colors):
            selected = (context.sketch.color == color)
            p1, p2 = context.palette_location(i)
            obj_id = context.canvas.create_rectangle(*p1, *p2, fill=color, outline="#FFFFFF", activewidth=2, activedash=(3,5))


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
        frame.push_stroke(self.stroke)
        self.stroke = Stroke([], self.color, width=Sketch.width)
    def render(self, context):
        f = partial(Viewport.world_to_screen, context=context)
        self.stroke.render(context.canvas, f, 1, draft=True)

## TODO
# curves
# smooth/simplify strokes
# shapes, text
# tutorial
# alpha blend if zoom is to much (so that we gradually hide frame)
  # use stiple
# rotations
# buttons to transform last stroke to line/box/ellipse
# export button
# Bookmarks (with descr?)
# meta data (mtime, ctime)
# when jump to frame select it for draw/delete/undo

## FEATURES
# Implicit save/load, never lose sketch
# 'infinite' canvas
# Easy color repick
