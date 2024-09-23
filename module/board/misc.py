import logging
import sys
from abc import abstractmethod

from datetime import datetime

from pixie import pixie, Image, Color, Paint

from module.ImgConvert import StyledString, ImgConvert
from module.config import Config
from module.structures import SubmissionData, RankingData
from module.submission import rank_by_verdict, get_first_ac, classify_by_verdict, get_hourly_submissions, \
    get_most_popular_problem, count_users_submitted
from module.utils import load_json, get_date_string
from module.verdict import ALIAS_MAP


class MiscBoard:

    def __init__(self, play_of_the_oj: str, top_five: list[dict], total_board: list[dict], total_submits: int,
                 first_ac: SubmissionData, verdict_data: dict, avg_score: float, ac_rate: float, hourly_data: dict,
                 popular_problem: tuple[str, int], users_submitted: int):
        self.play_of_the_oj = play_of_the_oj
        self.top_five = top_five
        self.total_board = total_board
        self.total_submits = total_submits
        self.first_ac = first_ac
        self.verdict_data = verdict_data
        self.avg_score = avg_score
        self.ac_rate = ac_rate
        self.hourly_data = hourly_data
        self.popular_problem = popular_problem
        self.users_submitted = users_submitted


def generate_board_data(submissions: list[SubmissionData], verdict: str) -> MiscBoard:
    result = {}

    verdict_desc = rank_by_verdict(submissions).get(verdict)
    if verdict_desc is None:
        return MiscBoard("", [], pack_verdict_rank_data(None, verdict),
                         0, get_first_ac(submissions), {}, 0, 0, {},
                         ("", 0), 0)

    result['play_of_the_oj'] = next(iter(verdict_desc))  # 昨日
    total_board = pack_verdict_rank_data(verdict_desc, verdict)
    result['top_five'] = slice_ranking_data(total_board, 5)  # 昨日
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
                      first_ac=result['first_ac'], verdict_data=result['verdict_data'], avg_score=result['avg_score'],
                      ac_rate=result['ac_rate'], hourly_data=result['hourly_data'],
                      popular_problem=result['popular_problem'],
                      users_submitted=result['users_submitted'])
    return board


def pack_ranking_list(config: Config, tops: list[dict], key: str) -> list[dict]:
    if len(tops) == 0:
        return []
    max_val = tops[0][key][-1] if isinstance(tops[0][key], tuple) else tops[0][key]  # 以key作为排名依据

    ranking_list = []

    for top in tops:
        unrated = True if top.get('unrated') else False
        cnt = top[key][-1] if isinstance(top[key], tuple) else top[key]
        record = {'progress': int(cnt) / int(max_val),
                  'unrated': unrated,
                  'rank': StyledString(config, "*" if unrated else str(top['rank']), 'H', 64),
                  'user': StyledString(config, str(top['user']), 'B', 36),
                  'val': StyledString(config, str(cnt), 'H', 36)}
        ranking_list.append(record)

    return ranking_list


def pack_verdict_detail(verdict_data: dict) -> str:
    if verdict_data is None:
        return ""

    alias = {val: key for key, val in ALIAS_MAP.items()}
    verdict_detail = ''

    for (key, val) in alias.items():
        if key not in verdict_data:
            continue

        if len(verdict_detail) > 0:
            verdict_detail += ', '
        verdict_detail += str(verdict_data[key]) + val

    return verdict_detail


def pack_hourly_detail(hourly_data: dict) -> dict:
    if len(hourly_data) == 0:
        return {}

    max_hourly_submit = max(hourly[1] for (time, hourly) in hourly_data.items())
    hourly_detail: dict[str, any] = {'distribution': [], 'hot_time': 0, 'hot_count': 0, 'hot_ac': 0.0}

    for (time, hourly) in hourly_data.items():
        hourly_detail['distribution'].append({'hot_prop': hourly[1] / max_hourly_submit,  # 这个用来画柱状图
                                              'ac_prop': hourly[0]})
        if hourly[1] == max_hourly_submit:
            hourly_detail['hot_time'] = int(time)
            hourly_detail['hot_count'] = hourly[1]
            hourly_detail['hot_ac'] = max(hourly_detail['hot_ac'], hourly[0])

    return hourly_detail


