import os

import random
import re
from typing import Tuple

from pixie import pixie, Font, Image

from module.config import Config


def text_size(content: str, font: Font) -> Tuple[int, int]:
    bounds = font.layout_bounds(content)
    return bounds.x, bounds.y


class Color:
    def __init__(self, hex_color: str):
        self.hex_color = hex_color
        self.rgb = tuple(int(hex_color[1 + i:1 + i + 2], 16) for i in (0, 2, 4))

    @staticmethod
    def from_hex(hex_color: str) -> 'Color':
        return Color(hex_color)

    def __repr__(self):
        return f"Color(Hex={self.hex_color}, RGB={self.rgb})"


class StyledString:
    def __init__(self, config: Config, content: str, font_type: str, font_size: int,
                 font_color: Tuple[int, ...] = (0, 0, 0, 1), line_multiplier=1.0):  # 添加字体颜色
        file_path = os.path.join(config.work_dir, "data", f'OPPOSans-{font_type}.ttf')
        self.content = content
        self.line_multiplier = line_multiplier
        # 尝试加载字体
        try:
            self.font = pixie.read_font(file_path)
            self.font.size = font_size
            if len(font_color) == 3:
                self.font.paint.color = pixie.Color(font_color[0], font_color[1], font_color[2], 1)
            else:
                self.font.paint.color = pixie.Color(font_color[0], font_color[1], font_color[2], font_color[3])
        except IOError:
            raise IOError(f"无法加载字体文件: {file_path}")
        self.height = ImgConvert.draw_string(None, self, 0, 0, draw=False)

    def set_font_color(self, font_color: pixie.Color):
        self.font.paint.color = font_color


class ImgConvert:
    MAX_WIDTH = 1024

    """  
    计算文本在给定字体和大小下的长度（宽度）。  
  
    :param font: 字体
    :param content: 要测量的文本内容  
    :return: 文本的宽度（像素）  
    """

    @staticmethod
    def calculate_string_width(content: StyledString):
        # 获取文本的宽度
        text_width, _ = text_size(content.content, content.font)

        # 返回文本的宽度  
        return text_width

    """  
    绘制文本
  
    :param draw             目标图层
    :param styled_string    包装后的文本内容
    :param x                文本左上角的横坐标 
    :param y                文本左上角的纵坐标
    :param max_width        文本最大长度
    :param line_multiplier  行距
    :param draw             是否绘制
    :return                 计算得到的高度
    """

    @staticmethod
    def draw_string(image: Image | None, styled_string: StyledString, x, y, max_width=MAX_WIDTH,
                    draw: bool = True) -> int:
        offset = 0
        lines = styled_string.content.split("\n")
        text_height = styled_string.font.layout_bounds("A").y

        for line in lines:
            if not line.strip():  # 忽略空行  
                offset += int(text_height * styled_string.line_multiplier)
                continue

            text_width, _ = text_size(line, font=styled_string.font)
            words: list[str] = re.findall(r'\s+\S+|\S+|\s+', line)  # 分割为单词，并把空格放在单词前面处理
            draw_text = ""
            line_x = 0
            first_line = True

            for word in words:
                text_width, _ = text_size(word, font=styled_string.font)
                line_x += text_width

                if line_x <= max_width:
                    draw_text += word
                else:  # 将该单词移到下一行
                    if len(draw_text) > 0:
                        if draw:
                            image.fill_text(styled_string.font, draw_text, pixie.translate(x, y + offset))
                        offset += int(text_height * styled_string.line_multiplier)
                        first_line = False

                    if not first_line:
                        word = word.replace(" ", "")  # 保证除了第一行，每一行开头不是空格
                        text_width, _ = text_size(word, font=styled_string.font)

                    while text_width > max_width:  # 简单的文本分割逻辑，一行塞不下就断开
                        n = text_width // max_width
                        sub_pos = int(len(word) // n)
                        draw_text = word[:sub_pos]
                        draw_width, _ = text_size(draw_text, font=styled_string.font)

                        while draw_width > max_width and sub_pos > 0:  # 微调，保证不溢出
                            sub_pos -= 1
                            draw_text = word[:sub_pos]
                            draw_width, _ = text_size(draw_text, font=styled_string.font)

                        if draw:
                            image.fill_text(styled_string.font, draw_text, pixie.translate(x, y + offset))
                        offset += int(text_height * styled_string.line_multiplier)
                        first_line = False
                        word = word[sub_pos:]
                        text_width -= draw_width

                    draw_text = word
                    line_x = text_width

            if len(draw_text) > 0:
                if draw:
                    image.fill_text(styled_string.font, draw_text, pixie.translate(x, y + offset))
                offset += int(text_height * styled_string.line_multiplier)

        return offset

    """  
    给图片应用覆盖色
  
    :param image        目标图片
    :param tint         覆盖色
    :return             处理完后的图片
    """

    @staticmethod
    def apply_tint(image_path: str, tint: pixie.Color) -> Image:
        image = pixie.read_image(image_path)
        width, height = image.width, image.height
        tinted_image = pixie.Image(width, height)
        alpha = 1
        for x in range(width):
            for y in range(height):
                orig_pixel = image.get_color(x, y)
                mixed_r = orig_pixel.r * (1 - alpha) + tint.r * alpha
                mixed_g = orig_pixel.g * (1 - alpha) + tint.g * alpha
                mixed_b = orig_pixel.b * (1 - alpha) + tint.b * alpha
                tinted_image.set_color(x, y, pixie.Color(mixed_r, mixed_g, mixed_b, orig_pixel.a))
        return tinted_image

    class GradientColors:
        colors = [
            ["#C6FFDD", "#FBD786", "#F7797D"],
            ["#009FFF", "#EC2F4B"],
            ["#22C1C3", "#FDBB2D"],
            ["#3A1C71", "#D76D77", "#FFAF7B"],
            ["#00C3FF", "#FFFF1C"],
            ["#FEAC5E", "#C779D0", "#4BC0C8"],
            ["#C9FFBF", "#FFAFBD"],
            ["#FC354C", "#0ABFBC"],
            ["#355C7D", "#6C5B7B", "#C06C84"],
            ["#00F260", "#0575E6"],
            ["#FC354C", "#0ABFBC"],
            ["#833AB4", "#FD1D1D", "#FCB045"],
            ["#FC466B", "#3F5EFB"],
            ["#BBD2C5", "#536976", "#292E49"],
            ["#40E0D0", "#FF8C00", "#FF0080"],
            ["#3A1C71", "#D76D77", "#FFAF7B"],
            ["#FC00FF", "#00DBDE"]
        ]

        @staticmethod
        def generate_gradient() -> tuple[list[str], list[float]]:
            now_colors = ImgConvert.GradientColors.colors[random.randint(0, len(ImgConvert.GradientColors.colors) - 1)]
            if random.randint(0, 1):
                now_colors.reverse()
            colors_list = [color for color in now_colors]
            position_list = [0.0, 1.0] if len(now_colors) == 2 else [0.0, 0.5, 1.0]
            return colors_list, position_list
