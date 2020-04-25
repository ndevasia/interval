import sys, os
sys.path.insert(0, os.path.abspath('..'))

from common.gfxutil import CLabelRect, CRectangle
from kivy.graphics import Color, Line, Rectangle
from kivy.graphics.instructions import InstructionGroup
from kivy.core.image import Image

def midi_pitch_to_note_name(pitch):
    """
    Given a numerical MIDI pitch, return the note name, e.g. "C4".
    Assumes that 24 <= pitch <= 96 (C1 through C7).
    """
    residue_to_note_name = [
        'C',
        'C#/Db',
        'D',
        'D#/Eb',
        'E',
        'F',
        'F#/Gb',
        'G',
        'G#/Ab',
        'A',
        'A#/Bb',
        'B'
    ]
    octave = 1
    residue = pitch - 24
    while (residue - 12 >= 0):
        residue -= 12
        octave += 1
    return '{}{}'.format(residue_to_note_name[residue], octave)

def in_bounds(mouse_pos, obj_pos, obj_size):
    """
    Check if a mouse's position is inside an object.
    :param mouse_pos: (x, y) mouse position
    :param obj_pos: (x, y) object position
    :param obj_size: (width, height) object size
    """
    return (mouse_pos[0] >= obj_pos[0]) and \
           (mouse_pos[0] <= obj_pos[0] + obj_size[0]) and \
           (mouse_pos[1] >= obj_pos[1]) and \
           (mouse_pos[1] <= obj_pos[1] + obj_size[1])

class BlockGUI(InstructionGroup):
    def __init__(self, norm, pos, pitch_callback):
        super(BlockGUI, self).__init__()

        self.norm = norm
        self.pos = pos
        self.size = self.norm.nt((495, 495))

        self.add(Color(1, 1, 1))
        self.add(Line(rectangle=(*self.pos, *self.size), width=2))

        ps_pos = (self.pos[0]+self.norm.nv(20), self.pos[1]+self.norm.nv(20))
        self.ps = PitchSelect(norm, ps_pos, pitch_callback)
        self.add(self.ps)

    def on_touch_down(self, pos):
        for submodule in [self.ps]:
            if in_bounds(pos, submodule.pos, submodule.size):
                submodule.on_touch_down(pos)

    def on_update(self, pos):
        self.ps.on_update(pos)