def pack_rank_data(rank: list[RankingData]) -> list[dict]:
    # 封装一下
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
    return rank_data


# 处理一下有排名并列时直接切片导致的问题
def slice_ranking_data(rank: list[dict], lim: int) -> list[dict]:
    if len(rank) == 0:
        return []

    max_rank = min(lim, rank[len(rank) - 1]['rank'])
    return [ranking_data for ranking_data in rank if ranking_data['rank'] <= max_rank]


def pack_verdict_rank_data(verdict_desc: dict | None, verdict: str) -> list[dict]:
    if verdict_desc is None:
        return [{"user": "", f"{verdict}": (0, 1), "rank": -1}]

    total_board = []
    rank = 1
    for i, (user, verdict_cnt) in enumerate(verdict_desc.items()):
        if i > 0 and verdict_cnt[1] != verdict_desc[list(verdict_desc.keys())[i - 1]][1]:
            rank = i + 1
        total_board.append({"user": user, f"{verdict}": verdict_cnt, "rank": rank})
    return total_board


class Section:
    def __init__(self, config: Config):
        self.config = config

    @abstractmethod
    def draw(self, output_img: Image, x: int, y: int) -> int:
        pass

    @abstractmethod
    def get_height(self):
        pass


class RankSection(Section):

    def __init__(self, config: Config,
                 title: str, subtitle: str, rank_data: list[dict], hint: str = None, tops: int = -1):
        super().__init__(config)
        self.title = StyledString(config, title, "H", 72)
        self.subtitle = StyledString(config, subtitle, "B", 36)
        self.rank_data = rank_data
        self.hint = StyledString(config, hint, 'M', 28, font_color=(0, 0, 0, 136 / 255)) if hint else None
        self.tops = StyledString(config, f"Top {tops}th", "H", 48) if tops != -1 else None

    def draw(self, output_img: Image, x: int, y: int) -> int:
        current_y = y

        current_y = draw_text(output_img, self.subtitle, 16, current_y)
        current_y = draw_text(output_img, self.title, 16 if self.hint else 32, current_y)
        if self.tops:
            current_y -= 86 if self.hint else 102
            current_y = draw_text(output_img, self.tops, 16 if self.hint else 32, current_y,
                                  x=ImgConvert.calculate_string_width(self.title) + 128 + 28)
        if self.hint:
            current_y = draw_text(output_img, self.hint, 32, current_y)

        pre_rank = ""
        for rank in self.rank_data:
            if rank['unrated'] and not self.config.get_config()["show_unrated"]:  # 不显示的话不画
                continue
            progress_len = 360 + 440 * rank['progress']
            line_y = current_y
            current_x = 128 + 32
            same_rank = False
            if rank['unrated']:
                rank['rank'].set_font_color(Color(0, 0, 0, 100 / 255))
            else:
                same_rank = rank['rank'].content == pre_rank
                rank['rank'].set_font_color(Color(0, 0, 0, 0 if same_rank else 1))
                pre_rank = rank['rank'].content
            current_y = line_y + 8
            draw_text(output_img, rank['rank'], 12, current_y, x=current_x)

            current_x += ImgConvert.calculate_string_width(rank['rank']) + 28
            current_y = line_y + 40
            rank['user'].set_font_color(Color(0, 0, 0, 100 / 255 if rank['unrated'] else 1))
            draw_text(output_img, rank['user'], 12, current_y, x=current_x)

            current_x = max(progress_len + 128, current_x + ImgConvert.calculate_string_width(rank['user'])) + 36
            current_y = line_y + 40
            rank['val'].set_font_color(Color(0, 0, 0, 100 / 255 if rank['unrated'] else 1))
            current_y = draw_text(output_img, rank['val'], 32, current_y, x=current_x)

            tile_colors = [
                Color(0, 0, 0, (12 if rank['unrated'] else (10 if same_rank else 18)) / 255),
                Color(0, 0, 0, (15 if rank['unrated'] else (18 if same_rank else 28)) / 255),
                Color(0, 0, 0, (18 if rank['unrated'] else 32) / 255)
            ]
            tile_positions = [0.0, 0.5, 1.0]

            draw_horizontal_gradient_round_rect(output_img, 128, line_y + 38, progress_len, 52,
                                                tile_colors, tile_positions)

        return current_y - 32

    def get_height(self):
        height = ImgConvert.calculate_height([self.title, self.subtitle, self.hint]) + 48
        if self.hint:
            height += 32
        for item in self.rank_data:
            if item['unrated'] and not self.config.get_config()["show_unrated"]:  # 不显示的话不计算unrated的高度
                continue
            height += item['user'].height + 40 + 32
        height -= 32
        return height


