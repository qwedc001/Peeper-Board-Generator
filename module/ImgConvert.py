from PIL import Image, ImageDraw, ImageFont
import random
from typing import Tuple, List


def textsize(draw: ImageDraw, content: str, font: ImageFont) -> Tuple[int, int]:
    _, _, width, height = draw.textbbox((0, 0), content, font=font)
    return width, height


class Color:
    def __init__(self, hex_color: str):
        self.hex_color = hex_color
        self.rgb = tuple(int(hex_color[1 + i:1 + i + 2], 16) for i in (0, 2, 4))

    @staticmethod
    def from_hex(hex_color: str) -> 'Color':
        return Color(hex_color)

    def __repr__(self):
        return f"Color(Hex={self.hex_color}, RGB={self.rgb})"


class Pair:
    def __init__(self, first, second):
        self.first = first
        self.second = second

    @staticmethod
    def of(first, second):
        return Pair(first, second)


class StyledString:
    def __init__(self, content, font_type, font_size, font_color=(0, 0, 0)):  # 添加字体颜色  
        self.content = content
        self.font = ImageFont.truetype(font_type, font_size)
        self.font_color = font_color


class ImgConvert:
    MAX_WIDTH = 1024

    """  
    计算文本在给定字体和大小下的长度（宽度）。  
  
    :param font_type: 字体文件 
    :param font_size: 字体大小  
    :param content: 要测量的文本内容  
    :return: 文本的宽度（像素）  
    """

    @staticmethod
    def calculate_string_width(font_type, font_size, content):

        try:
            # 加载字体  
            font = ImageFont.truetype(font_type, font_size)
        except IOError:
            print(f"无法加载字体文件: {font_type}")
            return 0

            # 创建一个虚拟图像，该图像足够大以绘制文本
        image = Image.new('RGB', (ImgConvert.MAX_WIDTH, 100), color=(255, 255, 255))
        draw = ImageDraw.Draw(image)

        # 获取文本的宽度（不实际显示图像）  
        text_width, text_height = textsize(draw, content, font=font)

        # 返回文本的宽度  
        return text_width

    """  
    计算文本在给定字体和大小下的高度。  
  
    :param font_type:       字体文件 
    :param font_size:       字体大小  
    :param content:         要测量的文本内容  
    :param max_width:       文本最大长度
    :param line_multiplier  行距
    :return:                文本的高度
    """

    @staticmethod
    def calculate_string_height(font_type, font_size, content, max_width, line_multiplier):
        # 加载字体  
        font = ImageFont.truetype(font_type, font_size)
        # font = "symbol.ttf"

        # 创建一个足够大的图像来绘制文本（这里只是一个临时图像）
        temp_image = Image.new('RGB', (max_width * 2, 1000), color=(255, 255, 255))
        draw = ImageDraw.Draw(temp_image)

        x, y = 0, 0
        line_height = font.getsize('A')[1]  # 使用'A'的高度作为行高，这通常是一个合理的近似值

        words = content.split()
        line = []

        for word in words:
            # 尝试将单词添加到当前行
            test_width, _ = textsize(draw, content, font=font)

            if test_width <= max_width:
                line.append(word)
            else:
                # 如果当前行太宽，则绘制它并开始新行  
                draw.text((x, y), ' '.join(line), font=font, fill=(0, 0, 0))
                y += line_height * line_multiplier
                line = [word]

                # 绘制最后一行
        draw.text((x, y), ' '.join(line), font=font, fill=(0, 0, 0))
        total_height = y + line_height * line_multiplier  # 确保总高度包括最后一行  

        del temp_image

        return int(total_height)

    """  
    绘制文本
  
    :param image            目标图片
    :param styled_string    包装后的文本内容
    :param x                文本左上角的横坐标 
    :param y                文本左上角的纵坐标
    :param max_width        文本最大长度
    :param line_multiplier  行距
    """

    @staticmethod
    def draw_string(image, styled_string, x, y, max_width, line_multiplier):
        draw = ImageDraw.Draw(image)
        offset = 0
        lines = styled_string.content.split("\n")

        for line in lines:
            if not line.strip():  # 忽略空行  
                offset += int(styled_string.font.getsize("A")[1] * line_multiplier)
                continue

            text_width, text_height = textsize(draw, line, font=styled_string.font)
            temp_text = line

            while text_width > max_width:
                # 简单的文本分割逻辑，考虑是不是需要更复杂的分割逻辑
                n = text_width // max_width
                sub_pos = len(temp_text) // n
                draw_text = temp_text[:sub_pos]
                draw_width, _ = textsize(draw, draw_text, font=styled_string.font)

                while draw_width > max_width and sub_pos > 0:
                    sub_pos -= 1
                    draw_text = temp_text[:sub_pos]
                    draw_width, _ = textsize(draw, draw_text, font=styled_string.font)

                draw.text((x, y + offset), draw_text, font=styled_string.font, fill=styled_string.font_color)
                offset += int(text_height * line_multiplier)
                temp_text = temp_text[sub_pos:]
                text_width -= draw_width

            draw.text((x, y + offset), temp_text, font=styled_string.font, fill=styled_string.font_color)
            offset += int(text_height * line_multiplier)

    """  
    给图片应用覆盖色
  
    :param image        目标图片
    :param tint         覆盖色
    :return             处理完后的图片
    """

    # FIXIT: WHAT

    @staticmethod
    def apply_tint(image, tint):

        def RGBImageFilter(tint):
            tint = tint.lstrip('#')  # 去除可能的前缀'#'  
            length = len(tint)
            return tuple(int(tint[i:i + length // 3], 16) for i in range(0, length, length // 3))

        tint_color = RGBImageFilter(tint)

        image = Image.open(image)
        image = image.convert("RGBA")  # 转换图片到RGBA模式，以支持透明度  
        width, height = image.size  # 获取图片的宽度和高度  

        # 创建一个新的图片对象，用于保存处理后的图片  
        tinted_image = Image.new("RGBA", (width, height), color=tint_color)

        # 使用Pillow的混合功能将原始图片和覆盖色混合  
        # 这里我们简单地使用blend函数，但它不是直接“覆盖”颜色，而是混合  
        # 如果想要“覆盖”效果，可以直接将覆盖色设置为alpha为0（透明）的像素，但这通常不是期望的覆盖效果  
        # 这里的简单处理是混合两个图像，你可能需要根据需要调整alpha值  
        # 注意：这里为了简单起见，我们直接设置alpha为0.5，表示半透明覆盖  
        alpha = 0.5  # 你可以根据需要调整这个值  
        for x in range(width):
            for y in range(height):
                # 获取原始图片和覆盖色在(x, y)位置的像素  
                orig_pixel = image.getpixel((x, y))
                tint_pixel = tint_color + (255,)  # 添加alpha通道，这里设为不透明  

                # 混合像素（简单地将RGB值按alpha混合，注意这里并未真正处理alpha通道）  
                # 注意：这里的混合方式非常基础，并不考虑alpha通道的复杂混合  
                mixed_r = int(orig_pixel[0] * (1 - alpha) + tint_pixel[0] * alpha)
                mixed_g = int(orig_pixel[1] * (1 - alpha) + tint_pixel[1] * alpha)
                mixed_b = int(orig_pixel[2] * (1 - alpha) + tint_pixel[2] * alpha)
                mixed_a = 255  # 这里简单设为不透明，实际使用时可能需要更复杂处理  

                # 设置混合后的像素  
                tinted_image.putpixel((x, y), (mixed_r, mixed_g, mixed_b, mixed_a))

        return tinted_image

    class GradientColors:
        colors = [
            ["#C6FFDD", "#FBD786", "#f7797d"],
            ["#009FFF", "#ec2F4B"],
            ["#22c1c3", "#fdbb2d"],
            ["#3A1C71", "#D76D77", "#FFAF7B"],
            ["#00c3ff", "#ffff1c"],
            ["#FEAC5E", "#C779D0", "#4BC0C8"],
            ["#C9FFBF", "#FFAFBD"],
            ["#FC354C", "#0ABFBC"],
            ["#355C7D", "#6C5B7B", "#C06C84"],
            ["#00F260", "#0575E6"],
            ["#FC354C", "#0ABFBC"],
            ["#833ab4", "#fd1d1d", "#fcb045"],
            ["#FC466B", "#3F5EFB"]
        ]
        """
        随机抽取一个渐变色

        :return     渐变色 <每个颜色所处的位置, 颜色>
        """

        @staticmethod
        def generate_gradient() -> Tuple[List[float], List['Color']]:
            random.shuffle(ImgConvert.GradientColors.colors)  # 这一步其实是不必要的，因为我们直接随机选择一个  
            now_colors = ImgConvert.GradientColors.colors[random.randint(0, len(ImgConvert.GradientColors.colors) - 1)]
            # 50%的概率翻转渐变色  
            if random.randint(0, 1) == 1:
                now_colors.reverse()

            positions = [0.0] * len(now_colors)
            if len(now_colors) == 2:
                positions = [0.0, 1.0]
            elif len(now_colors) == 3:
                positions = [0.0, 0.5, 1.0]

            colors_list = [Color.from_hex(color) for color in now_colors]

            return positions, colors_list

    """
    包含绘制需要的参数的字符串
    """

    class StyledString:
        def __init__(self, content: str, font_type: str, font_size: int, line_multiplier: float = 1.0):
            self.content = content
            self.line_multiplier = line_multiplier

            # 尝试加载字体  
            try:
                self.font = ImageFont.truetype(font_type, font_size)
            except IOError:
                print(f"无法加载字体文件: {font_type}")
                self.font = None  # 或者你可以抛出一个异常  

            # textsize is deprecated and will be removed in Pillow 10 (2023-07-01). Use textbbox or textlength instead.
            if self.font:
                image = Image.new('RGB', (ImgConvert.MAX_WIDTH, 100), color=(255, 255, 255))
                draw = ImageDraw.Draw(image)
                _, text_height = textsize(draw, content, font=self.font)
                self.height = int(text_height * line_multiplier)
            else:
                self.height = 0


styled_string = ImgConvert.StyledString("Hello, world!", "msyh.ttc", 24)
print(styled_string.content)
print(styled_string.height)
print(styled_string.font)  # 这将打印字体对象的表示，或者None如果加载失败  
print(styled_string.line_multiplier)
