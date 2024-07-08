import unittest

from module.ImgConvert import ImgConvert
from module.config import Config

config = Config("../config.json")


class GenerateTest(unittest.TestCase):
    def test_load(self):
        styled_string = ImgConvert.StyledString(config, "Hello, world!", "B", 24)
        print(styled_string.content)
        print(styled_string.height)
        print(styled_string.font)
        print(styled_string.line_multiplier)
        self.assertIsNotNone(styled_string.font)


if __name__ == '__main__':
    unittest.main()
