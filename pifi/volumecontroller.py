import subprocess
import re
import math

from pifi.config import Config

# Gets and sets alsa volume
class VolumeController:

    __GLOBAL_MIN_VOL_VAL = None
    __GLOBAL_MAX_VOL_VAL = None

    # gets a perceptual loudness %
    # returns a float in the range [0, 100]
    def get_vol_pct(self):
        vol_val = self.get_vol_val()
        if vol_val <= VolumeController.__get_global_min_vol_val():
            return 0

        if VolumeController.__should_adjust_volume_logarithmically():
            # Assume that the volume value is a value in millibels if we are adjusting volume logarithmically.
            # This might be a poor assumption if it's only true on the RPI internal soundcard...
            mb_level = vol_val

            # convert from decibel attenuation amount to perceptual loudness %
            # see: http://www.sengpielaudio.com/calculator-levelchange.htm
            db_level = mb_level / 100
            vol_pct = 100 * math.pow(2, (db_level / 10))
        else:
            vol_pct = 100 * vol_val / VolumeController.__get_limited_max_vol_val()

        vol_pct = max(0, vol_pct)
        vol_pct = min(100, vol_pct)
        return vol_pct

    # takes a perceptual loudness %.
    # vol_pct should be a float in the range [0, 100]
    def set_vol_pct(self, vol_pct):
        vol_pct = max(0, vol_pct)
        vol_pct = min(100, vol_pct)

        if VolumeController.__should_adjust_volume_logarithmically():
            # Assume that the volume value is a value in millibels if we are adjusting volume logarithmically.
            # This might be a poor assumption if it's only true on the RPI internal soundcard...
            mb_level = VolumeController.pct_to_millibels(vol_pct)
            vol_val = mb_level
        else:
            vol_val = vol_pct * VolumeController.__get_limited_max_vol_val() / 100

        vol_val = round(vol_val)
        subprocess.check_output(
            ('amixer', '-c', str(Config.get('sound.card', 0)), 'cset', f'numid={Config.get("sound.numid", 1)}', '--', str(vol_val))
        )

    # increments volume percentage by the specified increment. The increment should be a float in the range [0, 100]
    # Returns the new volume percent, which will be a float in the range [0, 100]
    def increment_vol_pct(self, inc = 1):
        old_vol_pct = self.get_vol_pct()
        new_vol_pct = old_vol_pct + inc
        new_vol_pct = max(0, new_vol_pct)
        new_vol_pct = min(100, new_vol_pct)
        self.set_vol_pct(new_vol_pct)
        return new_vol_pct

    @staticmethod
    def __get_global_min_vol_val():
        if VolumeController.__GLOBAL_MIN_VOL_VAL is not None:
            return VolumeController.__GLOBAL_MIN_VOL_VAL
        else:
            VolumeController.__init_global_min_and_max_vol_vals()
            return VolumeController.__GLOBAL_MIN_VOL_VAL

    @staticmethod
    def __get_global_max_vol_val():
        if VolumeController.__GLOBAL_MAX_VOL_VAL is not None:
            return VolumeController.__GLOBAL_MAX_VOL_VAL
        else:
            VolumeController.__init_global_min_and_max_vol_vals()
            return VolumeController.__GLOBAL_MAX_VOL_VAL

    @staticmethod
    def __init_global_min_and_max_vol_vals():
        res = subprocess.check_output(
            ('amixer', '-c', str(Config.get('sound.card', 0)), 'cget', f'numid={Config.get("sound.numid", 1)}'),
        ).decode("utf-8")
        m = re.search(r",min=(-?\d+),max=(-?\d+)", res, re.MULTILINE)

        if m is None:
            # use the defaults for the raspberry pi built in headphone jack:
            # amixer output: ; type=INTEGER,access=rw---R--,values=1,min=-10239,max=400,step=0
            # These values are in millibels.
            VolumeController.__GLOBAL_MIN_VOL_VAL = -10239
            VolumeController.__GLOBAL_MAX_VOL_VAL = 400
            return

        VolumeController.__GLOBAL_MIN_VOL_VAL = int(m.group(1))
        VolumeController.__GLOBAL_MAX_VOL_VAL = int(m.group(2))

    @staticmethod
    def __should_adjust_volume_logarithmically():
        if Config.get('sound.adjust_volume_logarithmically') is not None:
            return Config.get('sound.adjust_volume_logarithmically')

        if VolumeController.__is_internal_soundcard_being_used():
            # Assume we're using the raspberry pi internal soundcard's headphone jack
            return True

        return False

    @staticmethod
    def __get_limited_max_vol_val():
        if Config.get('sound.limited_max_vol_val') is not None:
            return Config.get('sound.limited_max_vol_val')

        if VolumeController.__is_internal_soundcard_being_used():
            # Assume we're using the raspberry pi internal soundcard's headphone jack
            # Anything higher than 0 dB may result in clipping.
            return 0

        return VolumeController.__get_global_max_vol_val()

    # Attempt to autodetect if the default soundcard is being used, based on config.json values.
    @staticmethod
    def __is_internal_soundcard_being_used():
        return Config.get('sound.card') == 0 and Config.get('sound.numid') == 1

    # Return volume value. Returns an integer in the range
    # [VolumeController.__get_global_min_vol_val(), VolumeController.__get_limited_max_vol_val()]
    def get_vol_val(self):
        res = subprocess.check_output(
            ('amixer', '-c', str(Config.get('sound.card', 0)), 'cget', f'numid={Config.get("sound.numid", 1)}')
        ).decode("utf-8")
        m = re.search(r" values=(-?\d+)", res, re.MULTILINE)
        if m is None:
            return VolumeController.__get_global_min_vol_val()

        vol_val = int(m.group(1))
        vol_val = max(VolumeController.__get_global_min_vol_val(), vol_val)
        vol_val = min(VolumeController.__get_limited_max_vol_val(), vol_val)
        return vol_val

    # Map the volume from [0, 100] to [0, 1]
    @staticmethod
    def normalize_vol_pct(vol_pct):
        vol_pct_normalized = vol_pct / 100
        vol_pct_normalized = max(0, vol_pct_normalized)
        vol_pct_normalized = min(1, vol_pct_normalized)
        return vol_pct_normalized

    # input: [0, 100]
    # output: [VolumeController.__get_global_min_vol_val(), VolumeController.__get_limited_max_vol_val()]
    @staticmethod
    def pct_to_millibels(vol_pct):
        if (vol_pct <= 0):
            mb_level = VolumeController.__get_global_min_vol_val()
        else:
            # get the decibel adjustment required for the human perceived loudness %.
            # see: http://www.sengpielaudio.com/calculator-levelchange.htm
            mb_level = 1000 * math.log(vol_pct / 100, 2)

        mb_level = max(VolumeController.__get_global_min_vol_val(), mb_level)
        mb_level = min(VolumeController.__get_limited_max_vol_val(), mb_level)
        return mb_level