class PitchSelect(InstructionGroup):
    """
    Submodule to select the instrument pitch of SoundBlock in the form of a graphical piano.
    """
    def __init__(self, norm, pos, callback):
        super(PitchSelect, self).__init__()
        self.norm = norm

        self.selected_key = 0
        self.root_pitch = 60
        self.pitch = 60 # default pitch

        self.green = (144/255, 238/255, 144/255)
        self.white = (239/255, 226/255, 222/255)
        self.black = (.2, .2, .2)
        self.color_names = [
            'red', 'orange', 'yellow', 'green', 'teal', 'blue', 'indigo', 'violet',
            'red', 'orange', 'yellow', 'green', 'teal'
        ]
        self.callback = callback
        self.pos = pos
        self.margin = self.norm.nv(20)
        self.white_key_size = self.norm.nt((50, 150))
        self.black_key_size = self.norm.nt((40, 100))
        self.key_margin = self.norm.nv(2) # pixels of space between keys
        self.size = (
            8*self.white_key_size[0] + 7*self.key_margin + 2*self.margin,
            self.white_key_size[1] + 2*self.margin + self.norm.nv(60)
        )
        self.border_color = Color(238/255, 234/255, 202/255) # yellow
        self.border = Line(rectangle=(*self.pos, *self.size), width=2)
        self.add(self.border_color)
        self.add(self.border)

        self.keys = [None] * 13
        self.white_keys = [0, 2, 4, 5, 7, 9, 11, 12]
        self.black_keys = [1, 3, 6, 8, 10]
        key_start = (self.pos[0] + self.margin, self.pos[1] + self.margin)
        unit = self.white_key_size[0] + self.key_margin
        black_key_units = [1, 2, 4, 5, 6]
        for i, m in zip(self.white_keys, range(8)):
            self.keys[i] = Rectangle(
                size=self.white_key_size,
                pos=(key_start[0] + m*unit, key_start[1])
            )
        for i, m in zip(self.black_keys, black_key_units):
            self.keys[i] = CRectangle(
                csize=self.black_key_size,
                cpos=(key_start[0] + m*unit, key_start[1] + self.norm.nv(100))
            )

        self.key_colors = [None] * 13
        for i in self.white_keys:
            self.key_colors[i] = Color(*self.white)
            self.add(self.key_colors[i])
            self.add(self.keys[i])
        for i in self.black_keys:
            self.key_colors[i] = Color(*self.black)
            self.add(self.key_colors[i])
            self.add(self.keys[i])
        self.key_colors[0].rgb = self.green

        self.arrow_size = self.norm.nt((50, 50))
        self.left_pos = (
            self.pos[0] + self.margin,
            self.pos[1] + self.size[1] - self.arrow_size[1] - self.norm.nv(10)
        )
        self.left_off = Rectangle(
            pos=self.left_pos,
            size=self.arrow_size,
            texture=Image('ui/buttons/left_arrow.png').texture
        )
        self.left_on = Rectangle(
            pos=self.left_pos,
            size=self.arrow_size,
            texture=Image('ui/buttons/left_arrow_clicked.png').texture
        )
        self.right_pos = (
            self.pos[0] + self.size[0] - self.margin - self.arrow_size[0],
            self.pos[1] + self.size[1] - self.arrow_size[1] - self.norm.nv(10)
        )
        self.right_off = Rectangle(
            pos=self.right_pos,
            size=self.arrow_size,
            texture=Image('ui/buttons/right_arrow.png').texture
        )
        self.right_on = Rectangle(
            pos=self.right_pos,
            size=self.arrow_size,
            texture=Image('ui/buttons/right_arrow_clicked.png').texture
        )
        # left_off and right_off are always drawn, but when user mouses over an arrow,
        # left_on and right_on are drawn over left_off and right_off
        self.add(Color(1, 1, 1))
        self.add(self.left_off)
        self.add(self.right_off)

        title_pos = (
            self.pos[0] + self.size[0]/2,
            self.pos[1] + self.size[1] - self.margin - self.norm.nv(20)
        )
        self.title = CLabelRect(
            cpos=title_pos,
            text='pitch: {}'.format(midi_pitch_to_note_name(self.pitch)),
            font_size='18')
        self.add(Color(1, 1, 1))
        self.add(self.title)

    def on_touch_down(self, pos):
        for i in self.black_keys:
            if in_bounds(pos, self.keys[i].pos, self.black_key_size):
                self.select(i)
                return # don't also check for white keys
        for i in self.white_keys:
            if in_bounds(pos, self.keys[i].pos, self.white_key_size):
                self.select(i)

        if in_bounds(pos, self.left_off.pos, self.arrow_size):
            self.left_press()
        if in_bounds(pos, self.right_off.pos, self.arrow_size):
            self.right_press()

    def left_press(self):
        if self.root_pitch - 12 < 24: # don't go below C1 in pitch
            return

        index = self.pitch - self.root_pitch
        self.root_pitch -= 12
        self.pitch -= 12
        self.title.set_text('pitch: {}'.format(midi_pitch_to_note_name(self.pitch)))
        self.callback(self.color_names[index], self.pitch)

    def right_press(self):
        if self.root_pitch + 12 >= 96: # don't go above C7 in pitch
            return

        index = self.pitch - self.root_pitch
        self.root_pitch += 12
        self.pitch += 12
        self.title.set_text('pitch: {}'.format(midi_pitch_to_note_name(self.pitch)))
        self.callback(self.color_names[index], self.pitch)

    def left_anim(self, pos):
        if in_bounds(pos, self.left_off.pos, self.arrow_size):
            if self.left_on not in self.children:
                self.add(self.left_on)
        else:
            if self.left_on in self.children:
                self.remove(self.left_on)

    def right_anim(self, pos):
        if in_bounds(pos, self.right_off.pos, self.arrow_size):
            if self.right_on not in self.children:
                self.add(self.right_on)
        else:
            if self.right_on in self.children:
                self.remove(self.right_on)

    def select(self, key):
        if key == self.selected_key:
            return
        previous_select = self.selected_key
        self.key_colors[key].rgb = self.green
        color = self.white if previous_select in self.white_keys else self.black
        self.key_colors[previous_select].rgb = color
        pitch = self.root_pitch + key
        self.title.set_text('pitch: {}'.format(midi_pitch_to_note_name(pitch)))
        self.pitch = pitch
        self.selected_key = key
        self.callback(self.color_names[key], self.pitch)

    def on_update(self, pos):
        self.left_anim(pos)
        self.right_anim(pos)
