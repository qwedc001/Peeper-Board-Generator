"""用户信息名片：参考 OBot-ACM 的 /cf id 渲染图。"""

import logging
import os
import random
import tempfile
from dataclasses import dataclass, field
from datetime import datetime

import pixie
from easy_pixie import StyledString, Loc, apply_tint, calculate_height, calculate_width, change_alpha, \
    darken_color, draw_gradient_rect, draw_img, draw_mask_rect, draw_text, GradientColor, \
    GradientDirection, hex_to_color, lighten_color, pick_gradient_color, tuple_to_color

from module.board.model import RenderableSection, Renderer
from module.config import Config
from module.constants import VERSION_INFO
from module.utils import fetch_url

_CONTENT_WIDTH = 1216
_CONTAINER_PADDING = 32
_SIDE_PADDING = 128
_TOP_PADDING = 168
_BOTTOM_PADDING = 158
_SECTION_PADDING = 108

_AVATAR_SIZE = 176
_AVATAR_RADIUS = 44
_AVATAR_GAP = 48
_AVATAR_RING = 7
_HANDLE_GAP = 24
_ICON_SIZE = 44
_ICON_GAP = 16
_DETAIL_GAP = 28

_BAND_PADDING = 60
_BAND_SIDE_PADDING = 64
_BAND_RADIUS = 48
_RATING_SIZE = 168
_RATING_MIN_SIZE = 108
_RANK_SIZE = 40
_RANK_MIN_SIZE = 28

_CELL_HEIGHT = 168
_CELL_GAP = 32
_CELL_RADIUS = 36
_CELL_SIDE_PADDING = 40
_CELL_VERTICAL_PADDING = 36
_CELL_VALUE_SIZE = 56
_CELL_VALUE_MIN_SIZE = 40
_CELL_LABEL_SIZE = 26

_CONTENT_COLOR = (0, 0, 0, 208)
_BODY_COLOR = (0, 0, 0, 172)
_MUTED_COLOR = (0, 0, 0, 116)


@dataclass
class UserCardSection:
    title: str
    lines: list[str]


@dataclass
class UserCardInfo:
    platform_name: str
    handle: str
    accent_color: str = ""
    avatar_url: str = ""
    logo_url: str = ""
    data_source: str = ""
    rating: str = ""
    rank: str = ""
    social: list[str] = field(default_factory=list)
    timeline: list[str] = field(default_factory=list)
    metrics: list[tuple[str, str]] = field(default_factory=list)
    sections: list[UserCardSection] = field(default_factory=list)


def _fit_styled_string(content: str, weight: str, max_size: int, min_size: int,
                       max_width: int, **kwargs) -> StyledString:
    size = max_size
    while size > min_size:
        candidate = StyledString(content, weight, size, **kwargs)
        if calculate_width(candidate) <= max_width:
            return candidate
        size -= 2
    return StyledString(content, weight, min_size, **kwargs)


def _is_vivid(hex_str: str) -> bool:
    color = hex_to_color(hex_str)
    max_channel, min_channel = max(color.r, color.g, color.b), min(color.r, color.g, color.b)
    return (0.299 * color.r + 0.587 * color.g + 0.114 * color.b < 0.8
            and max_channel > 0 and (max_channel - min_channel) / max_channel >= 0.15)


def _pick_theme_color() -> tuple[str, str]:
    """随机取一个足够鲜艳的渐变色作为主题色"""
    for _ in range(12):
        picked = pick_gradient_color()
        vivid_colors = [color for color in picked.color_list
                        if isinstance(color, str) and _is_vivid(color)]
        if vivid_colors:
            return random.choice(vivid_colors), picked.name
    return "#2F80ED", "Fallback"


def _download_image(url: str) -> pixie.Image | None:
    if not url:
        return None
    if url.startswith("//"):
        url = "https:" + url

    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_file:
            temp_file.write(fetch_url(url, method='get').content)
            temp_path = temp_file.name
        return pixie.read_image(temp_path)
    except Exception as e:
        logging.warning(f"加载图片失败 {url}: {e}")
        return None
    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)


def _load_avatar(url: str) -> pixie.Image | None:
    avatar = _download_image(url)
    if avatar is None:
        return None
    avatar = avatar.resize(_AVATAR_SIZE, _AVATAR_SIZE)
    mask = pixie.Mask(_AVATAR_SIZE, _AVATAR_SIZE)
    path = pixie.Path()
    path.rounded_rect(0, 0, _AVATAR_SIZE, _AVATAR_SIZE,
                      _AVATAR_RADIUS, _AVATAR_RADIUS, _AVATAR_RADIUS, _AVATAR_RADIUS)
    mask.fill_path(path)
    avatar.mask_draw(mask)
    return avatar


