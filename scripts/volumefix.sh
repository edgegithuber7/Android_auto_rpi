#!/system/bin/sh
# volumefix.sh - pin USB DAC hardware gain + Android media volume
# Target: KonstaKANG LineageOS 22.2 (Android 15), Raspberry Pi 5
# DAC: USB combo device (playback + mic) enumerating as card 2
#
# Behaviour:
#   - waits for the DAC device node to appear (boot or reconnect)
#   - sets DAC hardware gain + mic capture to max via tinymix
#   - sets Android media stream (3) to its max (25 on this build)
#   - then passively monitors: only re-sets the slider if something
#     lowered it (unconditional periodic sets audibly interrupt playback)
#
# ADJUST FOR YOUR HARDWARE:
#   DAC_NODE   - check with: ls /dev/snd/  (plug/unplug the DAC)
#   tinymix -D <card>            - card number
#   control numbers (2,3,4,5)    - check with: tinymix -D <card>
#   media max (25)               - check with: cmd media_session volume --stream 3 --get
# NOTE: this tinymix takes integers, not percentages. Two-channel
# controls take two values (e.g. "100 100").

DAC_NODE=/dev/snd/pcmC2D0p

while true; do
    while [ ! -e "$DAC_NODE" ]; do sleep 1; done
    sleep 2
    tinymix -D 2 5 100 100 2>/dev/null   # Headphone Playback Volume (use 90-95 if aux clips)
    tinymix -D 2 4 1 2>/dev/null          # Headphone Playback Switch
    tinymix -D 2 3 100 2>/dev/null        # Mic Capture Volume
    tinymix -D 2 2 1 2>/dev/null          # Mic Capture Switch
    cmd media_session volume --stream 3 --set 25 2>/dev/null
    # Optional: pin the voice-call stream too (fixes quiet calls).
    # Check max first: cmd media_session volume --stream 0 --get
    # cmd media_session volume --stream 0 --set 7 2>/dev/null
    while [ -e "$DAC_NODE" ]; do
        vol=$(cmd media_session volume --stream 3 --get 2>/dev/null | grep -o 'volume is [0-9]*' | grep -o '[0-9]*$')
        if [ -n "$vol" ] && [ "$vol" -lt 25 ]; then
            cmd media_session volume --stream 3 --set 25 2>/dev/null
        fi
        sleep 10
    done
done
