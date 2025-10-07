import os
import unittest

import pixie
from easy_pixie import StyledString

from module.Hydro.entry import HydroHandler
from module.board.misc import MiscBoardGenerator
from module.config import Configs

config = Configs(os.path.join(
    os.path.dirname(__file__), '..', 'config.json'
)).get_configs()[0]


class GenerateTest(unittest.TestCase):
    def test_load(self):
        styled_string = StyledString("Hello, world!", "B", 24)
        print(styled_string.content)
        print(styled_string.height)
        print(styled_string.font)
        print(styled_string.line_multiplier)
        self.assertIsNotNone(styled_string.font)

    def test_gen_full(self):
        HydroHandler(config).save_daily("full")
        output_img = MiscBoardGenerator(config, "full",
                                        str(os.path.join(config.work_dir,
                                                         config.get_config()["data"],
                                                         f'logo.png')),
                                        separate_columns=True).render()
        output_img.write_file("full.png")
        self.assertIsNotNone(output_img)

    def test_gen_now(self):
        HydroHandler(config).save_daily("now")
        output_img = MiscBoardGenerator(config, "now",
                                        str(os.path.join(config.work_dir,
                                                         config.get_config()["data"],
                                                         f'logo.png')),
                                        separate_columns=True).render()
        output_img.write_file("now.png")
        self.assertIsNotNone(output_img)

    def test_gen_verdict(self):
        HydroHandler(config).save_daily("now")
        output_img = MiscBoardGenerator(config, "now",
                                        str(os.path.join(config.work_dir,
                                                         config.get_config()["data"],
                                                         f'logo.png')),
                                        verdict="Wrong Answer",
                                        separate_columns=True).render()
        output_img.write_file("verdict_wa.png")
        self.assertIsNotNone(output_img)

    def test_font(self):
        output_img = pixie.Image(400, 200)
        output_img.fill(pixie.Color(1, 1, 1, 1))
        font = pixie.read_font(os.path.join(config.work_dir, config.get_config()["data"], f'OPPOSans-B.ttf'))
        font.size = 20
        font.paint.color = pixie.Color(0, 0, 0, 0.5)

        text = ("Typesetting is the arrangement and composition of text in graphic design and publishing in both "
                "digital and traditional medias. π 錩 旸 堉 峣 垚 鋆 旻 淏 珺 玥 炘.")

        output_img.fill_text(
            font,
            text,
            bounds=pixie.Vector2(360, 180),
            transform=pixie.translate(10, 10)
        )

        output_img.write_file("test_font.png")
        self.assertIsNotNone(output_img)


if __name__ == '__main__':
    unittest.main()
