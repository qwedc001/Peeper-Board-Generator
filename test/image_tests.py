import unittest

from module.ImgConvert import ImgConvert


class GenerateTest(unittest.TestCase):
    def test_load(self):
        styled_string = ImgConvert.StyledString("Hello, world!", "../data/OPPOSans-B.ttf", 24)
        print(styled_string.content)
        print(styled_string.height)
        print(styled_string.font)
        print(styled_string.line_multiplier)
        self.assertIsNotNone(styled_string.font)


if __name__ == '__main__':
    unittest.main()
