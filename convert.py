#!/usr/bin/env python3
import cv2
import sys
import struct

# device_model = 11
Center_Operate_Mode = 0
Exchange_Mode = 1
targetFPS = 12.0
Decode_Vedio_Width = 112
Decode_Video_Height = 512
Target_Result_Width = 252
Decode_One_Picture_Operate_Size = Target_Result_Width * Decode_Video_Height * 8 // 6
Decode_One_Picture_Target_Size = Target_Result_Width * Decode_Video_Height

def convert_image(path, gamma_mode=0):
    img = cv2.imread(path, cv2.IMREAD_COLOR)

    width = img.shape[1]
    height = img.shape[0]

    middlepoint = (width // 2, height // 2)
    polar_img = cv2.warpPolar(img, (width, height), middlepoint, max(width, height) / 2, cv2.WARP_FILL_OUTLIERS + cv2.INTER_LINEAR)

    out = bytearray(Decode_One_Picture_Target_Size)
    target = bytearray(Decode_One_Picture_Operate_Size)

    target_size = (Decode_Vedio_Width, Decode_Video_Height)
    polar_img = cv2.resize(polar_img, target_size)
    polar_img = cv2.cvtColor(polar_img, cv2.COLOR_RGB2BGR)
    # polar_img = cv2.convertTo(polar_img, cv2.CV_8UC3)
    polar_img = polar_img.astype('uint8')
    polar_img = bytes(polar_img)

    def make_gamma_table(mode):
        gamma_code = bytearray(256)
        if mode == 0:
            for i in range(256):
                gamma_code[i] = (i * (i + 1) * (i + 1)) >> 16
        elif mode == 1:
            for i in range(256):
                gamma_code[i] = (i * (i + 1)) >> 8
        else:
            for i in range(256):
                if i > 180:
                    gamma_code[i] = 0xff
                else:
                    gamma_code[i] = ((i + 1) * i) >> 7
        return gamma_code

    gamma_code = make_gamma_table(gamma_mode)

    for i in range(Decode_One_Picture_Operate_Size):
        target[i] = gamma_code[polar_img[i] & 0xff]

    for h_out in range(Decode_Video_Height):
        h_target = ((Target_Result_Width * h_out) // 3) * 4

        if h_out % 24:
            target[h_target] = 0
            target[h_target + 1] = 0
            target[h_target + 2] = 0
            if h_out % 6:
                target[h_target + 3] = 0
                target[h_target + 4] = 0
                target[h_target + 5] = 0
                if h_out % 3:
                    target[h_target + 6] = 0
                    target[h_target + 7] = 0
                    target[h_target + 8] = 0

        if not h_out % 2:
            target[h_target + 9] = 0
            target[h_target + 10] = 0
            target[h_target + 11] = 0
            if not h_out % 12:
                target[h_target + 12] = 0
                target[h_target + 13] = 0
                target[h_target + 14] = 0

    def extract_bits(data, offset, bit):
        result = 0
        for i in range(8):
            result |= ((data[i + offset] >> bit) & 1) << i
        return result

    target_off = 0
    decode_video_start_line_num = Decode_One_Picture_Target_Size
    for h in range(Decode_Video_Height):
        decode_video_start_line_num -= Target_Result_Width
        for switchid in range(Target_Result_Width // 6 - 1, -1, -1):
            out_off = decode_video_start_line_num + switchid
            for bit in range(6):
                b = extract_bits(target, target_off, 2 + bit)
                out[out_off + (Target_Result_Width // 6) * (5 - bit)] = b
            target_off += 8

    for pos in range(0, len(out), 42):
        for pos in range(pos + 2, pos + 42, 4):
            c2,c1 = struct.unpack(">HH", out[pos:][:4])
            res = 0
            for i in range(0, 32, 2):
                res |= (c1 & 1) << i
                res |= (c2 & 1) << i + 1
                c1 >>= 1
                c2 >>= 1
            out[pos:pos+4] = struct.pack(">I", res)

    return out

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python3 read_image.py <image_path> <output_path>")
        sys.exit(1)
    
    out = convert_image(sys.argv[1])
    with open(sys.argv[2], "wb") as f:
        f.write(out)
