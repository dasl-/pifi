import numpy as np
import time
import os
import sys
import youtube_dl
import subprocess
import math
import shlex
import tempfile
import hashlib
import select
import signal
import traceback

from pifi.logger import Logger
from pifi.datastructure.readoncecircularbuffer import ReadOnceCircularBuffer
from pifi.directoryutils import DirectoryUtils
from pifi.youtubedlexception import YoutubeDlException

class VideoProcessor:

    __DATA_DIRECTORY = 'data'

    __YOUTUBE_DL_FORMAT = 'worst[ext=mp4]/worst' # mp4 scales quicker than webm in ffmpeg scaling
    __DEFAULT_VIDEO_EXTENSION = '.mp4'
    __TEMP_VIDEO_DOWNLOAD_SUFFIX = '.dl_part'

    __FFMPEG_TO_PYTHON_FIFO_PREFIX = 'pifi_ffmpeg_to_python_fifo__'

    __FRAMES_BUFFER_LENGTH = 1024

    def __init__(self, url, video_settings, video_player):
        self.__logger = Logger().set_namespace(self.__class__.__name__)
        self.__url = url
        self.__video_settings = video_settings
        self.__video_player = video_player
        self.__process_and_play_vid_proc_pgid = None

        # Metadata about the video we are using, such as title, resolution, file extension, etc
        # Note this is only populated if the video didn't already exist (see: VideoSettings.should_save_video)
        # Access should go through self.__get_video_info() to populate it lazily
        self.__video_info = None

        # True if the video already exists (see: VideoSettings.should_save_video)
        self.__is_video_already_downloaded = False
        self.__do_housekeeping()
        self.__register_signal_handlers()

    def process_and_play(self):
        self.__logger.info(f"Starting process_and_play for url: {self.__url}, VideoSettings: " +
            f"{vars(self.__video_settings)}")
        self.__show_loading_screen()
        video_save_path = self.__get_video_save_path()

        if os.path.isfile(video_save_path):
            self.__logger.info('Video has already been downloaded. Using saved video: {}'.format(video_save_path))
            self.__is_video_already_downloaded = True
        elif self.__video_settings.should_predownload_video:
            download_command = self.__download_youtube_video()
            self.__logger.info('Downloading video: {}'.format(download_command))
            subprocess.call(download_command, shell=True)
            self.__logger.info('Video download complete: {}'.format(video_save_path))
            self.__is_video_already_downloaded = True

        attempt = 1
        max_attempts = 2
        while attempt <= max_attempts:
            try:
                self.__process_and_play_video()
                break
            except YoutubeDlException as e:
                if attempt < max_attempts:
                    self.__logger.warning("Caught exception in VideoProcessor.__process_and_play_video: " +
                        traceback.format_exc())
                    self.__logger.warning("Updating youtube-dl and retrying video...")
                    self.__update_youtube_dl()
                if attempt >= max_attempts:
                    raise e
            finally:
                self.__do_housekeeping()
            attempt += 1
        self.__logger.info("Finished process_and_play")

    def __show_loading_screen(self):
        filename = 'loading_screen_monochrome.npy'
        if self.__video_settings.is_color_mode_rgb():
            filename = 'loading_screen_color.npy'
        loading_screen_path = DirectoryUtils().root_dir + '/' + filename
        self.__video_player.play_frame(np.load(loading_screen_path))

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

        # Automatically try to update youtube-dl and retry failed youtube-dl operations when we get a youtube-dl
        # error.
        #
        # The youtube-dl package needs updating periodically when youtube make updates. This is
        # handled on a cron once a day: https://github.com/dasl-/pifi/blob/a614b33e1be093f6ee3bb62b036ee6472ffe5132/install/pifi_cron.sh#L5
        #
        # But we also attempt to update it on the fly here if we get youtube-dl errors when trying to play
        # a video.
        #
        # Example of how this would look in logs: https://gist.github.com/dasl-/09014dca55a2e31bb7d27f1398fd8155
        max_attempts = 2
        for attempt in range(1, (max_attempts + 1)):
            try:
                self.__video_info = ydl.extract_info(self.__url, download = False)
            except Exception as e:
                caught_or_raising = "Raising"
                if attempt < max_attempts:
                    caught_or_raising = "Caught"
                self.__logger.warning("Problem downloading video info during attempt {} of {}. {} exception: {}"
                    .format(attempt, max_attempts, caught_or_raising, traceback.format_exc()))
                if attempt < max_attempts:
                    self.__logger.warning("Attempting to update youtube-dl before retrying download...")
                    self.__update_youtube_dl()
                else:
                    self.__logger.error("Unable to download video info after {} attempts.".format(max_attempts))
                    raise e

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
        save_dir = DirectoryUtils().root_dir + '/' + self.__DATA_DIRECTORY
        os.makedirs(save_dir, exist_ok=True)
        return save_dir

    def __process_and_play_video(self):
        fps = self.__calculate_fps()
        ffmpeg_to_python_fifo_name = self.__make_ffmpeg_to_python_fifo()

        process_and_play_vid_cmd = self.__get_process_and_play_vid_cmd(ffmpeg_to_python_fifo_name)
        self.__logger.info('executing process and play cmd: ' + process_and_play_vid_cmd)
        process_and_play_vid_proc = subprocess.Popen(
            process_and_play_vid_cmd, shell = True, executable = '/usr/bin/bash', start_new_session = True
        )
        # Store the PGID separately, because attempting to get the PGID later via `os.getpgid` can
        # raise `ProcessLookupError: [Errno 3] No such process` if the process is no longer running
        self.__process_and_play_vid_proc_pgid = os.getpgid(process_and_play_vid_proc.pid)

        bytes_per_frame = self.__video_settings.display_width * self.__video_settings.display_height
        np_array_shape = [self.__video_settings.display_height, self.__video_settings.display_width]
        if self.__video_settings.is_color_mode_rgb():
            bytes_per_frame = bytes_per_frame * 3
            np_array_shape.append(3)

        vid_start_time = None
        frame_length = 1 / fps
        last_frame = None
        vid_processing_lag_counter = 0
        is_ffmpeg_done_outputting = False
        avg_color_frames = ReadOnceCircularBuffer(self.__FRAMES_BUFFER_LENGTH)
        ffmpeg_to_python_fifo = open(ffmpeg_to_python_fifo_name, 'rb')
        while True:
            if is_ffmpeg_done_outputting or avg_color_frames.is_full():
                pass
            else:
                is_ffmpeg_done_outputting, vid_start_time = self.__populate_avg_color_frames(
                    avg_color_frames, ffmpeg_to_python_fifo, vid_start_time, bytes_per_frame, np_array_shape
                )

            if vid_start_time is None:
                # video has not started being processed yet
                pass
            else:
                is_video_done_playing, last_frame, vid_processing_lag_counter = self.__play_video(
                    avg_color_frames, vid_start_time, frame_length, is_ffmpeg_done_outputting,
                    last_frame, vid_processing_lag_counter
                )
                if is_video_done_playing:
                    break

        self.__logger.info("Waiting for process_and_play_vid_proc to end...")
        while True: # Wait for proc to end
            if process_and_play_vid_proc.poll() is not None:
                if process_and_play_vid_proc.returncode != 0:
                    raise YoutubeDlException("The process_and_play_vid_proc process exited non-zero: " +
                        f"{process_and_play_vid_proc.returncode}. This could mean an issue with youtube-dl; " +
                        "it may require updating.")
                self.__logger.info("The process_and_play_vid_proc proc ended.")
                break
            time.sleep(0.1)

    def __download_youtube_video(self):
        return (
            'yt-dlp ' +
            '--output \'' + shlex.quote(self.__get_video_save_path()) + "' "
            '--restrict-filenames ' + # get rid of a warning ytdl gives about special chars in file names
            '--format ' + shlex.quote(self.__YOUTUBE_DL_FORMAT) + " " + # download the specified video quality / encoding
            '--retries infinite ' + # in case downloading has transient errors
            shlex.quote(self.__url) # url to download
        )

    def __populate_avg_color_frames(
        self, avg_color_frames, ffmpeg_to_python_fifo, vid_start_time, bytes_per_frame, np_array_shape
    ):
        is_ready_to_read, ignore1, ignore2 = select.select([ffmpeg_to_python_fifo], [], [], 0)
        if not is_ready_to_read:
            return [False, vid_start_time]

        ffmpeg_output = ffmpeg_to_python_fifo.read(bytes_per_frame)
        if ffmpeg_output and len(ffmpeg_output) < bytes_per_frame:
            raise Exception('Expected {} bytes from ffmpeg output, but got {}.'.format(bytes_per_frame, len(ffmpeg_output)))
        if not ffmpeg_output:
            self.__logger.info("no ffmpeg_output, end of video processing.")
            if vid_start_time is None:
                # under rare circumstances, youtube-dl might fail and we end up in this code path.
                self.__logger.error("No vid_start_time set. Possible yt-dl crash. See: https://github.com/ytdl-org/youtube-dl/issues/24780")
                vid_start_time = 0 # set this so that __process_and_play_video doesn't endlessly loop
            return [True, vid_start_time]

        if vid_start_time is None:
            # Start the video clock as soon as we see ffmpeg output. Ffplay probably sent its
            # first audio data at around the same time so they stay in sync.
            # Add time for better audio / video sync
            vid_start_time = time.time() + (0.15 if self.__video_settings.should_play_audio else 0)

        avg_color_frames.append(
            np.frombuffer(ffmpeg_output, np.uint8).reshape(np_array_shape)
        )
        return [False, vid_start_time]

    def __play_video(
        self, avg_color_frames, vid_start_time, frame_length, is_ffmpeg_done_outputting,
        last_frame, vid_processing_lag_counter
    ):
        cur_frame = max(math.floor((time.time() - vid_start_time) / frame_length), 0)
        if cur_frame >= len(avg_color_frames):
            if is_ffmpeg_done_outputting:
                self.__logger.info("Video done playing. Video processing lag counter: {}.".format(vid_processing_lag_counter))
                return [True, cur_frame, vid_processing_lag_counter]
            else:
                vid_processing_lag_counter += 1
                if vid_processing_lag_counter % 1000 == 0 or vid_processing_lag_counter == 1:
                    self.__logger.error(
                        f"Video processing is lagging. Counter: {vid_processing_lag_counter}. " +
                        f"Frames available: {avg_color_frames.unread_length()}."
                    )
                cur_frame = len(avg_color_frames) - 1 # play the most recent frame we have

        if cur_frame == last_frame:
            # We don't need to play a frame since we're still supposed to be playing the last frame we played
            return [False, cur_frame, vid_processing_lag_counter]

        # Play the new frame
        num_skipped_frames = 0
        if last_frame is None:
            if cur_frame != 0:
                num_skipped_frames = cur_frame
        elif cur_frame - last_frame > 1:
            num_skipped_frames = cur_frame - last_frame - 1
        if num_skipped_frames > 0:
            self.__logger.error(
                ("Video playing unable to keep up in real-time. Skipped playing {} frame(s)."
                    .format(num_skipped_frames))
            )
        self.__video_player.play_frame(avg_color_frames[cur_frame])
        return [False, cur_frame, vid_processing_lag_counter]

    def __get_process_and_play_vid_cmd(self, ffmpeg_to_python_fifo_name):
        video_save_path = self.__get_video_save_path()
        vid_data_cmd = None
        if self.__is_video_already_downloaded:
            vid_data_cmd = '< {} '.format(shlex.quote(video_save_path))
        else:
            vid_data_cmd = (
                # Add mbuffer to give some slack in the case of network blips downloading the video.
                self.__get_youtube_dl_cmd() + ' | ' +
                self.__get_mbuffer_cmd(1024 * 1024 * 10, '/tmp/mbuffer-ytdl.out') + ' | '
            )

        maybe_play_audio_tee = ''
        if self.__video_settings.should_play_audio:
            # Add mbuffer because otherwise the ffplay command blocks the whole pipeline. Because
            # audio can only play in real-time, this would block ffmpeg from processing the frames
            # as fast as it otherwise could. This prevents us from building up a big enough buffer
            # in the avg_color_frames circular buffer to withstand blips in performance. This
            # ensures the circular buffer will generally get filled, rather than lingering around
            # only ~70 frames full. Makes it less likely that we will fall behind in video
            # processing.
            maybe_play_audio_tee = (">(" +
                self.__get_mbuffer_cmd(1024 * 1024 * 10, '/tmp/mbuffer-ffplay.out') + ' | ' +
                self.__get_ffplay_cmd() +
                ") ")

        ffmpeg_tee = f'>( {self.__get_ffmpeg_cmd()} > {ffmpeg_to_python_fifo_name}) '

        maybe_save_video_tee = ''
        maybe_mv_saved_video_cmd = ''
        if self.__video_settings.should_save_video and not self.__is_video_already_downloaded:
            self.__logger.info('Video will be saved to: {}'.format(video_save_path))
            temp_video_save_path = video_save_path + self.__TEMP_VIDEO_DOWNLOAD_SUFFIX
            maybe_save_video_tee = shlex.quote(temp_video_save_path) + ' '
            maybe_mv_saved_video_cmd = '&& mv ' + shlex.quote(temp_video_save_path) + ' ' + shlex.quote(video_save_path)

        process_and_play_vid_cmd = (
            'set -o pipefail && export SHELLOPTS && ' +
            vid_data_cmd + "tee " +
            maybe_play_audio_tee +
            ffmpeg_tee +
            maybe_save_video_tee +
            "> /dev/null " +
            maybe_mv_saved_video_cmd
        )
        return process_and_play_vid_cmd

    def __get_youtube_dl_cmd(self):
        log_opts = '--no-progress '
        if Logger.get_level() <= Logger.DEBUG:
            log_opts = ' ' # show video download progress
        if not sys.stderr.isatty():
            log_opts += '--newline '
        return (
            'yt-dlp ' +
            '--output - ' + # output to stdout
            '--restrict-filenames ' + # get rid of a warning ytdl gives about special chars in file names
            '--format ' + shlex.quote(self.__YOUTUBE_DL_FORMAT) + " " + # download the specified video quality / encoding
            '--retries infinite ' + # in case downloading has transient errors
            log_opts +
            shlex.quote(self.__url) # url to download
        )

    def __get_ffmpeg_cmd(self):
        pix_fmt = 'gray'
        if self.__video_settings.is_color_mode_rgb():
            pix_fmt = 'rgb24'

        # unfortunately there's no way to make ffmpeg output its stats progress stuff with line breaks
        log_opts = ''
        if sys.stderr.isatty():
            log_opts = '-stats '

        # Note: don't use ffmpeg's `-xerror` flag:
        # https://gist.github.com/dasl-/1ad012f55f33f14b44393960f66c6b00
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

    def __get_mbuffer_cmd(self, buffer_size_bytes, log_file = None):
        log_file_clause = ' -Q '
        if log_file:
            log_file_clause = f' -l {log_file} '
        return f'mbuffer -q {log_file_clause} -m ' + shlex.quote(str(buffer_size_bytes)) + 'b'

    # Fps is available in self.__video_info metadata obtained via youtube-dl, but it is less accurate than using ffprobe.
    def __calculate_fps(self):
        self.__logger.info("Calculating video fps...")
        video_path = ''
        if self.__is_video_already_downloaded:
            video_path = shlex.quote(self.__get_video_save_path())
        else:
            video_path = f'<({self.__get_youtube_dl_cmd()} 2>/dev/null)'

        fps_cmd = f'ffprobe -v 0 -of csv=p=0 -select_streams v:0 -show_entries stream=r_frame_rate {video_path}'
        try:
            fps_parts = (subprocess
                .check_output(fps_cmd, shell = True, executable = '/usr/bin/bash')
                .decode("utf-8"))
        except subprocess.CalledProcessError as ex:
            if self.__is_video_already_downloaded:
                raise ex
            else:
                raise YoutubeDlException("The fps calculation process exited non-zero: " +
                    f"{ex.returncode}. Output: [{ex.output}]. This could mean an issue with youtube-dl; " +
                    "it may require updating.")

        fps_parts = fps_parts.split('/')
        fps = None
        try:
            # "Live" streams on youtube may fail here with an error:
            #   could not convert string to float: '1\n\n15'
            fps = float(fps_parts[0]) / float(fps_parts[1])
        except ValueError as ex:
            self.__logger.error("Got an error dividing fps parts: " + str(ex))
            video_info = self.__get_video_info()
            if video_info['fps'] is not None:
                self.__logger.error("Using fps approximation from video_info['fps']: " + str(video_info['fps']) + " fps.")
                fps = float(video_info['fps'])
            else:
                self.__logger.error("Assuming 30 fps for this video.")
                fps = 30

        self.__logger.info('Calculated video fps: ' + str(fps))
        return fps

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
            .check_output(make_fifo_cmd, shell = True, executable = '/usr/bin/bash')
            .decode("utf-8"))
        return ffmpeg_to_python_fifo_name

    def __update_youtube_dl(self):
        update_youtube_dl_output = (subprocess
            .check_output(
                'sudo ' + DirectoryUtils().root_dir + '/utils/update_youtube-dl.sh',
                shell = True,
                executable = '/usr/bin/bash',
                stderr = subprocess.STDOUT
            )
            .decode("utf-8"))
        self.__logger.info("Update youtube-dl output: {}".format(update_youtube_dl_output))

    def __do_housekeeping(self):
        self.__video_player.clear_screen()
        if self.__process_and_play_vid_proc_pgid:
            self.__logger.info("Killing process and play video process group (PGID: " +
                f"{self.__process_and_play_vid_proc_pgid})...")
            try:
                os.killpg(self.__process_and_play_vid_proc_pgid, signal.SIGTERM)
            except Exception:
                # might raise: `ProcessLookupError: [Errno 3] No such process`
                pass

        self.__logger.info("Deleting ffmpeg_to_python fifos...")
        path_glob = shlex.quote(tempfile.gettempdir() + "/" + self.__FFMPEG_TO_PYTHON_FIFO_PREFIX) + '*'
        cleanup_ffmpeg_to_python_fifos_cmd = f'sudo rm -rf {path_glob}'
        subprocess.check_output(cleanup_ffmpeg_to_python_fifos_cmd, shell = True, executable = '/usr/bin/bash')

        self.__logger.info("Deleting incomplete video downloads...")
        cleanup_incomplete_video_downloads_cmd = f'sudo rm -rf *{shlex.quote(self.__TEMP_VIDEO_DOWNLOAD_SUFFIX)}'
        subprocess.check_output(cleanup_incomplete_video_downloads_cmd, shell = True, executable = '/usr/bin/bash')

        self.__video_info = None

    def __register_signal_handlers(self):
        signal.signal(signal.SIGINT, self.__signal_handler)
        signal.signal(signal.SIGHUP, self.__signal_handler)
        signal.signal(signal.SIGQUIT, self.__signal_handler)
        signal.signal(signal.SIGABRT, self.__signal_handler)
        signal.signal(signal.SIGFPE, self.__signal_handler)
        signal.signal(signal.SIGSEGV, self.__signal_handler)
        signal.signal(signal.SIGPIPE, self.__signal_handler)
        signal.signal(signal.SIGTERM, self.__signal_handler)

    def __signal_handler(self, sig, frame):
        self.__logger.info(f"Caught signal {sig}, exiting gracefully...")
        self.__do_housekeeping()
        sys.exit(sig)
