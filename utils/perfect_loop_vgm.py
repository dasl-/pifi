#!/usr/bin/python3

import argparse, sys, os, subprocess, shlex, time
from pygame import mixer

# This is necessary for the import below to work
root_dir = os.path.abspath(os.path.dirname(__file__) + '/..')
sys.path.append(root_dir)
from pifi.directoryutils import DirectoryUtils

def parseArgs():
    parser = argparse.ArgumentParser(description="""
        Util to trim a vgm to a perfect loop.
        See: https://vgmrips.net/wiki/VGM_File_Format
    """)
    parser.add_argument('--input-file', dest='input_file', action='store', required = True,
        help='*.vgm input file')
    parser.add_argument('--output-file', dest='output_file', action='store', required = True,
        help='*.wav output file')

    args = parser.parse_args()
    return args

args = parseArgs()
input_file = args.input_file
output_file = args.output_file
SAMPLE_RATE = 44100
print('')
"""
0x18    32 bits     Total # samples
0x1C    32 bits     Loop offset
0x20    32 bits     Loop # samples
"""
f = open(input_file, "rb")

f.seek(24);
total_num_samples = int.from_bytes(f.read(4), byteorder=sys.byteorder)
print('total num samples: {} ({} sec)'.format(total_num_samples, round(total_num_samples / SAMPLE_RATE, 2)));

f.seek(32);
loop_num_samples = int.from_bytes(f.read(4), byteorder=sys.byteorder)
print('loop num samples: {} ({} sec)'.format(loop_num_samples, round(loop_num_samples / SAMPLE_RATE, 2)));

# not sure if i should be modifying offsets based on this value? hopefully it is small and unnoticeable in most cases...
f.seek(28);
loop_offset = int.from_bytes(f.read(4), byteorder=sys.byteorder)
print('loop offset: {} ({} sec)'.format(loop_offset, round(loop_offset / SAMPLE_RATE, 2)));
print('')
f.close()

"""
https://github.com/vgmrips/vgmtools
built via: `make all`

VGM Trimmer
-----------

Usage: vgm_trim [-state] [-nonotewarn] File.vgm
                StartSmpl LoopSmpl EndSmpl [OutFile.vgm]

Options:
    -state: put a save state of the chips at the start of the VGM
    -NoNoteWarn: don't print warnings about notes playing at EOF
"""
print("trimming vgm...")
vgm_trim_output = (subprocess
    .check_output(
        DirectoryUtils().root_dir + '/utils/vgm_trim ' + shlex.quote(input_file) + ' 0 0 ' + str(loop_num_samples) + ' tmp_perfect_loop.vgm',
        shell = True,
        executable = '/bin/bash',
        stderr = subprocess.STDOUT
    )
    .decode("utf-8"))
print(vgm_trim_output)

"""
https://github.com/vgmrips/vgmplay
built via: `cd VGMPlay ; make install DISABLE_HWOPL_SUPPORT=1 USE_DBUS=0 USE_LIBAO=0`

usage: vgm2wav [options] vgm_file wav_file
wav_file can be - for standard output.

Options:
--loop-count {number}
--fade-ms {number}
--no-smpl-chunk
"""
print("converting vgm to wav ({})...".format(output_file))
vgm2wav_output = (subprocess
    .check_output(
        DirectoryUtils().root_dir + '/utils/vgm2wav --loop-count 1 tmp_perfect_loop.vgm ' + shlex.quote(output_file),
        shell = True,
        executable = '/bin/bash',
        stderr = subprocess.STDOUT
    )
    .decode("utf-8"))
print(vgm2wav_output)

os.remove('tmp_perfect_loop.vgm')

print("Success! Playing perfect loop on repeat. Press ctrl + c to exit...")
mixer.init(frequency = 22050, buffer = 512)

loop_test = mixer.Sound(output_file)
print("Loop length: " + str(round(loop_test.get_length(),2)) + ' seconds')
loop_test.play(loops = -1)
time.sleep(100000)
