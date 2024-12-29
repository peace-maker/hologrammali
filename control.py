#!/usr/bin/env python3
from pwn import *


class State:
    filelist: list[str]
    currentPlayNo: int
    deviceType: int
    isHardwareAudioVersion: int
    powerMode: int
    brightness: int
    loopMode: int
    playMode: int
    clockVersionFlag: int

    DEVICE_TYPES = [
        "45cm-F4(17.7 inch)",
        "65cm-F4(25.6 inch)",
        "85cm-F4(33.5 inch)",
        "85cm-F6(33.5 inch)",
        "115cm-F6(45.3 inch)",
        "56cm-F4(22 inch)",
        "18cm-F2(7.1 inch)",
        "52cm-F4(20.5 inch)",
        "30cm-F2(11.8 inch)",
        "100cm-F6(39.4 inch)",
        "80cm-F4(31.5 inch)",
        "14cm-ND(5.6 inch)",
        "42cm-F2(16.5 inch)",
        "32cm-F2(12.6 inch)",
        "70cm-F6(27.1 inch)",
        "28cm-F2(11.0 inch)",
        "14cm-SD(5.6 inch)",
        "65cm-HD(25.6 inch)",
        "10cm-SD(4.0 inch)",
        "10cm-ND(4.0 inch)",
        "60cm-F6(23.6 inch)",
    ]

    def __init__(self, state_data: bytes) -> None:
        self.filelist = []
        i = 0
        while i < len(state_data) - 16:
            filename_len = state_data[i]
            filename = state_data[i+1:i+1+filename_len].decode('gb2312')
            i += filename_len + 1
            self.filelist.append(filename)
        extradata = state_data[-16:]
        self.currentPlayNo = extradata[0]
        self.deviceType = extradata[1]
        self.isHardwareAudioVersion = extradata[2]
        self.powerMode = extradata[3]
        self.brightness = extradata[4]
        self.loopMode = extradata[5]
        self.playMode = extradata[6]
        self.clockVersionFlag = extradata[7]
    
    def deviceTypeStr(self):
        if 0 <= self.deviceType < len(self.DEVICE_TYPES):
            return self.DEVICE_TYPES[self.deviceType]
        return "3D Circle"
    
    def brightnessStr(self):
        BRIGHTNESS_LEVELS = ["High", "Middle", "Low"]
        return BRIGHTNESS_LEVELS[self.brightness]
    
    def powerModeStr(self):
        if self.powerMode != 0:
            return "Sleep"
        if self.playMode != 0:
            return "PAUSE"
        if self.loopMode == 0: # looping
            return "Loop single play"
        return "Loop album play"
    
    def __repr__(self):
        return f"{self.filelist=} {self.currentPlayNo=} deviceType={self.deviceTypeStr()} {self.isHardwareAudioVersion=} Brightness={self.brightnessStr()} Playmode={self.powerModeStr()} {self.clockVersionFlag=}"
    
    def __str__(self):
        return f"{self.deviceTypeStr()} Brightness: {self.brightnessStr()} {self.powerModeStr()}"

