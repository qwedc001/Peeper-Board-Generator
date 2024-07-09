import os
import unittest

import pixie

from module.ImgConvert import ImgConvert
from module.board.misc import MiscBoardGenerator
from module.config import Config
from module.hydro.entry import HydroHandler

config = Config("../config.json")


class GenerateTest(unittest.TestCase):
    def test_load(self):
        styled_string = ImgConvert.StyledString(config, "Hello, world!", "B", 24)
        print(styled_string.content)
        print(styled_string.height)
        print(styled_string.font)
        print(styled_string.line_multiplier)
        self.assertIsNotNone(styled_string.font)

    def test_gen(self):
        output_img = MiscBoardGenerator.generate_image(config, "full", os.path.join(config.work_dir, config.get_config('data'), f'logo.png'))
        output_img.write_file("full.png")
        self.assertIsNotNone(output_img)


    def test_font(self):
        image = pixie.Image(200, 200)
        image.fill(pixie.Color(1, 1, 1, 1))
        font = pixie.read_font(os.path.join(config.work_dir, config.get_config('data'), f'OPPOSans-B.ttf'))
        font.size = 20
        font.paint.color = pixie.Color(0, 0, 0, 0.5)

        text = "Typesetting is the arrangement and composition of text in graphic design and publishing in both digital and traditional medias."

        bounds = font.layout_bounds(text)

        image.fill_text(
            font,
            text,
            bounds = pixie.Vector2(180, 180),
            transform = pixie.translate(10, 10)
        )

        image.write_file("test_font.png")


if __name__ == '__main__':
    unittest.main()