class SubmitDetailSection(Section):

    def __init__(self, config: Config, total_submits: int, verdict_prop: float, users_submitted: int = -1,
                 verdict_detail: str = None, verdict_prop_title: str = "提交通过率", avg_score: float = -1):
        super().__init__(config)
        self.total_submits_title = StyledString(config, "提交总数", 'B', 36)
        self.total_submits_detail = StyledString(config, str(total_submits), 'H', 72)

        if avg_score != -1:
            ave_score_split = format(avg_score, '.2f').split(".")  # 分割小数
            self.ave_score_title = StyledString(config, "提交平均分", 'B', 36)
            self.ave_score_detail_main = StyledString(config, ave_score_split[0], 'H', 72)
            self.ave_score_detail_sub = StyledString(config, "." + ave_score_split[1], 'H', 72,
                                                     font_color=(0, 0, 0, 64 / 255))  # 有傻逼写了0
        else:
            self.ave_score_title, self.ave_score_detail_main, self.ave_score_detail_sub = None, None, None

        verdict_prop_split = format(verdict_prop * 100, '.2f').split(".")
        self.verdict_prop_title = StyledString(config, verdict_prop_title, 'B', 36)
        self.verdict_prop_detail_main = StyledString(config, verdict_prop_split[0], 'H', 72)
        self.verdict_prop_detail_sub = StyledString(config, "." + verdict_prop_split[1], 'H', 72,
                                                    font_color=(0, 0, 0, 64 / 255))

        if users_submitted != -1 and verdict_detail is not None:
            self.verdict_detail = StyledString(config, f'收到 {users_submitted} 个人的提交，其中包含 {verdict_detail}',
                                               'M', 28, font_color=(0, 0, 0, 136 / 255))
        else:
            self.verdict_detail = None

    def draw(self, output_img: Image, x: int, y: int) -> int:
        current_y = y

        current_y = draw_text(output_img, self.total_submits_title, 16, current_y)
        draw_text(output_img, self.total_submits_detail, 16 if self.verdict_detail else 0, current_y)
        current_y = y  # 保持在同一行
        total_submits_width = max(
            ImgConvert.calculate_string_width(self.total_submits_title),
            ImgConvert.calculate_string_width(self.total_submits_detail)
        ) + 132

        if self.ave_score_title:
            current_y = draw_text(output_img, self.ave_score_title, 16, current_y,
                                  x=total_submits_width + 128)
            draw_text(output_img, self.ave_score_detail_main, 0, current_y, x=total_submits_width + 128)
            draw_text(output_img, self.ave_score_detail_sub, 16 if self.verdict_detail else 0, current_y,
                      x=ImgConvert.calculate_string_width(self.ave_score_detail_main) + total_submits_width + 128)
            current_y = y

            total_submits_width += max(
                ImgConvert.calculate_string_width(self.ave_score_title),
                ImgConvert.calculate_string_width(self.ave_score_detail_main) + ImgConvert.calculate_string_width(
                    self.ave_score_detail_sub)
            ) + 132

        current_y = draw_text(output_img, self.verdict_prop_title, 16, current_y, x=total_submits_width + 128)
        draw_text(output_img, self.verdict_prop_detail_main, 0, current_y, x=total_submits_width + 128)
        current_y = draw_text(output_img, self.verdict_prop_detail_sub, 16 if self.verdict_detail else 0, current_y,
                              x=ImgConvert.calculate_string_width(
                                  self.verdict_prop_detail_main) + total_submits_width + 128)

        if self.verdict_detail:
            current_y = draw_text(output_img, self.verdict_detail, 0, current_y)

        return current_y

    def get_height(self):
        return (ImgConvert.calculate_height([self.total_submits_title, self.total_submits_detail, self.verdict_detail])
                + (32 if self.verdict_detail else 16))


