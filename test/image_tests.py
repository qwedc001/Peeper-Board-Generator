import os
import unittest

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
        output_img.save("full.png")
        self.assertIsNotNone(output_img)


if __name__ == '__main__':
    unittest.main()
