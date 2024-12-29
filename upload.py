#!/usr/bin/env python3
from pwn import *


class FemtoCircleUpload:
    io: remote
    filename: str
    crc: int
    device_models: int
    send_audio_flag: bool

    def send_file(self, filename: str, frames: list[bytes]) -> None:
        for tryno in range(3):
            log.info('Start uploading %s try %d', filename, tryno)
            with remote('192.168.4.1', 20320, level="error") as self.io:
                self.filename = filename
                self.io.send(b'B2DDDDEDC0EEBDF9E5B7')
                time.sleep(0.1)
                self._send_file_request()
                response = self._parse_response()
                match response:
                    case 0:
                        with log.progress('Uploading') as p:
                            for i, frame in enumerate(frames):
                                p.status(f'Uploading frame {i+1}/{len(frames)}')
                                self.io.send(frame)
                                time.sleep(0.2)
                        time.sleep(0.1)
                        self.io.send(b'B2DDDDEDC0EEBDF9E5B7')
                        time.sleep(0.1)
                        break
                    case -1:
                        log.error('Invalid command')
                    case 1:
                        log.error('SDCard error')
                    case 2:
                        log.error('Other phone is sending,please wait and retry')
                    case 4:
                        log.error('Device license error')
                    case _:
                        log.error('Device busy,please try again later')
        else:
            log.error('Failed to upload file')
        time.sleep(0.5)
    
    def _send_file_request(self):
        filename = self.filename.encode('gb2312')
        data_len = bytes([len(filename) // 15, (len(filename) // 3) % 5 + 106, (len(filename) % 15) % 3 + 99])
        file_request = b'B2DDDDED' + data_len + filename + b'C0EEBDF9E5B7'
        self.io.send(file_request)

        # get file request crc
        cnt = [0]*8
        for i in range(8):
            for i2 in range(len(file_request)):
                if (file_request[i2] & (128 >> i)) > 0:
                    cnt[i] += 1
        self.crc = sum(cnt)
        self.crc += (cnt[0] + 199211) * 10
        self.crc += (cnt[1] + 199306) * 12
        self.crc += (cnt[2] + 202003) * 20
        self.crc += (cnt[3] | 90) * 31
        self.crc += (cnt[4] | 165) * 53
        self.crc += (cnt[5] | 195) * 79
        self.crc |= (cnt[6] << 15) + (cnt[7] << 23)
        self.crc &= 0xFFFFFFFF

    def _parse_response(self) -> int:
        data = self.io.recv(4096)
        if data[:8] != b'B2DDDDED' or data[-12:] != b'C0EEBDF9E5B7':
            return -1
        data_len = data[8] * 15 + (data[9] - 106) * 3 + (data[10] - 99)
        if data_len != (len(data) - 23) or data_len != 5:
            return -1
        if data[11] == 0:
            return data[12]
        self.device_models = data[11] & 127
        self.send_audio_flag = (data[11] & 255) >= 128
        if self.device_models < 64:
            crc = (data[12] << 24) + (data[13] << 16) + (data[14] << 8) + data[15]
            return 0 if crc == self.crc else -1
        return 127

if __name__ == '__main__':
    if len(sys.argv) < 1:
        log.warning('Usage: python3 upload.py <filename>')
        exit(1)
    client = FemtoCircleUpload()
    filename = sys.argv[1]
    with open(filename, 'rb') as f:
        frames = [f.read()]
    client.send_file(os.path.basename(filename), frames)
