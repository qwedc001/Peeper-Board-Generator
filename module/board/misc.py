import logging
import math
import sys
from dataclasses import dataclass
from datetime import datetime

import pixie
from easy_pixie import darken_color, hex_to_color, change_alpha, StyledString, Loc, draw_text, draw_img, \
    calculate_height, GradientColor, tuple_to_color, calculate_width, draw_gradient_rect, \
    GradientDirection, draw_rect, pick_gradient_color, draw_mask_rect

from module.board.model import RenderableSection, Renderer, RenderableSectionBundle, MultiColumnRenderableSection
from module.config import Config
from module.constants import VERSION_INFO
from module.structures import SubmissionData, RankingData
from module.submission import rank_by_verdict, get_first_ac, classify_by_verdict, get_hourly_submissions, \
    get_most_popular_problem, count_users_submitted
from module.utils import rand_tips, load_json, get_date_string
from module.verdict import ALIAS_MAP

_CONTENT_WIDTH = 1248
_RANK_TILE_BASE_WIDTH = 360
_RANK_TILE_STRETCH_WIDTH = 480
_HISTOGRAM_TILE_BASE_HEIGHT = 22
_HISTOGRAM_TILE_STRETCH_HEIGHT = 198
_TOP_PADDING = 168
_BOTTOM_PADDING = 158
_SIDE_PADDING = 128
_COLUMN_PADDING = 32
_SECTION_PADDING = 108


@dataclass
class MiscBoard:
    play_of_the_oj: str
    top_five: list[dict]
    total_board: list[dict]
    total_submits: int
    first_ac: SubmissionData
    verdict_data: dict
    avg_score: float
    ac_rate: float
    hourly_data: dict
    popular_problem: tuple[str, int]
    users_submitted: int


def generate_board_data(submissions: list[SubmissionData], verdict: str) -> MiscBoard:
    result = {}

    verdict_desc = rank_by_verdict(submissions).get(verdict)
    if verdict_desc is None:
        return MiscBoard("", [], _pack_verdict_rank_data(None, verdict),
                         0, get_first_ac(submissions), {}, 0, 0, {},
                         ("", 0), 0)

    result['play_of_the_oj'] = next(iter(verdict_desc))  # 昨日
    total_board = _pack_verdict_rank_data(verdict_desc, verdict)
    result['top_five'] = _slice_rank_data(total_board, 5)  # 昨日
    result['total_board'] = total_board  # 昨日 / 今日
    result['total_submits'] = len(submissions)  # 昨日 / 今日
    result['first_ac'] = get_first_ac(submissions)  # 昨日 / 今日
    result['verdict_data'] = classify_by_verdict(submissions)  # 昨日 / 今日
    result['avg_score'] = result['verdict_data']['avg_score']  # 昨日 / 今日
    result['ac_rate'] = result['verdict_data']['ac_rate']  # 昨日 / 今日
    result['hourly_data'] = get_hourly_submissions(submissions)  # 昨日 / 今日
    result['popular_problem'] = get_most_popular_problem(submissions)  # 昨日 / 今日
    result['users_submitted'] = count_users_submitted(submissions)  # 昨日 / 今日

    board = MiscBoard(play_of_the_oj=result['play_of_the_oj'], top_five=result['top_five'],
                      total_board=result['total_board'], total_submits=result['total_submits'],
                      first_ac=result['first_ac'], verdict_data=result['verdict_data'],
                      avg_score=result['avg_score'], ac_rate=result['ac_rate'],
                      hourly_data=result['hourly_data'], popular_problem=result['popular_problem'],
                      users_submitted=result['users_submitted'])
    return board


def _slice_rank_data(rank: list[dict], lim: int, show_unrated: bool = True) -> list[dict]:
    """针对有排名并列时的切片"""
    if len(rank) == 0:
        return []

    unrated_excluded = [rank_data for rank_data in rank if not rank_data.get('unrated')]
    max_rank = min(lim, unrated_excluded[len(unrated_excluded) - 1]['rank'])
    if not show_unrated:  # 预处理，避免后续无效绘图对象的预绘制
        max_rank = lim
        rank = unrated_excluded

    sliced_data = [rank_data for rank_data in rank if rank_data['rank'] <= max_rank]
    while len(sliced_data) > 0 and sliced_data[-1].get('unrated'):
        sliced_data.pop()  # 保证后面的打星不会计入

    return sliced_data


