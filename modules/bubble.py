import sys, os
sys.path.insert(0, os.path.abspath('..'))

from common.core import lookup
from common.gfxutil import topleft_label, CEllipse, CRectangle, CLabelRect, AnimGroup, KFAnim
from common.note import NoteGenerator, Envelope
from kivy.graphics import Color, Line
from kivy.graphics.instructions import InstructionGroup
from kivy.core.window import Window

import numpy as np

def timbre_to_shape(timbre, pos):
    if timbre == 'sine':
        return CEllipse(cpos=pos, size=(80, 80), segments=20)
    elif timbre == 'triangle':
        return CEllipse(cpos=pos, size=(90, 90), segments=3)
    elif timbre == 'square':
        return CRectangle(cpos=pos, size=(80, 80))
    elif timbre == 'sawtooth':
        # square rotated 45 degrees
        return CEllipse(cpos=pos, size=(90, 90), segments=4)

downwards_gravity = np.array((0, -1800))
damping_factor = 0.85

class PhysicsBubble(InstructionGroup):
    """
    This module is a drag-and-release physics-based bubble that plays a sound upon colliding with
    another collidable object, including the sandbox edges.
    """
    name = 'PhysicsBubble'

    def __init__(self, pos, vel, pitch, timbre, color, bounces, gravity=False, callback=None):
        """
        :param pos: initial position
        :param vel: initial velocity
        :param pitch: MIDI pitch value, where 60 is middle C
        :param timbre: type of waveform, e.g. 'sine' or 'sawtooth'
        :param color: 3-tuple of RGB color
        :param bounces: number of times the bubble bounces before fading away
        :param gravity: whether or not the bubble is subjected to downwards gravity
        :param callback: the sound function that is called when the bubble bounces
        """
        super(PhysicsBubble, self).__init__()

        self.r = 40
        self.pos = np.array(pos, dtype=np.float)
        self.vel = 2 * np.array(vel, dtype=np.float)

        self.pitch = pitch
        self.timbre = timbre
        self.color = Color(*color)
        self.text_color = Color(0, 0, 0)
        self.bounces = bounces
        self.gravity = gravity
        self.callback = callback

        self.text = CLabelRect(cpos=pos, text=str(self.bounces))
        self.bubble = timbre_to_shape(self.timbre, pos)

        self.add(self.color)
        self.add(self.bubble)
        self.add(self.text_color)
        self.add(self.text)

        # have the bubble fade away when self.bounces = 0
        self.fade_anim = KFAnim((0, 1), (0.25, 0))
        self.time = 0

        self.on_update(0)

    def on_update(self, dt):
        if self.gravity:
            self.vel += downwards_gravity * dt
            self.pos += self.vel * dt
        else:
            self.pos += self.vel * dt

        if self.bounces > 0:
            if self.check_for_collisions() and self.callback is not None:
                self.callback(self.pitch, self.timbre)
        else:
            self.color.a = self.fade_anim.eval(self.time)
            self.time += dt

        self.bubble.set_cpos(self.pos)
        self.text.set_cpos(self.pos)

        return self.fade_anim.is_active(self.time)

    def check_for_collisions(self):
        # collision with bottom
        if self.pos[1] - self.r < 0:
            self.vel[1] = -self.vel[1] * damping_factor if self.gravity else -self.vel[1]
            self.pos[1] = self.r
            self.bounces -= 1
            self.text.set_text(str(self.bounces))
            return True

        # collision with top
        if self.pos[1] + self.r > Window.height:
            self.vel[1] = -self.vel[1]
            self.pos[1] = Window.height - self.r
            self.bounces -= 1
            self.text.set_text(str(self.bounces))
            return True

        # collision with left
        if self.pos[0] - self.r < 0:
            self.vel[0] = -self.vel[0]
            self.pos[0] = self.r
            self.bounces -= 1
            self.text.set_text(str(self.bounces))
            return True

        # collision with right
        if self.pos[0] + self.r > Window.width:
            self.vel[0] = -self.vel[0]
            self.pos[0] = Window.width - self.r
            self.bounces -= 1
            self.text.set_text(str(self.bounces))
            return True