class HourlyDistributionSection(Section):

    def __init__(self, config: Config, hourly_data: dict):
        super().__init__(config)

        hourly_text = "" if len(hourly_data) == 0 else (
            f'提交高峰时段为 {"{:02d}:00 - {:02d}:59".format(hourly_data["hot_time"], hourly_data["hot_time"])}. '
            f'在 {hourly_data["hot_count"]} 份提交中，通过率为 {"{:.2f}".format(hourly_data["hot_ac"] * 100)}%.')

        self.hourly_title = StyledString(config, "提交时间分布", 'B', 36)
        self.hourly_data = hourly_data
        self.hourly_detail = StyledString(config, hourly_text, 'M', 28,
                                          font_color=(0, 0, 0, 136 / 255))

    def draw(self, output_img: Image, x: int, y: int) -> int:
        current_y = y
        current_y = draw_text(output_img, self.hourly_title, 24, current_y)
        current_y = draw_vertical_graph(output_img, self.hourly_data, 40, current_y)
        current_y = draw_text(output_img, self.hourly_detail, 0, current_y)
        return current_y

    def get_height(self):
        return (ImgConvert.calculate_height([self.hourly_title, self.hourly_detail])
                + 244  # 图表的高度
                + 40)


class SimpleTextSection(Section):

    def __init__(self, config: Config, title: str, subtitle: str, hint: str = None):
        super().__init__(config)
        self.title = StyledString(config, title, 'H', 72)
        self.subtitle = StyledString(config, subtitle, 'B', 36)
        self.hint = StyledString(config, hint, 'M', 28,
                                 font_color=(0, 0, 0, 136 / 255)) if hint else None

    def draw(self, output_img: Image, x: int, y: int) -> int:
        current_y = y
        current_y = draw_text(output_img, self.subtitle, 16, current_y)
        current_y = draw_text(output_img, self.title, 16 if self.hint else 0, current_y)
        if self.hint:
            current_y = draw_text(output_img, self.hint, 0, current_y)
        return current_y

    def get_height(self):
        return (ImgConvert.calculate_height([self.subtitle, self.title, self.hint])
                + (32 if self.hint else 16))


class CopyrightSection(Section):
    def __init__(self, config: Config):
        super().__init__(config)
        self.module_name = StyledString(config, "Peeper Board Generator", 'H', 36,
                                        font_color=(0, 0, 0, 208 / 255))
        self.module_version = StyledString(config, "v1.2.0", 'B', 20,
                                           font_color=(0, 0, 0, 208 / 255))  # todo
        self.generation_info = StyledString(config, f'Generated at {datetime.now().strftime("%Y/%m/%d %H:%M:%S")}.\n'
                                                    f'From {config.get_config()["board_name"]}.', 'B', 20,
                                            line_multiplier=1.32, font_color=(0, 0, 0, 136 / 255))

    def draw(self, output_img: Image, x: int, y: int) -> int:
        current_y = y
        draw_text(output_img, self.module_name, 16, current_y)
        current_y = draw_text(output_img, self.module_version, 24, current_y + 16,
                              x=ImgConvert.calculate_string_width(self.module_name) + 12 + 128)
        current_y = draw_text(output_img, self.generation_info, 0, current_y)
        return current_y

    def get_height(self):
        return (ImgConvert.calculate_height([self.module_name, self.generation_info])
                + 24)


def draw_text(image: Image, content: StyledString, padding_bottom: int, current_y: int, x: int = 128) -> int:
    ImgConvert.draw_string(image, content, x, current_y)
    return current_y + ImgConvert.calculate_height([content]) + padding_bottom


# 这个java自带 (Color.darker)
def darken_color(color: Color) -> Color:
    return Color(color.r * 0.7, color.g * 0.7, color.b * 0.7, color.a)


def draw_rect(image: Image, paint: Paint, x: int, y: int, width: int, height: int):
    ctx = image.new_context()
    ctx.fill_style = paint
    ctx.rect(x, y, width, height)
    ctx.fill()


def draw_round_rect(image: Image, paint: Paint, x: int, y: int, width: int, height: int, round_size: float):
    ctx = image.new_context()
    ctx.fill_style = paint
    ctx.rounded_rect(x, y, width, height, round_size, round_size, round_size, round_size)
    ctx.fill()