def _pack_rank_data(rank: list[RankingData], lim: int, show_unrated: bool) -> list[dict]:
    rank_by_ac = sorted(rank, key=lambda x: int(x.accepted), reverse=True)
    rank_data = []
    rank, last_ac, unrated_cnt = 1, -1, 0

    for i, ranking_data in enumerate(rank_by_ac):
        if i > 0 and ranking_data.accepted != last_ac and not ranking_data.unrated:
            rank = i + 1 - unrated_cnt
        if ranking_data.unrated:
            unrated_cnt += 1
        else:
            last_ac = ranking_data.accepted
        rank_data.append({'user': ranking_data.user_name, 'rank': rank,
                          'Accepted': ranking_data.accepted, 'unrated': ranking_data.unrated})

    return _slice_rank_data(rank_data, lim, show_unrated)


def _pack_verdict_rank_data(verdict_desc: dict | None, verdict: str, lim: int = -1) -> list[dict]:
    if verdict_desc is None:
        return []

    total_board = []
    rank = 1
    for i, (user, verdict_cnt) in enumerate(verdict_desc.items()):
        if i > 0 and verdict_cnt[1] != verdict_desc[list(verdict_desc.keys())[i - 1]][1]:
            rank = i + 1
        total_board.append({"user": user, f"{verdict}": verdict_cnt, "rank": rank})

    if lim >= 0:
        total_board = _slice_rank_data(total_board, lim)
    return total_board


def _check_parallel_play_of_the_oj(data: list) -> bool:
    if len(data) == 0:
        return False
    top1_cnt = data[0]['Accepted'][1]
    parallel = False
    for i, item in enumerate(data):
        if i == 0:
            continue
        if item['Accepted'][1] == top1_cnt:
            parallel = True
        break

    return parallel