class PhysicsBubbleHandler(object):
    """
    Handles user interaction and drawing of graphics before generating a PhysicsBubble.
    Also stores and updates all currently active PhysicsBubbles.
    """
    def __init__(self, canvas, mixer, client, client_id):
        self.module_name = 'PhysicsBubble'
        self.canvas = canvas
        self.mixer = mixer
        self.client = client
        self.cid = client_id

        # many variables here are dicts because a user's module handler needs to keep track of
        # not just its own variables, but other users' variables as well! so we use dictionaries
        # with client ids as the keys.
        self.hold_line = {}
        self.hold_point = {}
        self.hold_shape = {}
        self.text = {}
        self.text_color = Color(0, 0, 0)

        # TODO: update to use nisha's proposed pastel color palette
        self.color_dict = {
            'red': (255/255, 61/255, 40/255),
            'orange': (252/255, 144/255, 22/255),
            'yellow': (255/255, 255/255, 103/255),
            'green': (146/255, 205/255, 45/255),
            'blue': (71/255, 142/255, 191/255),
            'teal': (86/255, 190/255, 172/255),
            'violet': (143/255, 136/255, 191/255),
            'pink': (248/255, 133/255, 191/255)
        }
        self.pitch_list = [60, 62, 64, 65, 67, 69, 71, 72]

        self.default_color = self.color_dict['red']
        self.default_pitch = self.pitch_list[0]
        self.default_timbre = 'sine'
        self.default_bounces = 5
        self.default_gravity = False

        self.color = {}
        self.pitch = {}
        self.timbre = {}
        self.bounces = {}
        self.gravity = {}

        # flag used to only display controls when this module is synced
        # see on_update() and sync_state()
        self.display = False

        self.bubbles = AnimGroup()
        self.canvas.add(self.bubbles)

    def on_touch_down(self, cid, pos):
        """
        Start drawing the drag line and preview of the PhysicsBubble.
        """
        self.hold_point[cid] = pos
        self.hold_shape[cid] = timbre_to_shape(self.timbre[cid], pos)
        self.hold_line[cid] = Line(points=(*pos, *pos), width=3)
        self.text[cid] = CLabelRect(cpos=pos, text=str(self.bounces[cid]))

        self.canvas.add(Color(*self.color[cid]))
        self.canvas.add(self.hold_shape[cid])
        self.canvas.add(self.hold_line[cid])
        self.canvas.add(self.text_color)
        self.canvas.add(self.text[cid])

    def on_touch_move(self, cid, pos):
        """
        Update the position of the drag line and preview of the PhysicsBubble.
        """
        self.hold_shape[cid].set_cpos(pos)
        self.text[cid].set_cpos(pos)
        self.hold_line[cid].points = (*self.hold_point[cid], *pos)

    def on_touch_up(self, cid, pos):
        """
        Release the PhysicsBubble.
        """
        self.canvas.remove(self.hold_shape[cid])
        self.canvas.remove(self.text[cid])
        self.canvas.remove(self.hold_line[cid])

        # calculate velocity
        hold_point = self.hold_point[cid]
        dx = pos[0] - hold_point[0]
        dy = pos[1] - hold_point[1]
        vel = (-dx, -dy)

        pitch = self.pitch[cid]
        timbre = self.timbre[cid]
        color = self.color[cid]
        bounces = self.bounces[cid]
        gravity = self.gravity[cid]

        bubble = PhysicsBubble(
            pos, vel, pitch, timbre, color, bounces, gravity=gravity, callback=self.sound
        )
        self.bubbles.add(bubble)

    def on_key_down(self, cid, key):
        index = lookup(key, '12345678', range(8))
        color = lookup(key, '12345678', [
            'red', 'orange', 'yellow', 'green', 'blue', 'teal', 'violet', 'pink'
        ])
        if index is not None:
            self.pitch[cid] = self.pitch_list[index]
            self.color[cid] = self.color_dict[color]

        d_bounces = lookup(key, ['up', 'down'], [1, -1])
        if d_bounces is not None:
            self.bounces[cid] += d_bounces

        timbre = lookup(key, 'qwer', ['sine', 'square', 'triangle', 'sawtooth'])
        if timbre is not None:
            self.timbre[cid] = timbre

        if key == 'g': # toggle gravity
            self.gravity[cid] = not self.gravity[cid]

        # other clients should update their state to reflect this client's new selection.
        if self.cid == cid: # don't want every client updating server's state at the same time!
            self.update_server_state(post=False)

    def sound(self, pitch, timbre):
        """
        Play a sound when a PhysicsBubble collides with a collidable object.
        """
        note = NoteGenerator(pitch, 1, timbre)
        env = Envelope(note, 0.01, 1, 0.2, 2)
        self.mixer.add(env)

    def display_controls(self):
        """
        Provides additional info specific to this module to go on the top-left label.
        """
        if self.display:
            info = 'pitch: {}\n'.format(self.pitch[self.cid])
            info += 'timbre: {}\n'.format(self.timbre[self.cid])
            info += 'bounces: {}\n'.format(self.bounces[self.cid])
            info += 'gravity: {}\n'.format(self.gravity[self.cid])
            return info
        else:
            return ''

    def on_update(self):
        self.bubbles.on_update()

    def update_server_state(self, post=False):
        """
        Update server state. If post is True, relay this updated state to all clients.
        """
        state = {
            'color': self.color,
            'pitch': self.pitch,
            'timbre': self.timbre,
            'bounces': self.bounces,
            'gravity': self.gravity
        }
        data = {'module': self.module_name, 'cid': self.cid, 'state': state, 'post': post}
        self.client.emit('update_state', data)

    def update_client_state(self, cid, state):
        """
        Update this handler's state.
        """
        if cid != self.cid: # this client already updated its own state
            self.color = state['color']
            self.pitch = state['pitch']
            self.timbre = state['timbre']
            self.bounces = state['bounces']
            self.gravity = state['gravity']

    def sync_state(self, state):
        """
        Initial sync with the server's copy of module state.
        We don't sync with hold_shape, hold_point, and hold_line because those objects are not
        json-serializable and are short-term values anyway.
        """
        self.color = state['color']
        self.pitch = state['pitch']
        self.timbre = state['timbre']
        self.bounces = state['bounces']
        self.gravity = state['gravity']

        # after initial sync, add default values for this client
        self.color[self.cid] = self.default_color
        self.pitch[self.cid] = self.default_pitch
        self.timbre[self.cid] = self.default_timbre
        self.bounces[self.cid] = self.default_bounces
        self.gravity[self.cid] = self.default_gravity

        # now that default values are set, we can display this module's info
        self.display = True

        # update server with these default values
        # post=True here because we want all other clients' states to update with this client's
        # default values.
        self.update_server_state(post=True)
