import cv2
import sys

# device_model = 11
Center_Operate_Mode = 0
Exchange_Mode = 1
targetFPS = 12.0
Decode_Vedio_Width = 112
Decode_Video_Height = 512
Target_Result_Width = 252
Decode_One_Picture_Operate_Size = Target_Result_Width * Decode_Video_Height * 8 // 6
Decode_One_Picture_Target_Size = Target_Result_Width * Decode_Video_Height

def convert_image(path):
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

    def adjust_gamma(gamma_code, mode):
        if mode == 0:
            for i in range(256):
                gamma_code[i] = (i * (i + 1) * (i + 1)) >> 16
        elif mode == 1:
            for i in range(256):
                gamma_code[i] = (i * (i + 1)) >> 8
        else:
            for i in range(256):
                if i > 180:
                    gamma_code[i] = -1
                else:
                    gamma_code[i] = ((i + 1) * i) >> 7

    gamma_code = bytearray(256)
    adjust_gamma(gamma_code, 0)

    for i in range(Decode_One_Picture_Operate_Size):
        target[i] = gamma_code[polar_img[i] & 0xff]

    c24 = 0
    c6 = 0
    c3 = 0
    c2 = 0
    c12 = 0

    for h_out in range(Decode_Video_Height):
        h_target = ((Target_Result_Width * h_out) // 3) * 4

        if c24 != 0:
            target[h_target] = 0
            target[h_target + 1] = 0
            target[h_target + 2] = 0
            if c6 != 0:
                target[h_target + 3] = 0
                target[h_target + 4] = 0
                target[h_target + 5] = 0
                if c3 != 0:
                    target[h_target + 6] = 0
                    target[h_target + 7] = 0
                    target[h_target + 8] = 0

        if c2 == 0:
            target[h_target + 9] = 0
            target[h_target + 10] = 0
            target[h_target + 11] = 0
            if c12 == 0:
                target[h_target + 12] = 0
                target[h_target + 13] = 0
                target[h_target + 14] = 0

        c12 += 1
        if c12 == 12:
            c12 = 0
        c24 += 1
        if c24 == 24:
            c24 = 0
        c6 += 1
        if c6 == 6:
            c6 = 0
        c3 += 1
        if c3 == 3:
            c3 = 0
        c2 += 1
        if c2 == 2:
            c2 = 0

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

    buf = bytearray(4)
    i80 = 2
    for i81 in range(Decode_Video_Height * 6):
        for b7 in range(10):
            buf[0] = out[i80]
            buf[1] = out[i80 + 1]
            buf[2] = out[i80 + 2]
            buf[3] = out[i80 + 3]
            out[i80] = (buf[0] & 128) | ((buf[2] & 128) >> 1) | ((buf[0] & 64) >> 1) | ((buf[2] & 64) >> 2) | ((buf[0] & 32) >> 2) | ((buf[2] & 32) >> 3) | ((buf[0] & 16) >> 3) | ((buf[2] & 16) >> 4)
            out[i80 + 1] = ((buf[0] & 1) << 1) | ((buf[0] & 8) << 4) | ((buf[2] & 8) << 3) | ((buf[0] & 4) << 3) | ((buf[2] & 4) << 2) | ((buf[0] & 2) << 2) | ((buf[2] & 2) << 1) | (buf[2] & 1)
            out[i80 + 2] = (buf[1] & 128) | ((buf[3] & 128) >> 1) | ((buf[1] & 64) >> 1) | ((buf[3] & 64) >> 2) | ((buf[1] & 32) >> 2) | ((buf[3] & 32) >> 3) | ((buf[1] & 16) >> 3) | ((buf[3] & 16) >> 4)
            out[i80 + 3] = ((buf[1] & 8) << 4) | ((buf[3] & 8) << 3) | ((buf[1] & 4) << 3) | ((buf[3] & 4) << 2) | ((buf[1] & 2) << 2) | ((buf[3] & 2) << 1) | ((buf[1] & 1) << 1) | (buf[3] & 1)
            i80 += 4
        i80 += 2
    return out

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python3 read_image.py <image_path> <output_path>")
        sys.exit(1)
    
    out = convert_image(sys.argv[1])
    with open(sys.argv[2], "wb") as f:
        f.write(out)
