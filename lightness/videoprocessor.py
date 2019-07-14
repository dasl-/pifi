import numpy as np
import pprint
import time
import os
import time
import sys
import urllib
import re
from lightness.logger import Logger
from lightness.process import Process
from lightness.readoncecircularbuffer import ReadOnceCircularBuffer
from lightness.videosettings import VideoSettings
import youtube_dl
import subprocess
import math
import shlex
import tempfile
import hashlib
import select

class VideoProcessor:

    __video_settings = None
    __logger = None
    __process = None
    __url = None

    # True if the video already exists (see: VideoSettings.should_save_video)
    __is_video_already_downloaded = False

    # Metadata about the video we are using, such as title, resolution, file extension, etc
    # Note this is only populated if the video didn't already exist (see: VideoSettings.should_save_video)
    # Access should go through self.__get_video_info() to populate it lazily
    __video_info = None

    __DATA_DIRECTORY = 'data'

    __YOUTUBE_DL_FORMAT = 'worst[ext=mp4]/worst' # mp4 scales quicker than webm in ffmpeg scaling
    __YOUTUBE_DL_BUFFER_SIZE_BYTES = 1024 * 1024 * 10 # 10 megabytes
    __DEFAULT_VIDEO_EXTENSION = '.mp4'
    __TEMP_VIDEO_DOWNLOAD_SUFFIX = '.dl_part'

    __FFMPEG_TO_PYTHON_FIFO_PREFIX = 'lightness_ffmpeg_to_python_fifo__'

    __FRAMES_BUFFER_LENGTH = 1024

    def __init__(self, video_settings, process=None):
        self.__video_settings = video_settings
        self.__process = process
        self.__logger = Logger().set_namespace(self.__class__.__name__)
        if self.__video_settings.log_file != VideoSettings.LOG_FILE_TERMINAL:
            self.__logger.set_log_files(self.__video_settings.log_file, self.__video_settings.log_file)

    def process_and_play(self, url, video_player):
        self.__logger.info("Starting process_and_play for url: {}".format(url))
        self.__show_loading_screen(video_player)
        self.__url = url
        video_save_path = self.__get_video_save_path()
        if os.path.isfile(video_save_path):
            self.__logger.info('Video has already been downloaded. Using saved video: {}'.format(video_save_path))
            self.__is_video_already_downloaded = True

        self.__process_and_play_video(video_player)
        self.__logger.info("Finished process_and_play")

    def __show_loading_screen(self, video_player):
        filename = 'loading_screen_monochrome.npy'
        if self.__video_settings.color_mode == VideoSettings.COLOR_MODE_COLOR:
            filename = 'loading_screen_color.npy'
        loading_screen_path = os.path.abspath(os.path.dirname(__file__)) + '/../{}'.format(filename)
        video_player.playFrame(np.load(loading_screen_path))

    # Lazily populate video_info from youtube. This takes a couple seconds.
    def __get_video_info(self):
        if self.__is_video_already_downloaded:
            raise Exception('We should avoid populating video metadata from youtube if the video already ' +
                'exists for performance reasons and to have an offline mode for saved video files.')

        if self.__video_info:
            return self.__video_info

        self.__logger.info("Downloading and populating video metadata...")
        ydl_opts = {
            'format': self.__YOUTUBE_DL_FORMAT,
            'logger': Logger(),
            'restrictfilenames': True, # get rid of a warning ytdl gives about special chars in file names
        }
        ydl = youtube_dl.YoutubeDL(ydl_opts)
        self.__video_info = ydl.extract_info(self.__url, download = False)
        self.__logger.info("Done downloading and populating video metadata.")

        video_type = 'video_only'
        if self.__video_info['acodec'] != 'none':
            video_type = 'video+audio'
        self.__logger.info("Using: " + video_type + ":" + self.__video_info['ext'] + "@" +
            str(self.__video_info['width']) + "x" + str(self.__video_info['height']))

        return self.__video_info

    def __get_video_save_path(self):
        return (
            self.__get_data_directory() + '/' +
            hashlib.md5(self.__url.encode('utf-8')).hexdigest() + self.__DEFAULT_VIDEO_EXTENSION
        )

    def __get_data_directory(self):
        save_dir = os.path.abspath(os.path.dirname(__file__) + '/../' + self.__DATA_DIRECTORY)
        os.makedirs(save_dir, exist_ok=True)
        return save_dir

    def __process_and_play_video(self, video_player):
        self.__do_pre_cleanup()

        fps = self.__calculate_fps()
        ffmpeg_to_python_fifo_name = self.__make_ffmpeg_to_python_fifo()
        self.__maybe_set_volume()

        process_and_play_vid_cmd = self.__get_process_and_play_vid_cmd(ffmpeg_to_python_fifo_name)
        self.__logger.info('executing process and play cmd: ' + process_and_play_vid_cmd)
        process_and_play_vid_proc = subprocess.Popen(process_and_play_vid_cmd, shell = True, executable = '/bin/bash')

        self.__process.set_status(Process.STATUS_PLAYING)

        bytes_per_frame = self.__video_settings.display_width * self.__video_settings.display_height
        np_array_shape = [self.__video_settings.display_height, self.__video_settings.display_width]
        if self.__video_settings.color_mode == VideoSettings.COLOR_MODE_COLOR:
            bytes_per_frame = bytes_per_frame * 3
            np_array_shape.append(3)

        start_time = None
        frame_length =  1 / fps
        last_frame = None
        is_ffmpeg_done_outputting = False
        avg_color_frames = ReadOnceCircularBuffer(self.__FRAMES_BUFFER_LENGTH)
        ffmpeg_to_python_fifo = open(ffmpeg_to_python_fifo_name, 'rb')
        while True:
            if is_ffmpeg_done_outputting or avg_color_frames.is_full():
                pass
            else:
                is_ffmpeg_done_outputting, start_time = self.__populate_avg_color_frames(
                    avg_color_frames, ffmpeg_to_python_fifo, start_time, bytes_per_frame, np_array_shape
                )

            if not start_time:
                # video has not started being processed yet
                pass
            else:
                is_video_done_playing, last_frame = self.__play_video(
                    video_player, avg_color_frames, start_time, frame_length, is_ffmpeg_done_outputting, last_frame
                )
                if is_video_done_playing:
                    break

        self.__do_post_cleanup(process_and_play_vid_proc)

    def __populate_avg_color_frames(self, avg_color_frames, ffmpeg_to_python_fifo, start_time, bytes_per_frame, np_array_shape):
        is_ready_to_read, ignore1, ignore2 = select.select([ffmpeg_to_python_fifo], [], [], 0)
        if not is_ready_to_read:
            return [False, start_time]

        ffmpeg_output = ffmpeg_to_python_fifo.read(bytes_per_frame)
        if ffmpeg_output and len(ffmpeg_output) < bytes_per_frame:
            raise Exception('Expected {} bytes from ffmpeg output, but got {}.'.format(bytes_per_frame, len(ffmpeg_output)))
        if not ffmpeg_output:
            self.__logger.info("no ffmpeg_output, end of video processing.")
            return [True, start_time]

        if not start_time:
            # Start the video clock as soon as we see ffmpeg output. Ffplay probably sent its
            # first audio data at around the same time so they stay in sync.
            # Add time for better audio / video sync
            start_time = time.time() + (0.15 if self.__video_settings.should_play_audio else 0)

        avg_color_frames.append(
            np.frombuffer(ffmpeg_output, np.uint8).reshape(np_array_shape)
        )
        return [False, start_time]

    def __play_video(self, video_player, avg_color_frames, start_time, frame_length, is_ffmpeg_done_outputting, last_frame):
        cur_frame = max(math.floor((time.time() - start_time) / frame_length), 0)
        if cur_frame >= len(avg_color_frames):
            if is_ffmpeg_done_outputting:
                self.__logger.info("Video done playing.")
                return [True, cur_frame]
            else:
                self.__logger.error("Video processing unable to keep up in real-time")
                cur_frame = len(avg_color_frames) - 1 # play the most recent frame we have

        if cur_frame == last_frame:
            # Don't need to play a frame since we're still supposed to be playing the last frame we played
            return [False, cur_frame]

        # Play the new frame
        num_skipped_frames = 0
        if last_frame == None:
            if cur_frame != 0:
                num_skipped_frames = cur_frame
        elif cur_frame - last_frame > 1:
            num_skipped_frames = cur_frame - last_frame - 1
        if num_skipped_frames > 0:
            self.__logger.error(
                ("Video playing unable to keep up in real-time. Skipped playing {} frame(s)."
                    .format(num_skipped_frames))
            )
        video_player.playFrame(avg_color_frames[cur_frame])
        return [False, cur_frame]

    def __get_process_and_play_vid_cmd(self, ffmpeg_to_python_fifo_name):
        video_save_path = self.__get_video_save_path()
        vid_data_cmd = None
        if self.__is_video_already_downloaded:
            vid_data_cmd = '< {} '.format(shlex.quote(video_save_path))
        else:
            vid_data_cmd = (
                # Add a buffer to give some slack in the case of network blips downloading the video.
                # Not necessary in my testing, but then again I have a good connection...
                # Set HOME variable to prevent these logs when run via sudo:
                #   mbuffer: warning: HOME environment variable not set - unable to find defaults file
                self.__get_youtube_dl_cmd() + ' | ' +
                'HOME=/home/pi mbuffer -q -Q -m ' + shlex.quote(str(self.__YOUTUBE_DL_BUFFER_SIZE_BYTES) + 'b') + ' | '
            )

        maybe_play_audio_tee = ''
        if self.__video_settings.should_play_audio:
            maybe_play_audio_tee = ">(" + self.__get_ffplay_cmd() + ") "

        maybe_save_video_tee = ''
        maybe_mv_saved_video_cmd = ''
        if self.__video_settings.should_save_video and not self.__is_video_already_downloaded:
            self.__logger.info('Video will be saved to: {}'.format(video_save_path))
            temp_video_save_path = video_save_path + self.__TEMP_VIDEO_DOWNLOAD_SUFFIX
            maybe_save_video_tee = shlex.quote(temp_video_save_path) + ' '
            maybe_mv_saved_video_cmd = '&& mv ' + shlex.quote(temp_video_save_path) + ' ' + shlex.quote(video_save_path)

        process_and_play_vid_cmd = (
            'set -o pipefail && ' +
            vid_data_cmd + "tee " +
            maybe_play_audio_tee +
            ">(" + self.__get_ffmpeg_cmd() + " > " + ffmpeg_to_python_fifo_name + ") " +
            maybe_save_video_tee +
            "> /dev/null " +
            maybe_mv_saved_video_cmd
        )
        return process_and_play_vid_cmd

    def __get_youtube_dl_cmd(self):
        video_info = self.__get_video_info()
        if self.__video_settings.log_level == VideoSettings.LOG_LEVEL_VERBOSE:
            log_level = ''
        elif self.__video_settings.log_level == VideoSettings.LOG_LEVEL_NORMAL:
            log_level = '--no-progress '
        log_opts = ''
        if not sys.stderr.isatty():
            log_opts = '--newline '
        return (
            'youtube-dl ' +
            '--output - ' + # output to stdout
            '--restrict-filenames ' + # get rid of a warning ytdl gives about special chars in file names
            '--format ' + shlex.quote(video_info['format_id']) + " " + # download the specified video quality / encoding
            log_level +
            log_opts +
            shlex.quote(video_info['webpage_url']) # url to download
        )

    def __get_ffmpeg_cmd(self):
        pix_fmt = 'gray'
        if self.__video_settings.color_mode == VideoSettings.COLOR_MODE_COLOR:
            pix_fmt = 'rgb24'

        # unfortunately there's no way to make ffmpeg output its stats progress stuff with line breaks
        log_opts = ''
        if sys.stderr.isatty():
            log_opts = '-stats '

        return (
            'ffmpeg ' +
            '-threads 1 ' + # using one thread is plenty fast and is probably better to avoid tying up CPUs for displaying LEDs
            '-i pipe:0 ' + # read input video from stdin
            '-filter:v ' + shlex.quote( # resize video
                'scale=' + str(self.__video_settings.display_width) + 'x' + str(self.__video_settings.display_height)) + " "
            '-c:a copy ' + # don't process the audio at all
            '-f rawvideo -pix_fmt ' + shlex.quote(pix_fmt) + " " # output in numpy compatible byte format
            '-v quiet ' + # supress output of verbose ffmpeg configuration, etc
            log_opts + # maybe display progress stats
            'pipe:1' # output to stdout
        )

    def __get_ffplay_cmd(self):
        return (
            "ffplay " +
            "-nodisp " + # Disable graphical display.
            "-vn " + # Disable video
            "-autoexit " + # Exit when video is done playing
            "-i pipe:0 " + # play input from stdin
            "-v quiet" # supress verbose ffplay output
        )

    # Fps is available in self.__video_info metadata obtained via youtube-dl, but it is less accurate than using ffprobe.
    def __calculate_fps(self):
        self.__logger.info("Calculating video fps...")
        video_path = ''
        if self.__is_video_already_downloaded:
            video_path = self.__get_video_save_path()
        else:
            video_path = self.__get_video_info()['url']

        fps_parts = (subprocess
            .check_output(('ffprobe', '-v', '0', '-of', 'csv=p=0', '-select_streams', 'v:0', '-show_entries',
                'stream=r_frame_rate', video_path))
            .decode("utf-8"))
        fps_parts = fps_parts.split('/')
        fps = float(fps_parts[0]) / float(fps_parts[1])
        self.__logger.info('Calculated video fps: ' + str(fps))
        return fps

    def __maybe_set_volume(self):
        if self.__video_settings.should_play_audio:
            self.__logger.info('Setting volume to 100%...')
            subprocess.check_output(('amixer', 'cset', 'numid=1', '100%'))

    def __make_ffmpeg_to_python_fifo(self):
        make_fifo_cmd = (
            'fifo_name=$(mktemp --tmpdir={} --dry-run {}) && mkfifo -m 600 "$fifo_name" && printf $fifo_name'
                .format(
                    tempfile.gettempdir(),
                    self.__FFMPEG_TO_PYTHON_FIFO_PREFIX + 'XXXXXXXXXX'
                )
        )
        self.__logger.info('Making ffmpeg_to_python_fifo...')
        ffmpeg_to_python_fifo_name = (subprocess
            .check_output(make_fifo_cmd, shell = True, executable = '/bin/bash')
            .decode("utf-8"))
        return ffmpeg_to_python_fifo_name

    def __get_cleanup_ffmpeg_to_python_fifos_cmd(self):
        path_glob = shlex.quote(tempfile.gettempdir() + "/" + self.__FFMPEG_TO_PYTHON_FIFO_PREFIX) + '*'
        return 'sudo rm -rf {}'.format(path_glob)

    def __get_cleanup_incomplete_video_downloads_cmd(self):
        return 'sudo rm -rf *{}'.format(shlex.quote(self.__TEMP_VIDEO_DOWNLOAD_SUFFIX))

    # Perhaps aggressive to do 'pre' cleanup, but wanting to be a good citizen. Protects against a hypothetical
    # where we're stuck in a state of failing to finish playing videos and thus post cleanup logic never gets
    # run.
    def __do_pre_cleanup(self):
        self.__logger.info("Deleting orphaned ffmpeg_to_python_fifos...")
        subprocess.check_output(self.__get_cleanup_ffmpeg_to_python_fifos_cmd(), shell = True, executable = '/bin/bash')
        self.__logger.info("Deleting orphaned incomplete video downloads...")
        subprocess.check_output(self.__get_cleanup_incomplete_video_downloads_cmd(), shell = True, executable = '/bin/bash')

    def __do_post_cleanup(self, process_and_play_vid_proc):
        self.__logger.info("Waiting for process_and_play_vid_proc to end...")
        exit_status = process_and_play_vid_proc.wait()
        if exit_status != 0:
            self.__logger.error('Got non-zero exit_status for process_and_play_vid_proc: {}'.format(exit_status))

        self.__logger.info("Deleting ffmpeg_to_python fifos...")
        subprocess.check_output(self.__get_cleanup_ffmpeg_to_python_fifos_cmd(), shell = True, executable = '/bin/bash')

        self.__logger.info("Deleting incomplete video downloads...")
        subprocess.check_output(self.__get_cleanup_incomplete_video_downloads_cmd(), shell = True, executable = '/bin/bash')