class _IdentitySection(RenderableSection):

    def __init__(self, config: Config, info: UserCardInfo, text_color: pixie.Color, img_path: str):
        super().__init__(config)
        self._avatar = _load_avatar(info.avatar_url)
        self._ring_color = change_alpha(hex_to_color(info.accent_color), alpha=88)
        icon = _download_image(info.logo_url)
        if icon is not None:
            self.img_icon = apply_tint(icon.resize(_ICON_SIZE, _ICON_SIZE), text_color)
        else:
            self.img_icon = (Renderer.load_img_resource(img_path, text_color)
                             if img_path and os.path.exists(img_path) else None)

        head_width = _CONTENT_WIDTH - (_AVATAR_SIZE + _AVATAR_GAP if self._avatar else 0)
        self.str_platform = StyledString(
            f"{info.platform_name} ID", 'H', 36, font_color=text_color, max_width=head_width
        )
        self.str_handle = StyledString(
            info.handle, 'H', 92, font_color=text_color, max_width=head_width
        )
        self.str_social = StyledString(
            ' · '.join(info.social), 'B', 28, font_color=_MUTED_COLOR,
            line_multiplier=1.3, padding_bottom=10, max_width=_CONTENT_WIDTH
        )
        self.str_timeline = StyledString(
            ' · '.join(info.timeline), 'B', 28, font_color=_MUTED_COLOR,
            line_multiplier=1.3, max_width=_CONTENT_WIDTH
        )
        self._detail_rows = [row for row in [self.str_social, self.str_timeline] if row.content]

        self._head_height = calculate_height([self.str_platform, self.str_handle]) + _HANDLE_GAP
        if self._avatar:
            self._head_height = max(_AVATAR_SIZE, self._head_height)

    def get_height(self):
        return (self._head_height +
                (_DETAIL_GAP + calculate_height(self._detail_rows) if self._detail_rows else 0))

    def render(self, img: pixie.Image, x: int, y: int) -> int:
        current_x = x
        if self._avatar:
            avatar_y = y + (self._head_height - _AVATAR_SIZE) // 2
            draw_mask_rect(img, Loc(x - _AVATAR_RING, avatar_y - _AVATAR_RING,
                                    _AVATAR_SIZE + _AVATAR_RING * 2,
                                    _AVATAR_SIZE + _AVATAR_RING * 2),
                           self._ring_color, _AVATAR_RADIUS + _AVATAR_RING)
            draw_img(img, self._avatar, Loc(x, avatar_y, _AVATAR_SIZE, _AVATAR_SIZE))
            current_x = x + _AVATAR_SIZE + _AVATAR_GAP

        head_text_height = calculate_height([self.str_platform, self.str_handle]) + _HANDLE_GAP
        current_y = y + (self._head_height - head_text_height) // 2
        if self.img_icon:
            draw_img(img, self.img_icon, Loc(current_x, current_y + 2, _ICON_SIZE, _ICON_SIZE))
            current_y = draw_text(img, self.str_platform,
                                  current_x + _ICON_SIZE + _ICON_GAP, current_y)
        else:
            current_y = draw_text(img, self.str_platform, current_x, current_y)
        draw_text(img, self.str_handle, current_x, current_y + _HANDLE_GAP)

        if self._detail_rows:
            current_y = y + self._head_height + _DETAIL_GAP
            for row in self._detail_rows:
                current_y = draw_text(img, row, x, current_y)
        return y + self.get_height()


