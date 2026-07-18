"""Device profiles: what differs between a Pi 4 and a Pi 5 build.

Facts here are taken from CLAUDE.md / docs/GUIDE.md - the HDR-latching fix
is Pi 5-only, everything else applies to both boards.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class BootTarget(Enum):
    CMDLINE = "cmdline.txt"          # /boot/cmdline.txt - single line, space-separated params
    CONFIG_USER = "config_user.txt"  # /boot/config_user.txt - appended lines
    BUILD_PROP = "build.prop"        # /system/build.prop - appended key=value lines
    SETTINGS = "settings"            # settings put global <key> <value>


@dataclass(frozen=True)
class BootItem:
    key: str                # stable id, e.g. "hdmi_ignore_hdr"
    target: BootTarget
    description: str
    # CMDLINE/CONFIG_USER/BUILD_PROP: the literal text to add.
    # SETTINGS: "<setting_key> <value>".
    value: str
    required: bool = True   # optional items default off in the UI (e.g. skip bootanim)
    pi4: bool = True
    pi5: bool = True

    def applies_to(self, profile_name: str) -> bool:
        return self.pi4 if profile_name == "pi4" else self.pi5

    @property
    def setting_key(self) -> str:
        assert self.target is BootTarget.SETTINGS
        return self.value.split(" ", 1)[0]

    @property
    def setting_value(self) -> str:
        assert self.target is BootTarget.SETTINGS
        return self.value.split(" ", 1)[1]


BOOT_ITEMS = [
    BootItem(
        key="hdmi_ignore_hdr",
        target=BootTarget.CONFIG_USER,
        description=(
            "Stop the panel latching into HDR and locking its OSD "
            "(Pi 5 advertises HDR over HDMI; Pi 4 doesn't have this problem)"
        ),
        value="hdmi_ignore_hdr=1",
        pi4=False,
        pi5=True,
    ),
    BootItem(
        key="vc4_force_max_bpc",
        target=BootTarget.CMDLINE,
        description="Force SDR colour signalling over HDMI (pairs with hdmi_ignore_hdr)",
        value="vc4.force_max_bpc=8",
        pi4=False,
        pi5=True,
    ),
    BootItem(
        key="usb_autosuspend",
        target=BootTarget.CMDLINE,
        description="Disable USB autosuspend - the default 2s timeout caused audio dropouts on the DAC",
        value="usbcore.autosuspend=-1",
    ),
    BootItem(
        key="safemedia_bypass",
        target=BootTarget.BUILD_PROP,
        description="Stop the safe-media volume cap re-lowering the DAC's line-out level",
        value="audio.safemedia.bypass=true",
    ),
    BootItem(
        key="no_bootanim",
        target=BootTarget.BUILD_PROP,
        description="Skip the boot animation for a faster cold boot (cosmetic, optional)",
        value="debug.sf.nobootanimation=1",
        required=False,
    ),
    BootItem(
        key="safe_csd_disabled",
        target=BootTarget.SETTINGS,
        description="Disable the safe-volume/CSD system that re-arms and re-lowers headphone volume",
        value="audio_safe_csd_enabled 0",
    ),
    BootItem(
        key="safe_volume_state",
        target=BootTarget.SETTINGS,
        description="Pin the safe-volume state so it doesn't re-cap on DAC reconnect",
        value="audio_safe_volume_state 2",
    ),
]


@dataclass(frozen=True)
class DeviceProfile:
    name: str             # "pi4" / "pi5" - stable id
    label: str            # "Raspberry Pi 4" / "Raspberry Pi 5" - UI display
    konstakang_slug: str  # matches konstakang.com/devices/<slug>/

    @property
    def download_url(self) -> str:
        return f"https://konstakang.com/devices/{self.konstakang_slug}/"

    def boot_items(self) -> list:
        return [item for item in BOOT_ITEMS if item.applies_to(self.name)]


PI4 = DeviceProfile(name="pi4", label="Raspberry Pi 4", konstakang_slug="rpi4")
PI5 = DeviceProfile(name="pi5", label="Raspberry Pi 5", konstakang_slug="rpi5")

PROFILES = [PI4, PI5]


def by_name(name: str) -> DeviceProfile:
    for profile in PROFILES:
        if profile.name == name:
            return profile
    raise KeyError(name)
