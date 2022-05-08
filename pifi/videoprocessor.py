import hashlib
import math
import numpy as np
import os
import pathlib
import select
import shlex
import signal
import subprocess
import sys
import tempfile
import time
import traceback

from pifi.logger import Logger
from pifi.datastructure.readoncecircularbuffer import ReadOnceCircularBuffer
from pifi.directoryutils import DirectoryUtils
from pifi.youtubedlexception import YoutubeDlException

class VideoProcessor:

    __DATA_DIRECTORY = 'data'

    __DEFAULT_VIDEO_EXTENSION = '.mp4'
    __TEMP_VIDEO_DOWNLOAD_SUFFIX = '.dl_part'

    __FIFO_PREFIX = 'pifi_fifo'
    __FPS_READY_FILE = '/tmp/fps_ready.file'

    __FRAMES_BUFFER_LENGTH = 1024

    # clear_screen: boolean. If False, then we won't clear the screen during the init phase.
    #   This can be useful because the Queue process starts the loading screen. If we cleared
    #   it in the VideoProcessor before showing the loading screen again, there'd be a brief
    #   flicker in the loading screen image.
    def __init__(self, url, video_settings, video_player, clear_screen):
        self.__logger = Logger().set_namespace(self.__class__.__name__)
        self.__url = url
        self.__video_settings = video_settings
        self.__video_player = video_player
        self.__process_and_play_vid_proc_pgid = None
        self.__init_time = time.time()

        # True if the video already exists (see: VideoSettings.should_save_video)
        self.__is_video_already_downloaded = False
        self.__do_housekeeping(clear_screen)
        self.__register_signal_handlers()

    def process_and_play(self):
        self.__logger.info(f"Starting process_and_play for url: {self.__url}, VideoSettings: " +
            f"{vars(self.__video_settings)}")
        self.__video_player.show_loading_screen()
        video_save_path = self.__get_video_save_path()

        if os.path.isfile(video_save_path):
            self.__logger.info(f'Video has already been downloaded. Using saved video: {video_save_path}')
            self.__is_video_already_downloaded = True
        elif self.__video_settings.should_predownload_video:
            download_command = self.__get_streaming_video_download_cmd() + ' > ' + shlex.quote(self.__get_video_save_path())
            self.__logger.info(f'Downloading video: {download_command}')
            subprocess.call(download_command, shell = True, executable = '/usr/bin/bash')
            self.__logger.info(f'Video download complete: {video_save_path}')
            self.__is_video_already_downloaded = True

        attempt = 1
        max_attempts = 2
        clear_screen = True
        while attempt <= max_attempts:
            try:
                self.__process_and_play_video()
                clear_screen = True
                break
            except YoutubeDlException as e:
                if attempt < max_attempts:
                    self.__logger.warning("Caught exception in VideoProcessor.__process_and_play_video: " +
                        traceback.format_exc())
                    self.__logger.warning("Updating youtube-dl and retrying video...")
                    self.__video_player.show_loading_screen()
                    clear_screen = False
                    self.__update_youtube_dl()
                if attempt >= max_attempts:
                    clear_screen = True
                    raise e
            finally:
                self.__do_housekeeping(clear_screen = clear_screen)
            attempt += 1
        self.__logger.info("Finished process_and_play")

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
        ffmpeg_to_python_fifo_name = self.__make_fifo(additional_prefix = 'ffmpeg_to_python')
        fps_fifo_name = self.__make_fifo(additional_prefix = 'fps')

        process_and_play_vid_cmd = self.__get_process_and_play_vid_cmd(ffmpeg_to_python_fifo_name, fps_fifo_name)
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
        last_frame = None
        vid_processing_lag_counter = 0
        is_ffmpeg_done_outputting = False
        frames = ReadOnceCircularBuffer(self.__FRAMES_BUFFER_LENGTH)
        ffmpeg_to_python_fifo = open(ffmpeg_to_python_fifo_name, 'rb')

        fps = self.__read_fps_from_fifo(fps_fifo_name)
        frame_length = 1 / fps
        pathlib.Path(self.__FPS_READY_FILE).touch()
        while True:
            if is_ffmpeg_done_outputting or frames.is_full():
                pass
            else:
                is_ffmpeg_done_outputting, vid_start_time = self.__populate_frames(
                    frames, ffmpeg_to_python_fifo, vid_start_time, bytes_per_frame, np_array_shape
                )

            if vid_start_time is None:
                # video has not started being processed yet
                pass
            else:
                if self.__init_time:
                    self.__logger.info(f"Started playing video after {round(time.time() - self.__init_time, 3)} s.")
                    self.__init_time = None

                is_video_done_playing, last_frame, vid_processing_lag_counter = self.__play_video(
                    frames, vid_start_time, frame_length, is_ffmpeg_done_outputting,
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

    def __populate_frames(
        self, frames, ffmpeg_to_python_fifo, vid_start_time, bytes_per_frame, np_array_shape
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
            vid_start_time = time.time() + (0.075 if self.__video_settings.should_play_audio else 0)

        frames.append(
            np.frombuffer(ffmpeg_output, np.uint8).reshape(np_array_shape)
        )
        return [False, vid_start_time]

    def __play_video(
        self, frames, vid_start_time, frame_length, is_ffmpeg_done_outputting,
        last_frame, vid_processing_lag_counter
    ):
        cur_frame = max(math.floor((time.time() - vid_start_time) / frame_length), 0)
        if cur_frame >= len(frames):
            if is_ffmpeg_done_outputting:
                self.__logger.info("Video done playing. Video processing lag counter: {}.".format(vid_processing_lag_counter))
                return [True, cur_frame, vid_processing_lag_counter]
            else:
                vid_processing_lag_counter += 1
                if vid_processing_lag_counter % 1000 == 0 or vid_processing_lag_counter == 1:
                    self.__logger.error(
                        f"Video processing is lagging. Counter: {vid_processing_lag_counter}. " +
                        f"Frames available: {frames.unread_length()}."
                    )
                cur_frame = len(frames) - 1 # play the most recent frame we have

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
        self.__video_player.play_frame(frames[cur_frame])
        return [False, cur_frame, vid_processing_lag_counter]

    def __get_process_and_play_vid_cmd(self, ffmpeg_to_python_fifo_name, fps_fifo_name):
        video_save_path = self.__get_video_save_path()
        vid_data_cmd = None
        if self.__is_video_already_downloaded:
            vid_data_cmd = '< {} '.format(shlex.quote(video_save_path))
        else:
            vid_data_cmd = self.__get_streaming_video_download_cmd() + ' | '

        # Explanation of the FPS calculation pipeline:
        #
        # cat - >/dev/null: Prevent tee from exiting uncleanly (SIGPIPE) after ffprobe has finished probing.
        #
        # mbuffer: use mbuffer so that writes to ffprobe are not blocked by shell pipeline backpressure.
        #   Note: ffprobe may need to read a number of bytes proportional to the video size, thus there may
        #   be no buffer size that works for all videos (see: https://stackoverflow.com/a/70707003/627663 )
        #   But our current buffer size works for videos that are ~24 hours long, so it's good enough in
        #   most cases. Something fails for videos that are 100h+ long, but I believe it's unrelated to
        #   mbuffer size -- those videos failed even with our old model of calculating FPS separately from
        #   the video playback pipeline. See: https://github.com/yt-dlp/yt-dlp/issues/3390
        #
        # while true ... : The pipeline will wait until a signal is given (the existence of the __FPS_READY_FILE)
        #   before data is emitted downstream. The signal will be given once the videoprocessor has finished
        #   calculating the FPS of the video. The FPS is calculated by ffprobe and communicated to the
        #   videoprocessor via the fps_fifo_name fifo.
        ffprobe_cmd = f'ffprobe -v 0 -of csv=p=0 -select_streams v:0 -show_entries stream=r_frame_rate - > {fps_fifo_name}'
        ffprobe_mbuffer = self.__get_mbuffer_cmd(1024 * 1024 * 50, '/tmp/mbuffer-ffprobe.out')
        fps_cmd = (f'tee >( {ffprobe_cmd} && cat - >/dev/null ) | {ffprobe_mbuffer} | ' +
            f'{{ while true ; do [ -f {self.__FPS_READY_FILE} ] && break || sleep 0.1 ; done && cat - ; }} | ')

        maybe_play_audio_tee = ''
        if self.__video_settings.should_play_audio:
            # Add mbuffer because otherwise the ffplay command blocks the whole pipeline. Because
            # audio can only play in real-time, this would block ffmpeg from processing the frames
            # as fast as it otherwise could. This prevents us from building up a big enough buffer
            # in the frames circular buffer to withstand blips in performance. This
            # ensures the circular buffer will generally get filled, rather than lingering around
            # only ~70 frames full. Makes it less likely that we will fall behind in video
            # processing.
            maybe_play_audio_tee = (">( " +
                self.__get_mbuffer_cmd(1024 * 1024 * 10, '/tmp/mbuffer-ffplay.out') + ' | ' +
                self.__get_ffplay_cmd() +
                " ) ")

        ffmpeg_tee = f'>( {self.__get_ffmpeg_pixel_conversion_cmd()} > {ffmpeg_to_python_fifo_name} ) '

        maybe_save_video_tee = ''
        maybe_mv_saved_video_cmd = ''
        if self.__video_settings.should_save_video and not self.__is_video_already_downloaded:
            self.__logger.info(f'Video will be saved to: {video_save_path}')
            temp_video_save_path = video_save_path + self.__TEMP_VIDEO_DOWNLOAD_SUFFIX
            maybe_save_video_tee = shlex.quote(temp_video_save_path) + ' '
            maybe_mv_saved_video_cmd = '&& mv ' + shlex.quote(temp_video_save_path) + ' ' + shlex.quote(video_save_path)

        process_and_play_vid_cmd = (
            'set -o pipefail && export SHELLOPTS && ' +
            vid_data_cmd + fps_cmd + "tee " +
            maybe_play_audio_tee +
            ffmpeg_tee +
            maybe_save_video_tee +
            "> /dev/null " +
            maybe_mv_saved_video_cmd
        )
        return process_and_play_vid_cmd

    # Download the worst video and the best audio with youtube-dl, and mux them together with ffmpeg.
    # See: https://github.com/dasl-/piwall2/blob/53f5e0acf1894b71d180cee12ae49ddd3736d96a/docs/streaming_high_quality_videos_from_youtube-dl_to_stdout.adoc#solution-muxing-a-streaming-download
    def __get_streaming_video_download_cmd(self):
        # --retries infinite: in case downloading has transient errors
        youtube_dl_cmd_template = "yt-dlp {0} --retries infinite --format {1} --output - {2} | {3}"

        log_opts = '--no-progress'
        if Logger.get_level() <= Logger.DEBUG:
            log_opts = '' # show video download progress
        if not sys.stderr.isatty():
            log_opts += '--newline'

        # 50 MB. Based on one video, 1080p avc1 video consumes about 0.36 MB/s. So this should
        # be enough buffer for ~139s for a 1080p video, which is a lot higher resolution than we
        # are ever likely to use.
        video_buffer_size = 1024 * 1024 * 50

        # Choose 'worst' video because we want our pixel ffmpeg video scaler to do less work when we
        # scale the video down to the LED matrix size.
        #
        # But the height should be at least the height of the LED matrix (this probably only matters
        # if someone made a very large LED matrix such that the worst quality video was lower resolution
        # than the LED matrix pixel dimensions). Filter on only height so that vertical videos don't
        # result in a super large resolution being chosen? /shrug ... could consider adding a filter on
        # width too.
        #
        # Use avc1 because this means h264, and the pi has hardware acceleration for this format.
        # See: https://github.com/dasl-/piwall2/blob/88030a47790e5ae208d2c9fe19f9c623fc736c83/docs/video_formats_and_hardware_acceleration.adoc#youtube--youtube-dl
        #
        # Fallback onto 'worst' rather than 'worstvideo', because some videos (live videos) only
        # have combined video + audio formats. Thus, 'worstvideo' would fail for them.
        video_format = (f'worstvideo[vcodec^=avc1][height>={self.__video_settings.display_height}]/' +
            f'worst[vcodec^=avc1][height>={self.__video_settings.display_height}]')
        youtube_dl_video_cmd = youtube_dl_cmd_template.format(
            shlex.quote(self.__url),
            shlex.quote(video_format),
            log_opts,
            self.__get_mbuffer_cmd(video_buffer_size)
        )

        # Also use a 50MB buffer, because in some cases, the audio stream we download may also contain video.
        audio_buffer_size = 1024 * 1024 * 50
        youtube_dl_audio_cmd = youtube_dl_cmd_template.format(
            shlex.quote(self.__url),
            # bestaudio: try to select the best audio-only format
            # bestaudio*: this is the fallback option -- select the best quality format that contains audio.
            #   It may also contain video, e.g. in the case that there are no audio-only formats available.
            #   Some videos (live videos) only have combined video + audio formats. Thus 'bestaudio' would
            #   fail for them.
            shlex.quote('bestaudio/bestaudio*'),
            log_opts,
            self.__get_mbuffer_cmd(audio_buffer_size)
        )

        # Mux video from the first input with audio from the second input: https://stackoverflow.com/a/12943003/627663
        # We need to specify, because in some cases, either input could contain both audio and video. But in most
        # cases, the first input will have only video, and the second input will have only audio.
        return (f"{self.get_standard_ffmpeg_cmd()} -i <({youtube_dl_video_cmd}) -i <({youtube_dl_audio_cmd}) " +
            "-c copy -map 0:v:0 -map 1:a:0 -shortest -f mpegts -")

    def __get_ffmpeg_pixel_conversion_cmd(self):
        pix_fmt = 'gray'
        if self.__video_settings.is_color_mode_rgb():
            pix_fmt = 'rgb24'

        return (
            self.get_standard_ffmpeg_cmd() + ' '
            '-i pipe:0 ' + # read input video from stdin
            '-filter:v ' + shlex.quote( # resize video
                'scale=' + str(self.__video_settings.display_width) + 'x' + str(self.__video_settings.display_height)) + " "
            '-c:a copy ' + # don't process the audio at all
            '-f rawvideo -pix_fmt ' + shlex.quote(pix_fmt) + " " # output in numpy compatible byte format
            'pipe:1' # output to stdout
        )

    @staticmethod
    def get_standard_ffmpeg_cmd():
        # unfortunately there's no way to make ffmpeg output its stats progress stuff with line breaks
        log_opts = '-nostats '
        if sys.stderr.isatty():
            log_opts = '-stats '

        if Logger.get_level() <= Logger.DEBUG:
            pass # don't change anything, ffmpeg is pretty verbose by default
        else:
            log_opts += '-loglevel error'

        # Note: don't use ffmpeg's `-xerror` flag:
        # https://gist.github.com/dasl-/1ad012f55f33f14b44393960f66c6b00
        return f"ffmpeg -hide_banner {log_opts} "

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

    def __read_fps_from_fifo(self, fps_fifo_name):
        fps = None
        try:
            fps_fifo = open(fps_fifo_name, 'r')
            # Need to call .read() rather than .readline() because in some cases, the output could
            # contain multiple lines. We're only interested in the first line. Closing the fifo
            # after only reading the first line when it has multi-line output would result in
            # SIGPIPE errors
            fps_parts = fps_fifo.read().splitlines()[0].strip().split('/')
            fps_fifo.close()
            fps = float(fps_parts[0]) / float(fps_parts[1])
        except Exception as ex:
            self.__logger.error("Got an error determining the fps: " + str(ex))
            self.__logger.error("Assuming 30 fps for this video.")
            fps = 30
        self.__logger.info(f'Calculated video fps: {fps}')
        return fps

    def __make_fifo(self, additional_prefix = None):
        prefix = self.__FIFO_PREFIX + '__'
        if additional_prefix:
            prefix += additional_prefix + '__'

        make_fifo_cmd = (
            'fifo_name=$(mktemp --tmpdir={} --dry-run {}) && mkfifo -m 600 "$fifo_name" && printf $fifo_name'
            .format(
                tempfile.gettempdir(),
                prefix + 'XXXXXXXXXX'
            )
        )
        self.__logger.info('Making fifo...')
        fifo_name = (subprocess
            .check_output(make_fifo_cmd, shell = True, executable = '/usr/bin/bash')
            .decode("utf-8"))
        return fifo_name

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

    def __do_housekeeping(self, clear_screen = True):
        if clear_screen:
            self.__video_player.clear_screen()
        if self.__process_and_play_vid_proc_pgid:
            self.__logger.info("Killing process and play video process group (PGID: " +
                f"{self.__process_and_play_vid_proc_pgid})...")
            try:
                os.killpg(self.__process_and_play_vid_proc_pgid, signal.SIGTERM)
            except Exception:
                # might raise: `ProcessLookupError: [Errno 3] No such process`
                pass

        self.__logger.info(f"Deleting fifos, incomplete video downloads, and {self.__FPS_READY_FILE} ...")
        fifos_path_glob = shlex.quote(tempfile.gettempdir() + "/" + self.__FIFO_PREFIX) + '*'
        incomplete_video_downloads_path_glob = f'*{shlex.quote(self.__TEMP_VIDEO_DOWNLOAD_SUFFIX)}'
        cleanup_files_cmd = f'sudo rm -rf {fifos_path_glob} {incomplete_video_downloads_path_glob} {self.__FPS_READY_FILE}'
        subprocess.check_output(cleanup_files_cmd, shell = True, executable = '/usr/bin/bash')

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
