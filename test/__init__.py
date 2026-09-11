import unittest

# 测试模块按 `*_tests.py` 命名，不在 unittest 默认的 `test*.py` 发现范围内，
# 这里显式声明 load_tests，使 `python -m unittest discover` 也能收集到它们。
TEST_MODULES = (
    "test.common_tests",
    "test.hydro_tests",
    "test.image_tests",
)


def load_tests(loader: unittest.TestLoader, tests: unittest.TestSuite, pattern: str) -> unittest.TestSuite:
    suite = unittest.TestSuite()
    for module_name in TEST_MODULES:
        suite.addTests(loader.loadTestsFromName(module_name))
    return suite