def draw_background(image: Image, width: int, height: int, colors: list[str], positions: list[float]):
    image.fill(pixie.Color(0, 0, 0, 1))  # 填充黑色背景
    paint = Paint(pixie.LINEAR_GRADIENT_PAINT if len(colors) == 2 else pixie.ANGULAR_GRADIENT_PAINT)  # 准备渐变色画笔
    paint_mask = Paint(pixie.SOLID_PAINT)  # 准备蒙版画笔
    paint_mask.color = pixie.Color(1, 1, 1, 0.7)  # 设置蒙版颜色
    for i in range(len(colors)):
        color = pixie.parse_color(colors[i])
        paint.gradient_handle_positions.append(pixie.Vector2(32 + (width - 64) * positions[i],
                                                             32 + (height - 64) * positions[i]))
        paint.gradient_stops.append(pixie.ColorStop(color, i))
    draw_round_rect(image, paint, 32, 32, width - 64, height - 64, 96)
    mask = pixie.Image(width, height)
    draw_round_rect(mask, paint_mask, 32, 32, width - 64, height - 64, 96)
    image.draw(mask, blend_mode=pixie.NORMAL_BLEND)


def draw_basic_content(config: Config, image: Image, total_height: int, title: StyledString,
                       subtitle: StyledString, current_y: int, logo_path: str) -> int:
    current_gradient, gradient_positions = ImgConvert.GradientColors.generate_gradient(config)
    # 全部换用pixie
    draw_background(image, 1280, total_height + 336, current_gradient, gradient_positions)
    accent_color = pixie.parse_color(current_gradient[0])
    accent_dark_color = darken_color(darken_color(darken_color(accent_color)))

    logo_tinted = ImgConvert.apply_tint(logo_path, accent_dark_color).resize(140, 140)
    image.draw(logo_tinted, pixie.translate(108, 160))
    title.set_font_color(accent_dark_color)
    current_y = draw_text(image, title, 12, current_y, x=260)
    subtitle.set_font_color(Color(accent_dark_color.r, accent_dark_color.g, accent_dark_color.b, 136 / 255))
    current_y = draw_text(image, subtitle, 108, current_y)

    return current_y


def draw_horizontal_gradient_round_rect(image: Image, x: int, y: int, width: int, height: int,
                                        colors: list[Color], positions: list[float]):
    paint = Paint(pixie.LINEAR_GRADIENT_PAINT if len(colors) == 2 else pixie.RADIAL_GRADIENT_PAINT)  # 准备渐变色画笔
    for i in range(len(colors)):
        paint.gradient_handle_positions.append(pixie.Vector2(x + width * positions[i], y + height / 2))
        paint.gradient_stops.append(pixie.ColorStop(colors[i], i))
    round_size = min(width, height) / 2
    draw_round_rect(image, paint, x, y, width, height, round_size)


def draw_vertical_graph(image: Image, data: dict, padding_bottom: int, current_y: int, x: int = 128) -> int:
    current_x = x + 26
    current_y += 8

    outline_paint = Paint(pixie.SOLID_PAINT)
    outline_paint.color = pixie.Color(0, 0, 0, 32 / 255)

    main_tile_paint = Paint(pixie.SOLID_PAINT)
    main_tile_paint.color = pixie.Color(0, 0, 0, 32 / 255)

    sub_tile_paint = Paint(pixie.SOLID_PAINT)
    sub_tile_paint.color = pixie.Color(0, 0, 0, 16 / 255)

    # 绘制左半边框
    draw_rect(image, outline_paint, 128, current_y, 24, 4)
    draw_rect(image, outline_paint, 128, current_y + 4, 4, 20)
    draw_rect(image, outline_paint, 128, current_y + 240, 24, 4)
    draw_rect(image, outline_paint, 128, current_y + 220, 4, 20)

    for item in data['distribution']:
        progress_len = 24 + 176 * item['hot_prop']
        sub_progress_len = 24 + 176 * item['hot_prop'] * item['ac_prop']
        line_y = current_y + 24

        draw_round_rect(image, main_tile_paint, current_x, line_y + 200 - progress_len, 24, progress_len, 24)
        draw_round_rect(image, sub_tile_paint, current_x, line_y + 200 - sub_progress_len, 24, sub_progress_len, 24)

        current_x += 24 + 16

    current_x -= 24 + 16

    # 绘制右半边框
    draw_rect(image, outline_paint, current_x + 24, current_y, 24, 4)
    draw_rect(image, outline_paint, current_x + 44, current_y + 4, 4, 20)
    draw_rect(image, outline_paint, current_x + 24, current_y + 240, 24, 4)
    draw_rect(image, outline_paint, current_x + 44, current_y + 220, 4, 20)

    return current_y + padding_bottom + 232


