# lightness
## About
[![Lightness](https://lh3.googleusercontent.com/50Q5aQS7kWFsroNjzMIAM1pqVv42ulz_HItEhe2L8xTaOFm2AilcrGnE-fDCPQp0yWgW7cwHRb4f-xewnBwltcw0uFNSf3Cr0rMYlcJwHqVRCap3w8IQ9M4Udi9wRc-mVDdev1I8Z1JBOG5AVuqcpQL0BAIBUWdLRRDBOrXLuQQfYntW8PVBvr-2BXv88lZlFz9a98cHZDFcW3UobFMXGKrZEOd7sEE4KwrNQNgNni3hd3RgLs3CQui1WWuphBTj1ddxzoNUOCPpue26bYFjQI7KKeAtExC5gzQTYki1wMvaugi7My8W9DhBoENevYFDAXuJ2FuiEFPkTMy47ZFDx6QmSwBIuDtG55FqVjlnKj4HoJl8z8peLmV2ZVBte_6BA5geY5U9XT8Euhd93t3XrMs0O7N4VdcbA7SGetj7OKzlw1Fbj3K7wl0mSvEuomQAnSjVwIxnT9V9WuEe0Dy1h7dQ1EtqMJdcmCVf9pvzxMUiUIW3I1K82uS1liqHHd_aLaijgTdSYhus0pgKOIexfpGxEfghjXF6Ye8Va4xyggpkZ9qIQxr5aTkkVeabTrtnBA-CC8g3YmJcIGIjlxd5CY_I3OzzQ6OjdFl4DF-dP6Wu1MjafiTT_LH2wifY4iyigNCLZ322vk2_vJTymZkjIBnCR7HvgDIdSbIMw6CBuzW-42C-n6qulXQ7nyYc0YNt4GXGti4iacyy48hFgpuzBljU=w1125-h625-no)](https://photos.app.goo.gl/hCSq6Vcvd1VbCVPs8)

## Setting up from Scratch
### Install Raspian Lite
https://www.raspberrypi.org/documentation/installation/installing-images/mac.md
1. `diskutil list`
1. `diskutil unmountDisk /dev/disk<disk# from diskutil>`
1. download raspbian lite image from https://www.raspberrypi.org/downloads/raspbian/
1. `sudo dd bs=1m if=image.img of=/dev/rdisk<disk# from diskutil> conv=sync`

### Set up Wifi
[`/boot/wpa_supplicant.conf`](https://raspberrypi.stackexchange.com/a/57023):

    country=US
    ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
    update_config=1
    network={
      ssid="MyWiFiNetwork"
      psk="MyPassword"
      key_mgmt=WPA-PSK
    }

### Enable ssh, Connect
1. create a file `/boot/wpa_supplicant.conf` to enable SSH on the raspberry pi
1. plug in raspberry pi
1. find its IP: `sudo arp-scan --interface=en0 --localnet` or `sudo nmap -sS -p 22 192.168.1.0/24`
1. ssh in `ssh pi@<ip.address>`, password: `raspberry`

### Setup Raspberry Pi
1. `sudo raspi-config`
-- change password
-- enable SPI (interfacing options)
1. `sudo apt-get update`
1. `sudo apt-get upgrade -y`
1. `sudo apt-get install git`

### Setup Git
1. `ssh-keygen -t rsa -b 4096 -C “your@email.com”`
1. `eval "$(ssh-agent -s)"`
1. `ssh-add ~/.ssh/id_rsa`
1. `more ~/.ssh/id_rsa.pub` (copy to git) 
    1. https://help.github.com/en/github/authenticating-to-github/adding-a-new-ssh-key-to-your-github-account
    1. https://github.com/settings/keys

### Checkout Repo
1. `git clone git@github.com:dasl-/lightness.git`
1. `cd lightness`

### Install
1. `./install/install_dependencies.sh`
1. `./install/install.sh`
1. `./utils/make_db`
1. optionally create a config file: [`config.json`](https://gist.github.com/dasl-/2081e697ab1c602a7b5dc02f100dd0a8)
1. optional reboot to confirm services come up automatically and cleanly from a reboot: `sudo shutdown -r now`

### Static IP and DNS A record (optional):
1. Setup static IP for raspberry pi via: https://raspberrypi.stackexchange.com/a/74428 . Basically the steps are:
    1. Add [these lines](https://gist.github.com/dasl-/33f81e0c193424c3c378b08c2d0d5da7) to the end of your `/etc/dhcpcd.conf`
    1. reboot: `sudo shutdown -r now`
1. Optionally reserve the chosen IP on your router (if it supports this) to avoid conflicts
1. Note if you choose 192.168.1.100 for the static IP, then the domain name http://pifi.club/ will resolve to your pi on your wifi network :) ([other options](https://www.devside.net/wamp-server/accessing-websites-on-a-local-network-lan-web-server) for accessing the pi via a domain name)

### Connect GPIO Pins
(pinout: https://pinout.xyz/)
- power: 2
- ground: 6
- data: 19
- clock: 23

### Hacking on the code:
See [development_setup](development_setup.md)

## Troubleshooting
If you see log lines like this:
```
2019-07-01T05:36:14.567699+00:00 [error] [VideoProcessor] video processing unable to keep up in real-time
```
It might mean the pi is getting throttled because it's either overheating or has too low of a voltage from the power supply.

Test running a command like this (video obtained via [youtube](https://www.youtube.com/watch?v=4aeETEoNfOg)):
```
vcgencmd measure_temp && vcgencmd get_throttled && time ffmpeg -threads 1 -i "/home/pi/lightness/data/The Smashing Pumpkins - 1979 (Official Video)@480x360.mp4" -filter:v scale=28x18 -c:a copy -f rawvideo -pix_fmt gray pipe:1 > /dev/null && vcgencmd measure_temp && vcgencmd get_throttled
```

If all is going well, ffmpeg should convert it in ~6x speed. If you're getting throttled, it might only run at ~3x speed.

If temperature is > 80 C, it might be getting [throttled](https://www.techrepublic.com/article/raspberry-pi-overheating-heres-how-to-stop-it-says-microsoft/). Install a heatsink or fan.

You can also interpret the `vcgencmd get_throttled` as shown [here](https://gist.github.com/dasl-/f875535b2b71bcab0f1215a1b39b52cf) and [here](https://www.raspberrypi.org/forums/viewtopic.php?t=240215)

And you can check for undervoltage errors in `dmesg`:
```
$ dmesg -e
[Jul 2 02:47] rpi_firmware_get_throttled: 4 callbacks suppressed
[  +0.000008] Under-voltage detected! (0x00050005)
```

If it shows undervoltage issues when you think everything is wired / powered correctly, you can override the undervoltage settings by adding a line to `/boot/config.txt`:
```
# disables the warning overlays, but additionally allows turbo mode even when low-voltage is present.
avoid_warnings=2
```

Refer to [docs](https://www.raspberrypi.org/documentation/configuration/config-txt/misc.md) and use at your own risk!