class _RatingSection(RenderableSection):

    def __init__(self, config: Config, info: UserCardInfo, text_color: pixie.Color):
        super().__init__(config)
        accent = hex_to_color(info.accent_color)
        self._panel_color = change_alpha(accent, alpha=36)
        self._pill_color = change_alpha(accent, alpha=48)
        self.str_label = StyledString("Ranking Points", 'M', 30,
                                      font_color=_MUTED_COLOR, padding_bottom=10)
        self.str_rank = (_fit_styled_string(info.rank, 'H', _RANK_SIZE, _RANK_MIN_SIZE,
                                            _CONTENT_WIDTH // 2,
                                            font_color=darken_color(accent, 0.5))
                         if info.rank else None)
        self._rank_width = calculate_width(self.str_rank) if self.str_rank else 0
        self._rank_height = calculate_height(self.str_rank) if self.str_rank else 0
        self._pill_width = int(self._rank_width) + 56
        self._pill_height = int(self._rank_height) + 28
        self.str_rating = _fit_styled_string(
            info.rating, 'H', _RATING_SIZE, _RATING_MIN_SIZE,
            max(256, _CONTENT_WIDTH - _BAND_SIDE_PADDING * 2 - self._pill_width - 72),
            font_color=text_color
        )
        self._left_height = calculate_height([self.str_label, self.str_rating])
        self._right_offset = calculate_height(self.str_label) + 28

    def get_height(self):
        right_height = self._pill_height + 22 if self.str_rank else 0
        return max(self._left_height, self._right_offset + right_height) + _BAND_PADDING * 2 - 20

    def render(self, img: pixie.Image, x: int, y: int) -> int:
        height = self.get_height()
        draw_mask_rect(img, Loc(x, y, _CONTENT_WIDTH, height), self._panel_color, _BAND_RADIUS)

        current_y = draw_text(img, self.str_label, x + _BAND_SIDE_PADDING, y + _BAND_PADDING)
        draw_text(img, self.str_rating, x + _BAND_SIDE_PADDING - 8, current_y)

        if self.str_rank:
            pill_x = x + _CONTENT_WIDTH - _BAND_SIDE_PADDING - self._rank_width - 28
            pill_y = y + _BAND_PADDING + self._right_offset
            draw_mask_rect(img, Loc(pill_x, pill_y, self._pill_width, self._pill_height),
                           self._pill_color, self._pill_height // 2)
            draw_text(img, self.str_rank, pill_x + (self._pill_width - self._rank_width) // 2,
                      pill_y + 14)
        return y + height


class _MetricsSection(RenderableSection):

    def __init__(self, config: Config, metrics: list[tuple[str, str]]):
        super().__init__(config)
        self._cols = (1 if not metrics else
                      len(metrics) if len(metrics) <= 4 else
                      (3 if len(metrics) % 3 == 0 else 4))
        self._cell_width = ((_CONTENT_WIDTH - _CELL_GAP * (self._cols - 1)) // self._cols
                            if metrics else 0)
        inner_width = self._cell_width - _CELL_SIDE_PADDING * 2

        value_size = _CELL_VALUE_SIZE
        while value_size > _CELL_VALUE_MIN_SIZE:
            if all(calculate_width(StyledString(value, 'H', value_size)) <= inner_width
                   for _, value in metrics):
                break
            value_size -= 2
        self._cells = [
            (StyledString(value, 'H', value_size, font_color=_CONTENT_COLOR,
                          max_width=inner_width, padding_bottom=6),
             StyledString(label, 'B', _CELL_LABEL_SIZE, font_color=_MUTED_COLOR,
                          max_width=inner_width))
            for label, value in metrics
        ]
        self._row_height = max(
            _CELL_HEIGHT,
            max((calculate_height([value, label]) for value, label in self._cells), default=0)
            + _CELL_VERTICAL_PADDING * 2
        )

    def get_height(self):
        rows = (len(self._cells) + self._cols - 1) // self._cols
        return rows * self._row_height + (rows - 1) * _CELL_GAP

    def render(self, img: pixie.Image, x: int, y: int) -> int:
        for idx, (str_value, str_label) in enumerate(self._cells):
            row, col = divmod(idx, self._cols)
            cell_x = x + col * (self._cell_width + _CELL_GAP)
            cell_y = y + row * (self._row_height + _CELL_GAP)
            draw_mask_rect(img, Loc(cell_x, cell_y, self._cell_width, self._row_height),
                           (255, 255, 255, 136), _CELL_RADIUS)

            content_height = calculate_height([str_value, str_label])
            content_y = cell_y + (self._row_height - content_height) // 2
            draw_text(img, str_value, cell_x + _CELL_SIDE_PADDING, content_y)
            draw_text(img, str_label, cell_x + _CELL_SIDE_PADDING,
                      content_y + calculate_height(str_value))
        return y + self.get_height()


class _DetailSection(RenderableSection):

    def __init__(self, config: Config, section: UserCardSection, accent_color: pixie.Color):
        super().__init__(config)
        self._bar_color = change_alpha(accent_color, alpha=108)
        self.str_title = StyledString(section.title, 'H', 34,
                                      font_color=_CONTENT_COLOR, padding_bottom=26)
        self.str_lines = [StyledString(line, 'M', 30, font_color=_BODY_COLOR,
                                       line_multiplier=1.3, padding_bottom=10,
                                       max_width=_CONTENT_WIDTH - 28)
                          for line in section.lines]

    def get_height(self):
        return calculate_height(self.str_title) + calculate_height(self.str_lines)

    def render(self, img: pixie.Image, x: int, y: int) -> int:
        draw_mask_rect(img, Loc(x, y + 8, 6, 30), self._bar_color, 3)
        current_y = draw_text(img, self.str_title, x + 28, y)
        for str_line in self.str_lines:
            current_y = draw_text(img, str_line, x + 28, current_y)
        return y + self.get_height()


class _FooterSection(RenderableSection):

    def __init__(self, config: Config, data_source: str = ""):
        super().__init__(config)
        self.str_note = StyledString(
            f'Generated at {datetime.now().strftime("%Y/%m/%d %H:%M:%S")} · '
            f"Peeper Board Generator {VERSION_INFO}.",
            'B', 24, font_color=_MUTED_COLOR, line_multiplier=1.3, max_width=_CONTENT_WIDTH
        )
        self.str_source = (StyledString(f"Data from {data_source}", 'B', 24,
                                        font_color=_MUTED_COLOR, max_width=_CONTENT_WIDTH)
                           if data_source else None)

    def get_height(self):
        return (2 + 30 + calculate_height(self.str_note) +
                (12 + calculate_height(self.str_source) if self.str_source else 0))

    def render(self, img: pixie.Image, x: int, y: int) -> int:
        draw_mask_rect(img, Loc(x, y, _CONTENT_WIDTH, 2), (0, 0, 0, 24), 1)
        current_y = draw_text(img, self.str_note, x, y + 30)
        if self.str_source:
            draw_text(img, self.str_source, x, current_y + 12)
        return y + self.get_height()


class UserCardGenerator(Renderer):

    def __init__(self, config: Config, info: UserCardInfo, img_path: str = ""):
        super().__init__(config)
        base_color, palette_name = _pick_theme_color()
        if not info.accent_color:
            info.accent_color = base_color
        self._accent_color = hex_to_color(info.accent_color)
        self._text_color = darken_color(self._accent_color, 0.32)
        self._gradient_color = GradientColor(
            ["#fcfcfc", lighten_color(self._accent_color, 0.3)], [0.0, 1.0], palette_name
        )

        self.sections = [_IdentitySection(config, info, self._text_color, img_path)]
        if info.rating:
            self.sections.append(_RatingSection(config, info, self._text_color))
        if info.metrics:
            self.sections.append(_MetricsSection(config, info.metrics))
        self.sections.extend(_DetailSection(config, section, self._accent_color)
                             for section in info.sections)
        self.sections.append(_FooterSection(config, info.data_source))

    def render(self) -> pixie.Image:
        width = _CONTENT_WIDTH + _SIDE_PADDING * 2
        height = (sum(section.get_height() for section in self.sections) +
                  _SECTION_PADDING * (len(self.sections) - 1) +
                  _TOP_PADDING + _BOTTOM_PADDING)

        img = pixie.Image(width + _CONTAINER_PADDING * 2, height + _CONTAINER_PADDING * 2)
        img.fill(tuple_to_color((0, 0, 0)))
        background_loc = Loc(_CONTAINER_PADDING, _CONTAINER_PADDING, width, height)
        draw_gradient_rect(img, background_loc, self._gradient_color,
                           GradientDirection.DIAGONAL_LEFT_TO_RIGHT, 96)
        draw_mask_rect(img, background_loc, (255, 255, 255, 152), 96)

        current_y = _CONTAINER_PADDING + _TOP_PADDING - _SECTION_PADDING
        for section in self.sections:
            current_y += _SECTION_PADDING
            current_y = section.render(img, _CONTAINER_PADDING + _SIDE_PADDING, current_y)
        return img


def render_user_notice(config: Config, platform_name: str, handle: str, message: str,
                       img_path: str = "", data_source: str = "",
                       logo_url: str = "") -> pixie.Image:
    info = UserCardInfo(platform_name=platform_name, handle=handle, timeline=[message],
                        data_source=data_source, logo_url=logo_url)
    return UserCardGenerator(config, info, img_path).render()