def check_parallel_play_of_the_oj(data: list) -> bool:
    top1_cnt = data[0]['Accepted'][1]
    parallel = False
    for i, item in enumerate(data):
        if i == 0:
            continue
        if item['Accepted'][1] == top1_cnt:
            parallel = True
        break

    return parallel


class MiscBoardGenerator:

    @staticmethod
    def generate_image(config: Config, board_type: str,
                       logo_path, verdict: str = "Accepted") -> Image:
        today = load_json(config, False)
        title = StyledString(config, "Unknown Board", 'H', 96)
        eng_full_name = StyledString(config,
                                     f'{get_date_string(board_type == "full", ".")}  '
                                     f'{config.get_config()["board_name"]} Rank List',
                                     'H', 36,
                                     line_multiplier=1.2)
        sections: list[Section] = []  # 各板块
        copyright_section = CopyrightSection(config)

        if board_type == "full":  # 对于 full 榜单的图形逻辑
            title = StyledString(config, "昨日卷王天梯榜", 'H', 96)

            try:
                yesterday = load_json(config, True)
            except FileNotFoundError:
                logging.error("未检测到昨日榜单文件，请改用--now参数生成今日榜单")
                sys.exit(1)
            data = generate_board_data(yesterday.submissions, verdict)
            rank = today.rankings
            rank_data = pack_rank_data(rank)
            has_ac_submission = len([s for s in yesterday.submissions if s.verdict == "Accepted"]) > 0

            submission_none_section = SimpleTextSection(config, "昨日无AC提交", "记录为空")
            ranking_none_section = SimpleTextSection(config, "当前排行榜为空", "暂无排行")

            play_of_the_oj_is_parallel = check_parallel_play_of_the_oj(data.total_board)
            play_of_the_oj_time_text = \
                f'于 {datetime.fromtimestamp(data.total_board[0]["Accepted"][0]).strftime("%H:%M:%S")} 率先通过，成为卷王中的卷王'
            play_of_the_oj_section = SimpleTextSection(config, data.play_of_the_oj, "昨日卷王",
                                                       play_of_the_oj_time_text if play_of_the_oj_is_parallel else None)

            yesterday_top_5_data = pack_ranking_list(config, data.top_five, verdict)
            yesterday_top_5_section = RankSection(config, "昨日过题数", "过题数榜单", yesterday_top_5_data, tops=5)

            submit_detail_section = SubmitDetailSection(config, data.total_submits, data.ac_rate, data.users_submitted,
                                                        pack_verdict_detail(data.verdict_data.get("verdicts")),
                                                        avg_score=data.avg_score)

            hourly_distribution_section = HourlyDistributionSection(config, pack_hourly_detail(data.hourly_data))

            first_ac_text = (f'在 {datetime.fromtimestamp(data.first_ac.at).strftime("%H:%M:%S")} '
                             f'提交了 {data.first_ac.problem_name} 并通过.')
            first_ac_section = SimpleTextSection(config, data.first_ac.user.name, "昨日最速通过", first_ac_text)

            popular_problem_section = SimpleTextSection(config, data.popular_problem[0], "昨日最受欢迎的题目",
                                                        f'共有 {data.popular_problem[1]} 个人提交本题')

            total_rank_top_10 = pack_ranking_list(config, slice_ranking_data(rank_data, 10), verdict)
            total_rank_top_10_section = RankSection(config, "题数排名", "训练榜单", total_rank_top_10, tops=10)

            yesterday_full_detail = pack_ranking_list(config, data.total_board, verdict)
            yesterday_full_section = RankSection(config, "昨日 OJ 总榜", "完整榜单", yesterday_full_detail)

            # 注册板块
            if not has_ac_submission:
                sections.append(submission_none_section)
            else:
                sections.extend([play_of_the_oj_section, yesterday_top_5_section, submit_detail_section,
                                 hourly_distribution_section, first_ac_section, popular_problem_section])

            sections.append(ranking_none_section if len(rank) == 0 else total_rank_top_10_section)

            if has_ac_submission:
                sections.append(yesterday_full_section)

        if board_type == "now":  # 对于 now 榜单的图形逻辑
            alias = {val: key for key, val in ALIAS_MAP.items()}

            submission_none_section = SimpleTextSection(config, f"今日无{alias[verdict]}提交", "记录为空")
            ranking_none_section = SimpleTextSection(config, "当前排行榜为空", "暂无排行")

            if verdict == "Accepted":
                title = StyledString(config, "今日当前提交榜单", 'H', 96)

                data = generate_board_data(today.submissions, verdict)
                rank = today.rankings
                rank_data = pack_rank_data(rank)
                has_ac_submission = len([s for s in today.submissions if s.verdict == verdict]) > 0

                today_tops_detail = pack_ranking_list(config, data.total_board, verdict)
                today_tops_section = RankSection(config, "今日过题数", "过题数榜单", today_tops_detail)

                submit_detail_section = SubmitDetailSection(config, data.total_submits, data.ac_rate,
                                                            data.users_submitted,
                                                            pack_verdict_detail(data.verdict_data.get("verdicts")),
                                                            avg_score=data.avg_score)

                hourly_distribution_section = HourlyDistributionSection(config, pack_hourly_detail(data.hourly_data))

                first_ac_text = (f'在 {datetime.fromtimestamp(data.first_ac.at).strftime("%H:%M:%S")} '
                                 f'提交了 {data.first_ac.problem_name} 并通过.')
                first_ac_section = SimpleTextSection(config, data.first_ac.user.name, "今日最速通过", first_ac_text)

                total_rank_top_5 = pack_ranking_list(config, slice_ranking_data(rank_data, 5), verdict)
                total_rank_top_5_section = RankSection(config, "题数排名", "训练榜单", total_rank_top_5, tops=5,
                                                       hint="为存在\"重复提交往日已AC的题目\"条件下的过题数理论值")

                if not has_ac_submission:
                    sections.append(submission_none_section)
                else:
                    sections.extend([today_tops_section, submit_detail_section, hourly_distribution_section,
                                     first_ac_section])

                sections.append(ranking_none_section if len(rank) == 0 else total_rank_top_5_section)

            else:  # 对于分 verdict 的 now 榜单的图形逻辑
                title = StyledString(config, f"今日当前{alias[verdict]}榜单", 'H', 96)
                data = generate_board_data(today.submissions, verdict)
                rank = (rank_by_verdict([s for s in today.submissions if s.verdict == verdict])
                        .get(verdict))  # { username: submissionCnt}
                rank_data = pack_verdict_rank_data(rank, verdict)

                prop_val = 0.0 if data.total_submits == 0 else (
                        sum(item[verdict][1] for item in data.total_board) / data.total_submits)
                submit_detail_section = SubmitDetailSection(config, data.total_submits, prop_val,
                                                            verdict_prop_title=f"{verdict} 占比")

                today_top_10 = pack_ranking_list(config, slice_ranking_data(rank_data, 10), verdict)
                today_top_10_section = RankSection(config, f"{alias[verdict]} 排行榜", "分类型提交榜单", today_top_10, tops=10)

                if len(rank) == 0:
                    sections.append(ranking_none_section)
                else:
                    sections.extend([submit_detail_section, today_top_10_section])

        sections.append(copyright_section)

        total_height = sum([section.get_height() for section in sections])
        total_height += ImgConvert.calculate_height([title, eng_full_name])
        total_paddings = 108 * len(sections) + 12
        output_img = pixie.Image(1280, total_height + total_paddings + 336)

        current_y = draw_basic_content(config, output_img, total_height + total_paddings,
                                       title, eng_full_name, 168, logo_path)

        for section in sections:
            current_y = section.draw(output_img, 128, current_y) + 108

        return output_img
