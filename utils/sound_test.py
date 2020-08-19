#!/usr/bin/python3

# We've observed that pygame audio has a slight lag when playing. Run this script and you'll notice a
# very slight delay in the synchronization of the sound effects. This delay was bad enough that for
# real-time sound effects (i.e. not background music), we use simpleaudio to play the sound effect in
# real time.
#
# We use pygame to play background audio.
#
# Simpleaudio is good because it is real time. It is bad because it doesnt offer advanced controls.
# All you can do is start and stop sounds. You can't change their volume nor loop them.
#
# Pygame audio is good because it has advanced controls. You can change their volume or loop them.
# Pygame audio is bad because it has a slight lag in playing the audio.
#
# To get around simpleaudio's lack of volume controls, we use ffmpeg to change the volume of
# the source audio file if necessary:
#
#   ffmpeg -i input.wav -filter:a "volume=0.5" output_50_pct_vol.wav
#
# We keep the source file (input.wav) around in case we need to adjust it more in the future --
# better to have the original file.
import time
import simpleaudio
from pygame import mixer
import os
import sys

# This is necessary for the import below to work
root_dir = os.path.abspath(os.path.dirname(__file__) + '/..')
sys.path.append(root_dir)
from pifi.directoryutils import DirectoryUtils

# FREQUENCY:
#
#   setting frequency to 22050 rather than 44100 seems to reduce the likelihood of audio stutters / dropouts:
#
#     Aug 19 05:17:51 pifi PIFI_QUEUE[31591]: ALSA lib pcm.c:8424:(snd_pcm_recover) underrun occurred
#
#   They didn't happen super often, but after playing some background music for a while, they would sometimes happen
#
# BUFFER:
#
#  setting buffer to 512 was found to be a good compromise between likelihood of audio stutters / dropouts
#  and not having audio lag in playing realtime sounds. See: https://www.pygame.org/docs/ref/mixer.html#pygame.mixer.init
#
#  Setting to 256, and we'd see dropouts sometimes. Setting to 1024, and the lag was way too noticeable
mixer.init(frequency = 22050, buffer = 512)

apple_sound_slow = mixer.Sound(DirectoryUtils().root_dir + "/assets/snake/sfx_coin_double7.wav")
apple_sound_fast = simpleaudio.WaveObject.from_wave_file(DirectoryUtils().root_dir + "/assets/snake/sfx_coin_double7.wav")
background_music = mixer.Sound(DirectoryUtils().root_dir + "/assets/snake/04 Solitary Warrior.wav")
background_music.play(loops = -1)

while True:
    apple_sound_fast.play()
    apple_sound_slow.play()
    time.sleep(1)