def _ellipsize_str(origin: any, limit: int) -> str:
    data = str(origin)  # 自动转 str 并加省略号
    if len(data) <= limit or limit <= 1:
        return data
    return data[:(limit - 1) // 2] + "..." + data[-((limit - 1) // 2):]


def _make_watermark(img: pixie.Image, width: int, height: int):
    cp = StyledString(
        "©2023-2025 P.B.G. Dev Team.", 'H', 16, font_color=(0, 0, 0, 72)
    )
    cp_width, cp_height = calculate_width(cp), calculate_height(cp)
    draw_text(img, cp,
              width + 64 - _SIDE_PADDING - cp_width,
              height + 64 - _BOTTOM_PADDING - cp_height - 32)


class _TitleSection(RenderableSection):

    def __init__(self, config: Config, accent_color: str, img_path: str,
                 title: str, subtitle: str):
        super().__init__(config)
        accent_dark_color = darken_color(hex_to_color(accent_color), 0.3)
        accent_dark_color_tran = change_alpha(accent_dark_color, 136)
        self.img_logo = Renderer.load_img_resource(img_path, accent_dark_color)

        self.str_title = StyledString(
            title, 'H', 96, padding_bottom=12, font_color=accent_dark_color
        )
        self.str_subtitle = StyledString(
            subtitle, 'H', 36, font_color=accent_dark_color_tran
        )

    def render(self, img: pixie.Image, x: int, y: int) -> int:
        draw_img(img, self.img_logo, Loc(108, 160, 140, 140))

        current_x, current_y = x, y
        current_y = draw_text(img, self.str_title, 260, current_y)
        current_y = draw_text(img, self.str_subtitle, current_x, current_y)

        return current_y

    def get_height(self):
        return calculate_height([self.str_title, self.str_subtitle])


class _SimpleTextSection(RenderableSection):

    def __init__(self, config: Config, header: str, title: str, hint: str = None):
        super().__init__(config)
        self.str_header = StyledString(
            header, 'B', 36, padding_bottom=16
        )
        self.str_title = StyledString(
            _ellipsize_str(title, 25), 'H', 72, padding_bottom=(16 if hint else 0)
        )
        self.str_hint = StyledString(
            hint, 'M', 28, font_color=(0, 0, 0, 136)
        ) if hint else None

    def render(self, img: pixie.Image, x: int, y: int) -> int:
        current_x, current_y = x, y
        current_y = draw_text(img, self.str_header, current_x, current_y)
        current_y = draw_text(img, self.str_title, current_x, current_y)
        if self.str_hint:
            current_y = draw_text(img, self.str_hint, current_x, current_y)
        return current_y

    def get_height(self):
        return calculate_height([self.str_header, self.str_title, self.str_hint])


class _RankSection(RenderableSection):

    @classmethod
    def _get_tile_gradient_color(cls, unrated: bool, same_rank: bool) -> GradientColor:
        color_list = [
            (0, 0, 0, 12 if unrated else (10 if same_rank else 18)),
            (0, 0, 0, 15 if unrated else (18 if same_rank else 28)),
            (0, 0, 0, 18 if unrated else 32)
        ]
        pos_list = [0.0, 0.5, 1.0]
        return GradientColor(color_list, pos_list, '')

    def _decode_rank_data(self, rank_data: list[dict], rank_key: str) -> list[dict]:
        if len(rank_data) == 0:
            return []

        show_unrated = self.config.get_config()['show_unrated']
        max_val = int(rank_data[0][rank_key][-1]
                      if isinstance(rank_data[0][rank_key], tuple) else
                      rank_data[0][rank_key])
        min_val = int(rank_data[-1][rank_key][-1]
                      if isinstance(rank_data[-1][rank_key], tuple) else
                      rank_data[-1][rank_key])
        color_black = tuple_to_color((0, 0, 0))
        pre_rank = ""
        render_material = []

        for top in rank_data:
            unrated = True if top.get('unrated') else False
            if unrated and not show_unrated:  # 不显示的话不画
                continue

            val = int(top[rank_key][-1] if isinstance(top[rank_key], tuple) else top[rank_key])
            current_rank = "*" if unrated else str(top['rank'])
            same_rank = current_rank == pre_rank
            if not unrated:
                pre_rank = current_rank

            str_rank = StyledString(
                current_rank, 'H', 64,
                font_color=change_alpha(color_black,
                                        100 if unrated else (0 if same_rank else 255))
            )
            str_uname = StyledString(
                _ellipsize_str(top['user'], 25), 'B', 36,
                font_color=change_alpha(color_black, 100 if unrated else 255)
            )
            str_value = StyledString(
                str(val), 'H', 36,
                font_color=change_alpha(color_black, 100 if unrated else 255),
                padding_bottom=32
            )
            tile_progress = (val - min_val + 1) / (max_val - min_val + 1)
            tile_width = _RANK_TILE_BASE_WIDTH + _RANK_TILE_STRETCH_WIDTH * tile_progress
            tile_gradient_color = self._get_tile_gradient_color(unrated, same_rank)

            render_material.append({
                'str_rank': str_rank,
                'str_uname': str_uname,
                'str_value': str_value,
                'tile_width': tile_width,
                'tile_gradient_color': tile_gradient_color
            })

        return render_material

    def __init__(self, config: Config, header: str, title: str,
                 rank_data: list[dict], rank_key: str = "Accepted",
                 hint: str = None, top_count: int = -1,
                 separate_columns: bool = False):
        super().__init__(config)
        self._max_col_count = 3 if separate_columns else 1
        self.str_header = StyledString(
            header, "B", 36, padding_bottom=16
        )
        self.str_title = StyledString(
            title, "H", 72, padding_bottom=(32 if hint else 16)
        )
        self.str_hint = StyledString(
            hint, 'M', 28, font_color=(0, 0, 0, 136), padding_bottom=16
        ) if hint else None
        self.str_tops = StyledString(
            f"Top {top_count}th", "H", 48, padding_bottom=(24 if hint else 16)
        ) if top_count != -1 else None
        self.section_render_materials = self._decode_rank_data(rank_data, rank_key)

    def get_columns(self):
        return min(self._max_col_count, 1 + len(self.section_render_materials) // 32)

    def render(self, img: pixie.Image, x: int, y: int) -> int:
        current_x, current_y = x, y

        current_y = draw_text(img, self.str_header, x, current_y)
        current_y = draw_text(img, self.str_title, x, current_y)

        if self.str_tops:
            current_x += calculate_width(self.str_title) + 28
            current_y -= 102 if self.str_hint else 86
            current_y = draw_text(img, self.str_tops, current_x, current_y)
            current_x = x

        if self.str_hint:
            current_y = draw_text(img, self.str_hint, current_x, current_y)

        column_count = math.ceil(len(self.section_render_materials) / self.get_columns())
        start_x, max_y, start_y = current_x, current_y, current_y
        for idx, item in enumerate(self.section_render_materials):
            current_x = start_x
            draw_gradient_rect(img, Loc(current_x, current_y + 38, item['tile_width'], 52),
                               item['tile_gradient_color'], GradientDirection.HORIZONTAL, 26)
            current_x += 32

            draw_text(img, item['str_rank'], current_x, current_y + 8)
            current_x += calculate_width(item['str_rank']) + 28

            draw_text(img, item['str_uname'], current_x, current_y + 40)
            current_x = max(item['tile_width'] + start_x,
                            current_x + calculate_width(item['str_uname'])) + 36

            current_y = draw_text(img, item['str_value'], current_x, current_y + 40)

            max_y = max(max_y, current_y)
            if (idx + 1) % column_count == 0:  # 分栏
                start_x += _CONTENT_WIDTH + _COLUMN_PADDING
                current_y = start_y

        current_y = max_y - 32  # 最后一项有多余底边距
        return current_y

    def get_height(self):
        height = calculate_height([self.str_header, self.str_title, self.str_tops, self.str_hint])
        if self.str_tops:
            height -= 102 if self.str_hint else 86
        column_count = math.ceil(len(self.section_render_materials) / self.get_columns())
        column_split = [self.section_render_materials[i:i + column_count]
                        for i in range(0, len(self.section_render_materials), column_count)]
        height += max(calculate_height([item['str_value'] for item in column]) +
                      40 * len(column) - 32
                      for column in column_split)
        return height


class _SubmitDetailSection(RenderableSection):

    @classmethod
    def _pack_verdict_detail(cls, verdict_data: dict) -> str:
        return ', '.join([
            str(verdict_data[full]) + alias
            for alias, full in ALIAS_MAP.items()
            if full in verdict_data
        ])

    def __init__(self, config: Config, total_submits: int, verdict_prop: float,
                 users_submitted: int = -1, verdict_data: dict = None,
                 verdict_prop_title: str = "提交通过率", avg_score: float = -1):
        super().__init__(config)
        has_verdict_data = users_submitted != -1 and verdict_data is not None

        self.str_total_header = StyledString(
            "提交总数", 'B', 36, padding_bottom=16
        )
        self.str_total_val = StyledString(
            str(total_submits), 'H', 72
        )

        if avg_score != -1:
            ave_score_split = format(avg_score, '.2f').split('.')  # 分割小数
            self.str_avg_header = StyledString(
                "提交平均分", 'B', 36, padding_bottom=16
            )
            self.str_avg_val_main = StyledString(
                ave_score_split[0], 'H', 72
            )
            self.str_avg_val_suf = StyledString(
                "." + ave_score_split[1], 'H', 72,
                font_color=(0, 0, 0, 64)
            )
        else:
            self.str_avg_header, self.str_avg_val_main, self.str_avg_val_suf = None, None, None

        verdict_prop_split = format(verdict_prop * 100, '.2f').split('.')
        self.str_prop_header = StyledString(
            verdict_prop_title, 'B', 36, padding_bottom=16
        )
        self.str_prop_val_main = StyledString(
            verdict_prop_split[0], 'H', 72
        )
        self.str_prop_val_suf = StyledString(
            "." + verdict_prop_split[1], 'H', 72,
            font_color=(0, 0, 0, 64), padding_bottom=(16 if has_verdict_data else 0)
        )

        if has_verdict_data:
            verdict_detail = self._pack_verdict_detail(verdict_data)
            self.str_verdict_detail = StyledString(
                f'收到 {users_submitted} 个人的提交，其中包含 {verdict_detail}', 'M', 28,
                font_color=(0, 0, 0, 136)
            )
        else:
            self.str_verdict_detail = None

    def render(self, img: pixie.Image, x: int, y: int) -> int:
        current_x, current_y = x, y

        current_y = draw_text(img, self.str_total_header, x, current_y)
        draw_text(img, self.str_total_val, x, current_y)
        current_x += max(calculate_width(self.str_total_header),
                         calculate_width(self.str_total_val)) + 132
        current_y = y

        if self.str_avg_header:
            current_y = draw_text(img, self.str_avg_header, current_x, current_y)
            draw_text(img, self.str_avg_val_main, current_x, current_y)
            draw_text(img, self.str_avg_val_suf,
                      current_x + calculate_width(self.str_avg_val_main), current_y)
            current_x += max(calculate_width(self.str_avg_header),
                             calculate_width([self.str_avg_val_main, self.str_avg_val_suf])) + 132
            current_y = y

        current_y = draw_text(img, self.str_prop_header, current_x, current_y)
        draw_text(img, self.str_prop_val_main, current_x, current_y)
        current_y = draw_text(img, self.str_prop_val_suf,
                              current_x + calculate_width(self.str_prop_val_main), current_y)

        if self.str_verdict_detail:
            current_y = draw_text(img, self.str_verdict_detail, x, current_y)

        return current_y

    def get_height(self):
        return calculate_height([self.str_total_header, self.str_total_val,
                                 self.str_verdict_detail])


class _HistogramSection(RenderableSection):

    def __init__(self, config: Config, render_material: dict):
        super().__init__(config)
        self._outline_paint = pixie.Paint(pixie.SOLID_PAINT)
        self._main_tile_paint = pixie.Paint(pixie.SOLID_PAINT)
        self._sub_tile_paint = pixie.Paint(pixie.SOLID_PAINT)
        self._outline_paint.color = tuple_to_color((0, 0, 0, 32))
        self._main_tile_paint.color = tuple_to_color((0, 0, 0, 26))
        self._sub_tile_paint.color = tuple_to_color((0, 0, 0, 22))

        self.section_render_material = render_material

    def render(self, img: pixie.Image, x: int, y: int) -> int:
        current_x, current_y = x, y
        tile_full_height = _HISTOGRAM_TILE_BASE_HEIGHT + _HISTOGRAM_TILE_STRETCH_HEIGHT
        current_y += 8

        # 绘制左半边框
        draw_rect(img, self._outline_paint, Loc(current_x, current_y, 24, 4))
        draw_rect(img, self._outline_paint, Loc(current_x, current_y + 4, 4, 20))
        draw_rect(img, self._outline_paint, Loc(current_x, current_y + 260, 24, 4))
        draw_rect(img, self._outline_paint, Loc(current_x, current_y + 240, 4, 20))
        current_x += 26 - (22 + 14)

        for item in self.section_render_material:
            current_x += 22 + 14
            tile_height = (_HISTOGRAM_TILE_BASE_HEIGHT +
                           _HISTOGRAM_TILE_STRETCH_HEIGHT * item['hot_prop'])
            sub_tile_height = (_HISTOGRAM_TILE_BASE_HEIGHT +
                               _HISTOGRAM_TILE_STRETCH_HEIGHT * item['hot_prop'] * item['ac_prop'])

            draw_rect(img, self._main_tile_paint, Loc(
                current_x, current_y + 24 + tile_full_height - tile_height, 22, tile_height
            ), 22)
            draw_rect(img, self._sub_tile_paint, Loc(
                current_x, current_y + 24 + tile_full_height - sub_tile_height, 22, sub_tile_height
            ), 22)

        # 绘制右半边框
        draw_rect(img, self._outline_paint, Loc(current_x + 24, current_y, 24, 4))
        draw_rect(img, self._outline_paint, Loc(current_x + 44, current_y + 4, 4, 20))
        draw_rect(img, self._outline_paint, Loc(current_x + 24, current_y + 260, 24, 4))
        draw_rect(img, self._outline_paint, Loc(current_x + 44, current_y + 240, 4, 20))

        current_y += tile_full_height + 24 + 8
        return current_y

    def get_height(self):
        return _HISTOGRAM_TILE_BASE_HEIGHT + _HISTOGRAM_TILE_STRETCH_HEIGHT + 24 + 8 * 2


class _HourlyDistributionSection(RenderableSection):

    @classmethod
    def _pack_hourly_detail(cls, hourly_data: dict) -> dict:
        hourly_detail = {'distribution': [], 'hot_time': 0, 'hot_count': 0, 'hot_ac': 0.0}
        if len(hourly_data) == 0:
            return hourly_detail

        max_hourly_submit = max(hourly[1] for (time, hourly) in hourly_data.items())
        for time, hourly in hourly_data.items():
            hourly_detail['distribution'].append({
                'hot_prop': hourly[1] / max_hourly_submit,  # 这个用来画柱状图
                'ac_prop': hourly[0]
            })
            if hourly[1] == max_hourly_submit:
                hourly_detail['hot_time'] = int(time)
                hourly_detail['hot_count'] = hourly[1]
                hourly_detail['hot_ac'] = max(hourly_detail['hot_ac'], hourly[0])

        return hourly_detail

    def __init__(self, config: Config, hourly_data: dict):
        super().__init__(config)

        hourly_detail = self._pack_hourly_detail(hourly_data)
        hourly_text = "" if len(hourly_data) == 0 else (
            f'提交高峰时段为 {hourly_detail["hot_time"]:02d}:00 - {hourly_detail["hot_time"]:02d}:59. '
            f'在 {hourly_detail["hot_count"]} 份提交中，通过率为 {hourly_detail["hot_ac"] * 100:.2f}%.')

        self.str_header = StyledString(
            "提交时间分布", 'B', 36, padding_bottom=24
        )
        self.str_hint = StyledString(
            hourly_text, 'M', 28, font_color=(0, 0, 0, 136)
        )
        self.section_histogram = _HistogramSection(config, hourly_detail['distribution'])

    def render(self, img: pixie.Image, x: int, y: int) -> int:
        current_x, current_y = x, y
        current_y = draw_text(img, self.str_header, current_x, current_y)

        current_y = self.section_histogram.render(img, current_x, current_y)
        current_y += 40

        current_y = draw_text(img, self.str_hint, current_x, current_y)
        return current_y

    def get_height(self):
        return (calculate_height([self.str_header, self.str_hint]) +
                self.section_histogram.get_height() + 40)


class _CopyrightSection(RenderableSection):

    def __init__(self, config: Config, gradient_color_name: str):
        super().__init__(config)
        self.str_tips_title = StyledString(
            "Tips:", 'H', 36, padding_bottom=64, font_color=(0, 0, 0, 208)
        )
        self.str_tips_detail = StyledString(
            rand_tips(config), 'M', 28, line_multiplier=1.32,
            max_width=(_CONTENT_WIDTH - _SIDE_PADDING -  # 考虑右边界，不然画出去了
                       calculate_width(self.str_tips_title) - 12 - 48),
            padding_bottom=64, font_color=(0, 0, 0, 208)
        )
        self.str_generator = StyledString(
            "Peeper Board Generator", 'H', 36, font_color=(0, 0, 0, 208)
        )
        self.str_version = StyledString(
            VERSION_INFO, 'B', 20, font_color=(0, 0, 0, 208), padding_bottom=24
        )
        self.str_generator_info = StyledString(
            f'Generated at {datetime.now().strftime("%Y/%m/%d %H:%M:%S")}.\n'
            f'From {config.get_config()["board_name"]}.\n'
            f'{gradient_color_name}.', 'B', 20, line_multiplier=1.32, font_color=(0, 0, 0, 136)
        )

    def render(self, img: pixie.Image, x: int, y: int) -> int:
        current_x, current_y = x, y

        draw_text(img, self.str_tips_title, current_x, current_y)
        current_y = draw_text(img, self.str_tips_detail,
                              current_x + calculate_width(self.str_tips_title) + 12,
                              current_y + 8)
        draw_text(img, self.str_generator, current_x, current_y)

        current_x += calculate_width(self.str_generator) + 12
        current_y += 16
        current_y = draw_text(img, self.str_version, current_x, current_y)
        current_x = x

        draw_text(img, self.str_generator_info, current_x, current_y)

        return current_y

    def get_height(self):
        return calculate_height([self.str_tips_detail, self.str_generator, self.str_generator_info])


class MiscBoardGenerator(Renderer):

    def __init__(self, config: Config, board_type: str, img_path: str, verdict: str = "Accepted",
                 separate_columns: bool = False):
        super().__init__(config)
        self._today = load_json(config, False)
        self._separate_columns = separate_columns
        self._gradient_color = pick_gradient_color()
        eng_full_name = (f'{get_date_string(board_type == "full", ".")}  '
                         f'{config.get_config()["board_name"]} Rank List')

        self.section_copyright = _CopyrightSection(config, self._gradient_color.name)

        if board_type == "full":  # 对于 full 榜单的图形逻辑
            try:
                self._yesterday = load_json(config, True)
            except FileNotFoundError:
                logging.error("未检测到昨日榜单文件，请改用--now参数生成今日榜单")
                sys.exit(1)
            self._board = generate_board_data(self._yesterday.submissions, verdict)
            self.section_title = _TitleSection(
                config, self._gradient_color.color_list[0], img_path,
                "昨日卷王天梯榜", eng_full_name
            )
            self._collect_full_sections()
        else:  # if board_type == "now"  对于 now 榜单的图形逻辑
            alias = {val: key for key, val in ALIAS_MAP.items()}
            self._verdict = verdict
            self._verdict_alias = alias[verdict]
            if self._verdict == "Accepted":
                self.section_title = _TitleSection(
                    config, self._gradient_color.color_list[0], img_path,
                    "今日当前提交榜单", eng_full_name
                )
                self._board = generate_board_data(self._today.submissions, self._verdict)
                self._collect_now_sections()
            else:
                self.section_title = _TitleSection(
                    config, self._gradient_color.color_list[0], img_path,
                    f"今日当前{self._verdict_alias}榜单", eng_full_name
                )
                self._board = generate_board_data(self._today.submissions, self._verdict)
                self._collect_verdict_sections()


    def _collect_full_sections(self):
        rank_data = _pack_rank_data(self._today.rankings, 10,
                                    self.config.get_config()['show_unrated'])
        has_ac_submission = len(
            [s for s in self._yesterday.submissions if s.verdict == "Accepted"]
        ) > 0

        section_submission_none = _SimpleTextSection(self.config, "昨日无AC提交", "记录为空")
        section_ranking_none = _SimpleTextSection(self.config, "当前排行榜为空", "暂无排行")
        is_parallel = _check_parallel_play_of_the_oj(self._board.total_board)
        parallel_time = (datetime.fromtimestamp(self._board.total_board[0]["Accepted"][0])
                         .strftime("%H:%M:%S")) if len(self._board.total_board) > 0 else None
        parallel_text = f'于 {parallel_time} 率先通过，成为卷王中的卷王'
        section_play_of_the_oj = _SimpleTextSection(
            self.config, "昨日卷王", self._board.play_of_the_oj,
            parallel_text if is_parallel else None
        )

        section_yesterday_top_5 = _RankSection(
            self.config, "过题数榜单", "昨日过题数", self._board.top_five,
            top_count=5, separate_columns=self._separate_columns
        )
        section_submit_detail = _SubmitDetailSection(
            self.config, self._board.total_submits, self._board.ac_rate,
            self._board.users_submitted, self._board.verdict_data.get("verdicts"),
            avg_score=self._board.avg_score
        )
        section_hourly_distribution = _HourlyDistributionSection(
            self.config, self._board.hourly_data
        )

        first_ac_time = datetime.fromtimestamp(self._board.first_ac.at).strftime("%H:%M:%S")
        first_ac_text = f'在 {first_ac_time} 提交了 {self._board.first_ac.problem_name} 并通过.'
        section_first_ac = _SimpleTextSection(
            self.config, "昨日最速通过", self._board.first_ac.user.name, first_ac_text
        )
        section_popular_problem = _SimpleTextSection(
            self.config, "昨日最受欢迎的题目",self._board.popular_problem[0],
            f'共有 {self._board.popular_problem[1]} 个人提交本题'
        )
        section_total_rank_top_10 = _RankSection(
            self.config, "训练榜单", "题数排名", rank_data,
            top_count=10, separate_columns=self._separate_columns
        )
        section_yesterday_full = _RankSection(
            self.config, "完整榜单", "昨日 OJ 总榜", self._board.total_board,
            separate_columns=self._separate_columns
        )

        section_content: list[RenderableSection] = []
        if not has_ac_submission:
            section_content.append(section_submission_none)
        else:
            section_content.extend([
                section_play_of_the_oj, section_yesterday_top_5,
                RenderableSectionBundle(
                    self.config, [section_submit_detail, section_hourly_distribution],
                    _SECTION_PADDING
                ), section_first_ac, section_popular_problem
            ])

        section_content.append(section_ranking_none if len(rank_data) == 0 else
                               section_total_rank_top_10)
        if has_ac_submission:
            section_content.append(section_yesterday_full)

        self.section_content = MultiColumnRenderableSection(
            self.config, section_content, _CONTENT_WIDTH, _SECTION_PADDING, _COLUMN_PADDING
        )

    def _collect_now_sections(self):
        rank_data = _pack_rank_data(self._today.rankings, 5,
                                    self.config.get_config()['show_unrated'])
        has_ac_submission = len([
            s for s in self._today.submissions if s.verdict == self._verdict
        ]) > 0

        section_submission_none = _SimpleTextSection(
            self.config, "记录为空", f"今日无{self._verdict_alias}提交"
        )
        section_ranking_none = _SimpleTextSection(
            self.config, "暂无排行", "当前排行榜为空"
        )
        section_today_tops = _RankSection(
            self.config, "过题数榜单", "今日过题数",
            self._board.total_board, self._verdict,
            separate_columns=self._separate_columns
        )
        section_submit_detail = _SubmitDetailSection(
            self.config, self._board.total_submits, self._board.ac_rate,
            self._board.users_submitted, self._board.verdict_data.get("verdicts"),
            avg_score=self._board.avg_score
        )
        section_hourly_distribution = _HourlyDistributionSection(
            self.config, self._board.hourly_data
        )

        first_ac_time = datetime.fromtimestamp(self._board.first_ac.at).strftime("%H:%M:%S")
        first_ac_text = f'在 {first_ac_time} 提交了 {self._board.first_ac.problem_name} 并通过.'
        section_first_ac = _SimpleTextSection(
            self.config, "今日最速通过", self._board.first_ac.user.name, first_ac_text
        )
        section_total_rank_top_5 = _RankSection(
            self.config, "训练榜单", "题数排名",
            rank_data, self._verdict, top_count=5,
            hint='为存在"重复提交往日已AC的题目"条件下的过题数理论值',
            separate_columns=self._separate_columns
        )

        section_content: list[RenderableSection] = []
        if not has_ac_submission:
            section_content.append(section_submission_none)
        else:
            section_content.extend([
                section_today_tops,
                RenderableSectionBundle(
                    self.config, [section_submit_detail, section_hourly_distribution],
                    _SECTION_PADDING
                ), section_first_ac
            ])

        section_content.append(section_ranking_none if len(rank_data) == 0 else
                               section_total_rank_top_5)

        self.section_content = MultiColumnRenderableSection(
            self.config, section_content, _CONTENT_WIDTH, _SECTION_PADDING, _COLUMN_PADDING
        )

    def _collect_verdict_sections(self):
        rank_data = _pack_verdict_rank_data(
            rank_by_verdict([s for s in self._today.submissions if s.verdict == self._verdict])
            .get(self._verdict)  # {username: submissionCnt}
            , self._verdict, lim=10)

        section_ranking_none = _SimpleTextSection(
            self.config, "暂无排行", "当前排行榜为空"
        )
        prop_val = (0.0 if self._board.total_submits == 0 else
                    (sum(item[self._verdict][1] for item in self._board.total_board) /
                     self._board.total_submits))
        section_submit_detail = _SubmitDetailSection(
            self.config, self._board.total_submits, prop_val,
            verdict_prop_title=f"{self._verdict} 占比"
        )
        section_today_top_10 = _RankSection(
            self.config, "分类型提交榜单", f"{self._verdict_alias} 排行榜",
            rank_data, self._verdict,
            top_count=10, separate_columns=self._separate_columns
        )

        section_content: list[RenderableSection] = []
        if len(rank_data) == 0:
            section_content.append(section_ranking_none)
        else:
            section_content.extend([section_submit_detail, section_today_top_10])

        self.section_content = MultiColumnRenderableSection(
            self.config, section_content, _CONTENT_WIDTH, _SECTION_PADDING, _COLUMN_PADDING
        )

    def render(self) -> pixie.Image:
        render_sections = [self.section_title, self.section_content, self.section_copyright]
        max_column = max(section.get_columns() for section in render_sections)

        width, height = (_CONTENT_WIDTH * max_column + _COLUMN_PADDING * (max_column - 1),
                         sum(section.get_height() for section in render_sections) +
                         _SECTION_PADDING * (len(render_sections) - 1) +
                         _TOP_PADDING + _BOTTOM_PADDING)

        img = pixie.Image(width + 64, height + 64)
        img.fill(tuple_to_color((0, 0, 0)))  # 填充黑色背景

        draw_gradient_rect(img, Loc(32, 32, width, height), self._gradient_color,
                           GradientDirection.DIAGONAL_LEFT_TO_RIGHT, 96)
        draw_mask_rect(img, Loc(32, 32, width, height), (255, 255, 255, 178), 96)

        current_x, current_y = _SIDE_PADDING, _TOP_PADDING - _SECTION_PADDING

        for section in render_sections:
            current_y += _SECTION_PADDING
            current_y = section.render(img, current_x, current_y)

        _make_watermark(img, width, height)

        return img
