#####################################################################
#
# synth.py
#
# Copyright (c) 2015, Eran Egozy
#
# Released under the MIT License (http://opensource.org/licenses/MIT)
#
#####################################################################

import numpy as np
from . import fluidsynth
from .audio import Audio

# create another kind of generator that generates audio based on the fluid
# synth synthesizer
class Synth(fluidsynth.Synth, object):
    """
    Generator that creates sounds from a FluidSynth synthesizer bank.
    """

    def __init__(self, filepath, gain = 0.8):
        """
        :param filepath: Path to the file containing the synthesizer bank.
        :param gain: The gain, a float between 0 and 1.
        """
        super(Synth, self).__init__(gain, samplerate=Audio.sample_rate)
        self.sfid = self.sfload(filepath)
        if self.sfid == -1:
            raise Exception('Error in fluidsynth.sfload(): cannot open ' + filepath)
        self.program(0, 0, 0)

    def program(self, chan, bank, preset):
        """
        Essentially defines which instrument this generator's synth uses.
        Specific *bank* and *preset* combinations can be used to switch between different instruments.

        :param chan: The channel to use for audio playback.
        :param bank: The sound bank to use.
        :param preset: The preset to use.
        """

        self.program_select(chan, self.sfid, bank, preset)

    def generate(self, num_frames, num_channels):
        """
        Generates and returns frames. Should be called every frame.

        :param num_frames: An integer number of frames to generate.
        :param num_channels: Number of channels. Can be 1 (mono) or 2 (stereo)

        :returns: A tuple ``(output, True)``. The output is a numpy array of length
            **(num_frames * num_channels)**
        """

        assert(num_channels == 2)
        # get_samples() returns interleaved stereo, so all we have to do is scale
        # the data to [-1, 1].
        samples = self.get_samples(num_frames).astype(np.float32)
        samples *= (1.0/32768.0)
        return (samples, True)

    def noteon(self, chan, key, vel):
        """
        Plays a note.

        :param chan: The channel to use for audio playback.
        :param key: The midi key to play.
        :param vel: The velocity to play the note at -- correlates with volume.
            Ranges from 0 to 127.
        """
        super().noteon(chan, key, vel)

    def noteoff(self, chan, key):
        """
        Stops a note.

        :param chan: The channel on which the note should be stopped.
        :param key: The key to stop.
        """
        super().noteoff(chan, key)

    def pitch_bend(self, chan, val):
        """
        Adjust pitch of a playing channel by small amounts.
        A pitch bend value of 0 is no pitch change from default.
        A value of -2048 is 1 semitone down.
        A value of 2048 is 1 semitone up.
        Maximum values are -8192 to +8192 (transposing by 4 semitones).

        :param channel: The channel to use for audio playback.
        :param val: The value to adjust pitch by, as specified above.
        """
        super().pitch_bend(chan, val)

    def cc(self, chan, ctrl, val):
        """
        Send control change value. The controls that are recognized
        are dependent on the SoundFont. 
        Typical values include -

            | 1 : vibrato
            | 7 : volume
            | 10 : pan (left to right)
            | 11 : expression (soft to loud)
            | 64 : sustain
            | 91 : reverb
            | 93 : chorus
        
        :param chan: The channel to use for audio playback.
        :param ctrl: The control to modify, examples provided above.
        :param val: The new value for the control. Always ranges 0 to 127.
        """
        super().cc(chan, ctrl, val)