class FemtoCircleControl:
    io: remote
    state: State
    _receiver: context.Thread

    def __init__(self, interactive = False):
        self.io = remote('192.168.4.1', 20320, log_level="error")
        # request initial config?
        self.io.send(b'C0EEB7C9BAA3C0EEBDF9E5B7')

        def recv_packet():
            if interactive:
                state_line = term.output()
                file_list_line = term.output()
            try:
                while True:
                    data = self.io.recv(4096)
                    assert data[:12] == b'C0EEB7C9BAA3'
                    assert data[-12:] == b'C0EEBDF9E5B7'
                    payload_len = data[12] * 323 + (data[13] - 99) * 17 + (data[14] - 98)
                    target_len = len(data) - 27
                    # print(f"{payload_len=:#x} {target_len=:#x}")
                    assert payload_len == target_len, payload_len
                    cmd = data[15]
                    payload_data = data[16:-12]
                    if cmd == 105: # i
                        # file list information
                        self.state = State(payload_data)
                        if interactive:
                            state_line.update(str(self.state))
                            file_list_line.update(f"{self.state.filelist}")
                        
                    elif cmd == 114: # r
                        # password return
                        print(f'password: {payload_data}')
                    else:
                        print(f"Unknown response type: {cmd}")
                        print(hexdump(payload_data))
            except Exception as ex:
                print(ex)

        self._receiver = context.Thread(target = recv_packet)
        self._receiver.daemon = True
        self._receiver.start()

    def send_packet(self, data: bytes) -> None:
        data_len = bytes([len(data) // 323, (len(data) // 17) % 19 + 99, (len(data) % 323) % 17 + 98])
        self.io.send(b'C0EEB7C9BAA3' + data_len + data + b'C0EEBDF9E5B7')

    def delete_file(self, idx: int) -> None:
        self.send_packet(b'A' + p8(idx))

    def format(self) -> None:
        self.send_packet(b'j')

    def clear(self) -> None:
        self.send_packet(b'k')

    def increaseBrightness(self) -> None:
        self.send_packet(b'm')

    def decreaseBrightness(self) -> None:
        self.send_packet(b'l')

    def clockwiserotate(self) -> None:
        self.send_packet(b'p')

    def counterclockwiserotate(self) -> None:
        self.send_packet(b'q')

    def setduration(self, duration: int):
        self.send_packet(b'C' + p8(duration))

    def setwificonfig(self, name: bytes, password: bytes):
        assert len(name) >= 8 and len(name) <= 16, len(name)
        assert len(password) >= 8 and len(password) <= 16, len(password)
        self.send_packet(b's' + p8(len(name)) + name + password)

    def readpassword(self) -> None:
        self.send_packet(b'r')

    def setgamma(self, gamma: int) -> None:
        self.send_packet(b'i' + p8(gamma))

    def prev(self):
        self.send_packet(b'd')

    def next(self):
        self.send_packet(b'c')

    def togglePowerMode(self):
        self.send_packet(b'a')

    def setSingleLoop(self):
        self.send_packet(b'g')

    def setAllLoop(self):
        self.send_packet(b'h')
    
    def toggleLoopMode(self):
        if self.state.loopMode == 0:
            self.setAllLoop()
        else:
            self.setSingleLoop()

    def togglePlayPause(self):
        self.send_packet(b'e')

    def playFileFromList(self, file_idx: int):
        self.send_packet(b'B' + p8(file_idx))

    def setclock(self, hours: int, minutes: int, seconds: int) -> None:
        self.send_packet(b'b' + bytes([hours & 0xff, minutes & 0xff, seconds & 0xff, 0]))

    def setclockcolor(self, white: bool):
        self.send_packet(b'b' + bytes([int(white), 0, 0, 3]))

    def setclockonoff(self, on: bool):
        self.send_packet(b'b' + bytes([int(on), 0, 0, 2]))

    def setclockpaneltype(self, panel_type: int):
        # 0: digitalButton, 1: symbol, 2: constellation, 3: chinese
        self.send_packet(b'b' + bytes([panel_type & 0xff, 0, 0, 4]))

def main() -> None:
    api = FemtoCircleControl(interactive=True)

    options = [
        {'label': 'Decrease brightness', 'op': api.decreaseBrightness},
        {'label': 'Increase brightness', 'op': api.increaseBrightness},
        {'label': 'Rotate clockwise', 'op': api.clockwiserotate},
        {'label': 'Rotate counter-clockwise', 'op': api.counterclockwiserotate},
        {'label': 'Previous video', 'op': api.prev},
        {'label': 'Next video', 'op': api.next},
        {'label': 'Toggle loop mode', 'op': api.toggleLoopMode},
        {'label': 'Toggle Play/Pause', 'op': api.togglePlayPause},
        {'label': 'Toggle Power', 'op': api.togglePowerMode},
        {'label': 'Get Wifi password', 'op': api.readpassword},
    ]

    # pwnlib.ui.options
    while True:
        if term.term_mode:
            numfmt = '%' + str(len(str(len(options)))) + 'd) '
            print(' Select option:')
            hs = []
            space = '       '
            arrow = term.text.bold_green('    => ')
            cur = None
            for i, opt in enumerate(options):
                h = term.output(arrow if i == cur else space, frozen = False)
                num = numfmt % (i + 1)
                h1 = term.output(num)
                h2 = term.output(opt['label'] + '\n', indent = len(num) + len(space))
                hs.append((h, h1, h2))
            ds = ''
            while True:
                prev = cur
                was_digit = False
                k = term.key.get()
                if   k == '<up>':
                    if cur is None:
                        cur = 0
                    else:
                        cur = max(0, cur - 1)
                elif k == '<down>':
                    if cur is None:
                        cur = 0
                    else:
                        cur = min(len(options) - 1, cur + 1)
                elif k == 'C-<up>':
                    cur = 0
                elif k == 'C-<down>':
                    cur = len(options) - 1
                elif k in ('<enter>', '<right>'):
                    if cur is not None:
                        options[cur]['op']()
                elif k in tuple(string.digits):
                    was_digit = True
                    d = str(k)
                    n = int(ds + d)
                    if 0 < n <= len(options):
                        ds += d
                        cur = n - 1
                    elif d != '0':
                        ds = d
                        n = int(ds)
                        cur = n - 1

                if prev != cur:
                    if prev is not None:
                        hs[prev][0].update(space)
                    if was_digit:
                        hs[cur][0].update(term.text.bold_green('%5s> ' % ds))
                    else:
                        hs[cur][0].update(arrow)
        else:
            time.sleep(1)

if __name__ == '__main__':
    main()
