import abc
import os
from datetime import datetime

import pixie
from easy_pixie import load_img, apply_tint, change_img_alpha

from module.config import Config

_img_load_cache: dict[str, tuple[float, pixie.Image]] = {}


class Renderer(abc.ABC):
    """
    图片渲染基类

    成员命名规范：渲染组件公开，可用命名前缀: str_, img_, section_；中间量私有
    """

    def __init__(self, config: Config):
        self.config = config

    @abc.abstractmethod
    def render(self) -> pixie.Image:
        pass

    @classmethod
    def load_img_resource(cls, img_path: str, tint_color: pixie.Color | tuple[int, ...] = None,
                          tint_ratio: int = 1, alpha_ratio: float = -1) -> pixie.Image:
        if not os.path.exists(img_path):
            raise FileNotFoundError("Img resource not found")

        # 缓存机制
        img_loaded = None
        if img_path in _img_load_cache:
            last_load_time, img = _img_load_cache[img_path]
            if datetime.now().timestamp() - last_load_time <= 30 * 60:  # 缓存半小时
                img_loaded = img
        if not img_loaded:
            img_loaded = load_img(img_path)
            _img_load_cache[img_path] = datetime.now().timestamp(), img_loaded

        if tint_color:
            img_loaded = apply_tint(img_loaded, tint_color, tint_ratio)
        if alpha_ratio != -1:
            img_loaded = change_img_alpha(img_loaded, alpha_ratio)

        return img_loaded


class RenderableSection(abc.ABC):
    """图片渲染分块基类"""

    def __init__(self, config: Config):
        self.config = config

    def get_columns(self):
        """占几列，重写本方法以实现多列"""
        return 1

    @abc.abstractmethod
    def render(self, img: pixie.Image, x: int, y: int) -> int:
        pass

    @abc.abstractmethod
    def get_height(self):
        pass


class RenderableSectionBundle(RenderableSection):
    """图片渲染分块打包基类"""

    def __init__(self, config: Config, sections: list[RenderableSection], section_padding: int):
        super().__init__(config)
        self._section_padding = section_padding
        self.section_bundle = sections

    def get_columns(self):
        return max([section.get_columns() for section in self.section_bundle])

    def render(self, img: pixie.Image, x: int, y: int) -> int:
        current_x, current_y = x, y

        current_y -= self._section_padding
        for section in self.section_bundle:
            current_y += self._section_padding
            current_y = section.render(img, current_x, current_y)

        return current_y

    def get_height(self):
        return (sum([section.get_height() for section in self.section_bundle]) +
                self._section_padding * (len(self.section_bundle) - 1))


class MultiColumnRenderableSection(RenderableSection):
    """图片渲染多栏分块基类"""

    def __init__(self, config: Config, sections: list[RenderableSection],
                 content_width: int, section_padding: int, column_padding: int):
        super().__init__(config)
        self._content_width = content_width
        self._section_padding = section_padding
        self._column_padding = column_padding
        self.section_bundle = sections

        self._sections_col_id = [0 for _ in range(len(self.section_bundle))]

        one_column_heights = [section.get_height() for section in self.section_bundle
                               if section.get_columns() == 1]
        one_column_height = max(sum(one_column_heights) // self.get_columns(),
                                max(one_column_heights))  # 保证至少能塞下一个

        current_col, current_height = 0, 0  # 分栏（策略：第一栏可以超出，后面不超出第一栏）
        for idx, section in enumerate(self.section_bundle):
            if section.get_columns() > 1 or current_col >= self.get_columns():
                self._sections_col_id[idx] = 0
                continue
            if (current_height + section.get_height() > one_column_height and
                    section.get_height() > one_column_height / 4):  # 让比较小的不单开一列
                current_col += 1
                current_height = 0
            current_height += section.get_height() + self._section_padding
            self._sections_col_id[idx] = current_col % self.get_columns()

    def get_columns(self):
        return max([section.get_columns() for section in self.section_bundle])

    def render(self, img: pixie.Image, x: int, y: int) -> int:
        column_current_y = [y - self._section_padding for _ in range(self.get_columns())]
        for i, section in enumerate(self.section_bundle):
            idx = self._sections_col_id[i]

            # 保证当前栏不会把跨越的某一栏挡住
            if section.get_columns() > 1:
                current_max_y = max([
                    column_current_y[idx + j] for j in range(section.get_columns())
                ])
                for j in range(section.get_columns()):
                    column_current_y[idx + j] = current_max_y

            current_y = column_current_y[idx] + self._section_padding
            current_y = section.render(
                img,
                x + (self._content_width + self._column_padding) * idx,
                current_y
            )
            for j in range(section.get_columns()):
                column_current_y[idx + j] = current_y

        return max(column_current_y)

    def get_height(self):
        column_current_height = [-self._section_padding for _ in range(self.get_columns())]

        for i, section in enumerate(self.section_bundle):
            idx = self._sections_col_id[i]

            # 保证当前栏不会把跨越的某一栏挡住
            if section.get_columns() > 1:
                current_max_height = max([
                    column_current_height[idx + j] for j in range(section.get_columns())
                ])
                for j in range(section.get_columns()):
                    column_current_height[idx + j] = current_max_height

            for j in range(section.get_columns()):
                column_current_height[idx + j] += self._section_padding + section.get_height()

        return max(column_current_height)
