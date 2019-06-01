#!/usr/bin/python3
import argparse

#local libraries
import videoplayer, videoprocessor, settings

def parseArgs():
    parser = argparse.ArgumentParser(description='convert a video.')
    parser.add_argument('--url', dest='url', action='store', default='https://www.youtube.com/watch?v=xmUZ6nCFNoU',
        help='youtube video url. default: The Smashing Pumpkins - Today.')
    parser.add_argument('--display-width', dest='display_width', action='store', type=int, default=28, metavar='N',
        help='Number of pixels / units')
    parser.add_argument('--display-height', dest='display_height', action='store', type=int, default=18, metavar='N',
        help='Number of pixels / units')
    parser.add_argument('--color', dest='is_color', action='store_true', default=False,
        help='color output? (default is black and white)')
    parser.add_argument('--brightness', dest='brightness', action='store', type=int, default=3, metavar='N',
        help='Global brightness value. Max of 31.')

    args = parser.parse_args()
    return args

args = parseArgs()
video_settings = settings.Settings(args)

video_player = videoplayer.VideoPlayer(video_settings)
video_processor = videoprocessor.VideoProcessor(video_settings)
video_processor.preprocess_and_play(url = args.url, video_player = video_player)
