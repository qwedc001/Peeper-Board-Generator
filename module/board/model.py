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


def _balanced_column_counts(heights: list[int], section_padding: int,
                            column_count: int) -> list[int]:
    """把一组连续的单栏分块按原顺序切成若干栏，使最高的一栏尽量矮。

    返回每栏包含的分块数量（长度固定为 column_count，未使用的栏为 0）。
    分块顺序保持不变，且优先使用较少的栏，避免把相邻的小分块拆散。
    """
    count = len(heights)
    if count == 0:
        return [0] * column_count

    prefix = [0] * (count + 1)
    for i, height in enumerate(heights):
        prefix[i + 1] = prefix[i] + height

    def group_height(start: int, end: int) -> int:
        return prefix[end] - prefix[start] + section_padding * (end - start - 1)

    infinity = float('inf')
    # dp[g][i]：前 i 个分块用 g 栏（每栏至少一个）装下时，最高一栏的最小高度
    max_groups = min(column_count, count)
    dp = [[infinity] * (count + 1) for _ in range(max_groups + 1)]
    cut = [[0] * (count + 1) for _ in range(max_groups + 1)]
    dp[0][0] = 0
    for group in range(1, max_groups + 1):
        for i in range(group, count + 1):
            for j in range(group - 1, i):  # 最后一栏为 [j, i)，不能为空
                if dp[group - 1][j] == infinity:
                    continue
                height = max(dp[group - 1][j], group_height(j, i))
                if height < dp[group][i]:
                    dp[group][i] = height
                    cut[group][i] = j

    best_group = 1  # 最高栏高度相同时优先用较少的栏
    for group in range(2, max_groups + 1):
        if dp[group][count] < dp[best_group][count]:
            best_group = group

    counts, i = [], count
    for group in range(best_group, 0, -1):
        counts.append(i - cut[group][i])
        i = cut[group][i]
    counts.reverse()
    return counts + [0] * (column_count - best_group)


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
        self._assign_columns()

    def _assign_columns(self):
        """按高度均衡分栏（跨栏分块固定从第一栏开始）"""
        column_count = self.get_columns()
        pending: list[int] = []  # 一段连续的单栏分块，整体参与高度均衡

        def flush():
            counts = _balanced_column_counts(
                [self.section_bundle[idx].get_height() for idx in pending],
                self._section_padding, column_count)
            start = 0
            for column, count in enumerate(counts):
                for idx in pending[start:start + count]:
                    self._sections_col_id[idx] = column
                start += count
            pending.clear()

        for idx, section in enumerate(self.section_bundle):
            if section.get_columns() > 1:
                flush()
                self._sections_col_id[idx] = 0
            else:
                pending.append(idx)
        flush()

    def get_columns(self):
        return max([section.get_columns() for section in self.section_bundle])

    def render(self, img: pixie.Image, x: int, y: int) -> int:
        column_current_y = [y - self._section_padding for _ in range(self.get_columns())]
        for i, section in enumerate(self.section_bundle):
            idx = self._sections_col_id[i]
            spanning = section.get_columns() > 1

            # 跨栏分块独占一行：即使它只占其中几栏，也从第一栏开始，
            # 并把所有栏对齐到它的下方，避免右侧栏的小分块跑到上面去
            if spanning:
                current_y = max(column_current_y)
                column_current_y = [current_y] * self.get_columns()

            current_y = column_current_y[idx] + self._section_padding
            current_y = section.render(
                img,
                x + (self._content_width + self._column_padding) * idx,
                current_y
            )
            if spanning:
                column_current_y = [current_y] * self.get_columns()
            else:
                column_current_y[idx] = current_y

        return max(column_current_y)

    def get_height(self):
        column_current_height = [-self._section_padding for _ in range(self.get_columns())]

        for i, section in enumerate(self.section_bundle):
            idx = self._sections_col_id[i]
            section_height = self._section_padding + section.get_height()

            # 跨栏分块独占一行，对齐方式与 render 保持一致
            if section.get_columns() > 1:
                current_height = max(column_current_height) + section_height
                column_current_height = [current_height] * self.get_columns()
            else:
                column_current_height[idx] += section_height

        return max(column_current_height)
