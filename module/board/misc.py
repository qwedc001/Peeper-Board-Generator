import logging
import sys

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
    hourly_detail = {'distribution': [], 'hot_time': 0, 'hot_count': 0, 'hot_ac': 0.0}

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


def calculate_height(strings: list[StyledString]) -> int:
    height = 0
    for string in strings:
        height += string.height
    return height


def calculate_ranking_height(config: Config, rankings: list[list[dict]]) -> int:
    height = 0
    for ranking in rankings:
        for item in ranking:
            if item['unrated'] and not config.get_config()["show_unrated"]:  # 不显示的话不计算unrated的高度
                continue
            height += item['user'].height + 40 + 32
        height -= 32
    return height


def draw_text(image: Image, content: StyledString, padding_bottom: int, current_y: int, x: int = 128) -> int:
    ImgConvert.draw_string(image, content, x, current_y)
    return current_y + calculate_height([content]) + padding_bottom


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
    paint = Paint(pixie.LINEAR_GRADIENT_PAINT if len(colors) == 2 else pixie.RADIAL_GRADIENT_PAINT)  # 准备渐变色画笔
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


def draw_basic_content(image: Image, total_height: int, title: StyledString,
                       subtitle: StyledString, current_y: int, logo_path: str) -> int:
    current_gradient, gradient_positions = ImgConvert.GradientColors.generate_gradient()
    # 全部换用pixie
    draw_background(image, 1280, total_height + 300, current_gradient, gradient_positions)
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


def draw_rank_detail(config: Config, image: Image, ranking: list[dict], padding_bottom: int, current_y: int) -> int:
    pre_rank = ""
    for rank in ranking:
        if rank['unrated'] and not config.get_config()["show_unrated"]:  # 不显示的话不画
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
        draw_text(image, rank['rank'], 12, current_y, x=current_x)

        current_x += ImgConvert.calculate_string_width(rank['rank']) + 28
        current_y = line_y + 40
        rank['user'].set_font_color(Color(0, 0, 0, 100 / 255 if rank['unrated'] else 1))
        draw_text(image, rank['user'], 12, current_y, x=current_x)

        current_x = max(progress_len + 128, current_x + ImgConvert.calculate_string_width(rank['user'])) + 36
        current_y = line_y + 40
        rank['val'].set_font_color(Color(0, 0, 0, 100 / 255 if rank['unrated'] else 1))
        current_y = draw_text(image, rank['val'], 32, current_y, x=current_x)

        tile_colors = [  # 这里有问题
            Color(0, 0, 0, (12 if rank['unrated'] else (10 if same_rank else 18)) / 255),
            Color(0, 0, 0, (15 if rank['unrated'] else (18 if same_rank else 28)) / 255),
            Color(0, 0, 0, (18 if rank['unrated'] else 32) / 255)
        ]
        tile_positions = [0.0, 0.5, 1.0]

        draw_horizontal_gradient_round_rect(image, 128, line_y + 38, progress_len, 52, tile_colors, tile_positions)

    return current_y + padding_bottom - 32


def draw_vertical_graph(image: Image, data: dict, padding_bottom: int, current_y: int) -> int:
    current_x = 152
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


def draw_submit_detail(image: Image,
                       total_submits_title: StyledString, total_submits_detail: StyledString,
                       ave_score_title: StyledString, ave_score_detail_main: StyledString,
                       ave_score_detail_sub: StyledString,
                       ac_rate_title: StyledString, ac_rate_detail_main: StyledString, ac_rate_detail_sub: StyledString,
                       verdict_detail: StyledString,
                       hourly_title: StyledString, hourly_data: dict, hourly_detail: StyledString,
                       first_ac_title: StyledString, first_ac_who: StyledString, first_ac_detail: StyledString,
                       current_y: int) -> int:
    begin_y = current_y

    current_y = draw_text(image, total_submits_title, 16, current_y)
    draw_text(image, total_submits_detail, 16, current_y)
    current_y = begin_y
    total_submits_width = max(
        ImgConvert.calculate_string_width(total_submits_title),
        ImgConvert.calculate_string_width(total_submits_detail)
    )

    current_y = draw_text(image, ave_score_title, 16, current_y, x=total_submits_width + 128 + 150)
    # 保持在同一行
    draw_text(image, ave_score_detail_main, 32, current_y, x=total_submits_width + 128 + 150)
    ave_score_detail_sub.set_font_color(Color(0, 0, 0, 64 / 255))
    draw_text(image, ave_score_detail_sub, 16, current_y,
              x=ImgConvert.calculate_string_width(ave_score_detail_main) + total_submits_width + 128 + 150)
    current_y = begin_y

    total_submits_width += max(
        ImgConvert.calculate_string_width(ave_score_title),
        ImgConvert.calculate_string_width(ave_score_detail_main) + ImgConvert.calculate_string_width(
            ave_score_detail_sub)
    )

    current_y = draw_text(image, ac_rate_title, 16, current_y, x=total_submits_width + 128 + 128 + 150)
    draw_text(image, ac_rate_detail_main, 32, current_y, x=total_submits_width + 128 + 128 + 150)
    ac_rate_detail_sub.set_font_color(Color(0, 0, 0, 64 / 255))
    current_y = draw_text(image, ac_rate_detail_sub, 16, current_y,
                          x=ImgConvert.calculate_string_width(
                              ac_rate_detail_main) + total_submits_width + 128 + 128 + 150)

    verdict_detail.set_font_color(Color(0, 0, 0, 136 / 255))
    current_y = draw_text(image, verdict_detail, 108, current_y)

    current_y = draw_text(image, hourly_title, 24, current_y)
    current_y = draw_vertical_graph(image, hourly_data, 40, current_y)
    hourly_detail.set_font_color(Color(0, 0, 0, 136 / 255))
    current_y = draw_text(image, hourly_detail, 108, current_y)

    current_y = draw_text(image, first_ac_title, 16, current_y)
    current_y = draw_text(image, first_ac_who, 16, current_y)
    first_ac_detail.set_font_color(Color(0, 0, 0, 136 / 255))
    current_y = draw_text(image, first_ac_detail, 108, current_y)

    return current_y


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
        eng_full_name = StyledString(config,
                                     f'{get_date_string(board_type == "full", ".")}  '
                                     f'{config.get_config()["board_name"]} Rank List',
                                     'H', 36,
                                     line_multiplier=1.2)
        if board_type == "full":
            title = StyledString(config, "昨日卷王天梯榜", 'H', 96)

            try:
                yesterday = load_json(config, True)
            except FileNotFoundError:
                logging.error("未检测到昨日榜单文件，请改用--now参数生成今日榜单")
                sys.exit(1)
            data = generate_board_data(yesterday.submissions, verdict)
            rank = today.rankings
            # 对于 full 榜单的图形逻辑
            rank_data = pack_rank_data(rank)
            has_ac_submission = len([s for s in yesterday.submissions if s.verdict == "Accepted"]) > 0

            submission_none_subtitle = StyledString(config, "记录为空", 'B', 36)
            submission_none_title = StyledString(config, "昨日无AC提交", 'H', 72)
            ranking_none_subtitle = StyledString(config, "暂无排行", 'B', 36)
            ranking_none_title = StyledString(config, "当前排行榜为空", 'H', 72)

            play_of_the_oj_is_parallel = check_parallel_play_of_the_oj(data.total_board)
            play_of_the_oj_title = StyledString(config, f"昨日卷王", 'B', 36)
            play_of_the_oj = StyledString(config, data.play_of_the_oj, 'H', 72)
            play_of_the_oj_time_text = \
                f'于 {datetime.fromtimestamp(data.total_board[0]["Accepted"][0]).strftime("%H:%M:%S")} 率先通过，成为卷王中的卷王'
            play_of_the_oj_time = StyledString(config, play_of_the_oj_time_text, 'M', 28)

            top_5_subtitle = StyledString(config, "过题数榜单", "B", 36)
            top_5_title = StyledString(config, "昨日过题数", "H", 72)
            top_5_mark = StyledString(config, "Top 5th", "H", 48)
            top_5_detail = pack_ranking_list(config, data.top_five, verdict)

            total_submits_title = StyledString(config, "提交总数", 'B', 36)
            total_submits_detail = StyledString(config, str(data.total_submits), 'H', 72)

            ave_score_split = format(data.avg_score, '.2f').split(".")  # 分割小数

            ave_score_title = StyledString(config, "提交平均分", 'B', 36)
            ave_score_detail_main = StyledString(config, ave_score_split[0], 'H', 72)
            ave_score_detail_sub = StyledString(config, "." + ave_score_split[1], 'H', 72)  # 有傻逼写了0

            ac_rate_split = format(data.ac_rate * 100, '.2f').split(".")

            ac_rate_title = StyledString(config, "提交通过率", 'B', 36)
            ac_rate_detail_main = StyledString(config, ac_rate_split[0], 'H', 72)
            ac_rate_detail_sub = StyledString(config, "." + ac_rate_split[1], 'H', 72)

            verdict_detail_text = (f'收到 {data.users_submitted} 个人的提交，'
                                   f'其中包含 {pack_verdict_detail(data.verdict_data.get("verdicts"))}')
            verdict_detail = StyledString(config, verdict_detail_text, 'M', 28)

            hourly_data = pack_hourly_detail(data.hourly_data)
            hourly_text = "" if len(hourly_data) == 0 else (
                f'提交高峰时段为 {"{:02d}:00 - {:02d}:59".format(hourly_data["hot_time"], hourly_data["hot_time"])}. '
                f'在 {hourly_data["hot_count"]} 份提交中，通过率为 {"{:.2f}".format(hourly_data["hot_ac"] * 100)}%.')

            hourly_title = StyledString(config, "提交时间分布", 'B', 36)
            hourly_detail = StyledString(config, hourly_text, 'M', 28)

            first_ac_text = (f'在 {datetime.fromtimestamp(data.first_ac.at).strftime("%H:%M:%S")} '
                             f'提交了 {data.first_ac.problem_name} 并通过.')

            first_ac_title = StyledString(config, "昨日最速通过", 'B', 36)
            first_ac_who = StyledString(config, data.first_ac.user.name, 'H', 72)
            first_ac_detail = StyledString(config, first_ac_text, 'M', 28)

            popular_problem_title = StyledString(config, "昨日最受欢迎的题目", 'B', 36)
            popular_problem_name = StyledString(config, data.popular_problem[0], 'H', 72)
            popular_problem_detail = StyledString(config, f'共有 {data.popular_problem[1]} 个人提交本题', 'M', 28)

            top_ten = slice_ranking_data(rank_data, 10)
            top_10_subtitle = StyledString(config, "训练榜单", "B", 36)
            top_10_title = StyledString(config, "题数排名", "H", 72)
            top_10_mark = StyledString(config, "Top 10th", "H", 48)
            top_10_detail = pack_ranking_list(config, top_ten, verdict)

            full_rank_subtitle = StyledString(config, "完整榜单", "B", 36)
            full_rank_title = StyledString(config, "昨日 OJ 总榜", "H", 72)
            full_rank_detail = pack_ranking_list(config, data.total_board, verdict)

            cp = StyledString(config, f'Generated from {config.get_config()["board_name"]}.\n'
                                      f'©Peeper-Board-Generator Dev Team.\n'
                                      f'At {datetime.now().strftime("%Y/%m/%d %H:%M:%S")}', 'B', 24,
                              line_multiplier=1.32)

            total_height = (
                    calculate_height([title, eng_full_name]) +
                    (
                        calculate_height([submission_none_subtitle, submission_none_title]) + 124
                        if not has_ac_submission
                        else (calculate_height([play_of_the_oj_title, play_of_the_oj,
                                                top_5_subtitle, top_5_title,
                                                total_submits_title, total_submits_detail, verdict_detail,
                                                first_ac_title, first_ac_who, first_ac_detail,
                                                popular_problem_title, popular_problem_name, popular_problem_detail,
                                                hourly_title, hourly_detail,
                                                full_rank_subtitle, full_rank_title]) +
                              calculate_ranking_height(config, [top_5_detail, full_rank_detail]) + 1248)
                    ) + (
                        calculate_height([ranking_none_subtitle, ranking_none_title]) + 124
                        if len(rank) == 0
                        else (calculate_height([top_10_subtitle, top_10_title]) +
                              calculate_ranking_height(config, [top_10_detail]) + 148)
                    ) +
                    calculate_height([cp]) +
                    (calculate_height([play_of_the_oj_time]) if play_of_the_oj_is_parallel else -16)
            ) + 180

            output_img = pixie.Image(1280, total_height + 300)
            current_y = draw_basic_content(output_img, total_height, title, eng_full_name, 168, logo_path)

            if not has_ac_submission:
                current_y = draw_text(output_img, submission_none_subtitle, 16, current_y)
                current_y = draw_text(output_img, submission_none_title, 108, current_y)
            else:
                current_y = draw_text(output_img, play_of_the_oj_title, 16, current_y)
                current_y = draw_text(output_img, play_of_the_oj, 16 if play_of_the_oj_is_parallel else 108, current_y)
                if play_of_the_oj_is_parallel:  # 并列时显示最早通过时间
                    play_of_the_oj_time.set_font_color(Color(0, 0, 0, 136 / 255))
                    current_y = draw_text(output_img, play_of_the_oj_time, 108, current_y)

                current_y = draw_text(output_img, top_5_subtitle, 16, current_y)
                current_y = draw_text(output_img, top_5_title, 16, current_y)
                current_y -= 86
                current_y = draw_text(output_img, top_5_mark, 32, current_y,
                                      x=ImgConvert.calculate_string_width(top_5_title) + 128 + 28)
                current_y = draw_rank_detail(config, output_img, top_5_detail, 108, current_y)

                current_y = draw_submit_detail(output_img,
                                               total_submits_title, total_submits_detail,
                                               ave_score_title, ave_score_detail_main, ave_score_detail_sub,
                                               ac_rate_title, ac_rate_detail_main, ac_rate_detail_sub,
                                               verdict_detail,
                                               hourly_title, hourly_data, hourly_detail,
                                               first_ac_title, first_ac_who, first_ac_detail,
                                               current_y)

                current_y = draw_text(output_img, popular_problem_title, 16, current_y)
                current_y = draw_text(output_img, popular_problem_name, 16, current_y)
                popular_problem_detail.set_font_color(Color(0, 0, 0, 136 / 255))
                current_y = draw_text(output_img, popular_problem_detail, 108, current_y)

            if len(rank) == 0:
                current_y = draw_text(output_img, ranking_none_subtitle, 16, current_y)
                current_y = draw_text(output_img, ranking_none_title, 108, current_y)
            else:
                current_y = draw_text(output_img, top_10_subtitle, 16, current_y)
                current_y = draw_text(output_img, top_10_title, 16, current_y)
                current_y -= 86
                current_y = draw_text(output_img, top_10_mark, 32, current_y,
                                      x=ImgConvert.calculate_string_width(top_10_title) + 128 + 28)
                current_y = draw_rank_detail(config, output_img, top_10_detail, 108, current_y)

            if len(yesterday.submissions) != 0:
                current_y = draw_text(output_img, full_rank_subtitle, 16, current_y)
                current_y = draw_text(output_img, full_rank_title, 16, current_y)
                current_y = draw_rank_detail(config, output_img, full_rank_detail, 108, current_y)

            draw_text(output_img, cp, 108, current_y)

            return output_img

        if board_type == "now":
            alias = {val: key for key, val in ALIAS_MAP.items()}
            submission_none_subtitle = StyledString(config, "记录为空", 'B', 36)
            submission_none_title = StyledString(config, f"今日无{alias[verdict]}提交", 'H', 72)
            ranking_none_subtitle = StyledString(config, "暂无排行", 'B', 36)
            ranking_none_title = StyledString(config, "当前排行榜为空", 'H', 72)

            if verdict == "Accepted":
                title = StyledString(config, "今日当前提交榜单", 'H', 96)

                data = generate_board_data(today.submissions, verdict)
                rank = today.rankings
                # 对于 now 榜单的图形逻辑
                rank_data = pack_rank_data(rank)
                has_ac_submission = len([s for s in today.submissions if s.verdict == verdict]) > 0

                tops_subtitle = StyledString(config, "过题数榜单", "B", 36)
                tops_title = StyledString(config, "今日过题数", "H", 72)
                tops_detail = pack_ranking_list(config, data.total_board, verdict)

                total_submits_title = StyledString(config, "提交总数", 'B', 36)
                total_submits_detail = StyledString(config, str(data.total_submits), 'H', 72)

                ave_score_split = format(data.avg_score, '.2f').split(".")  # 分割小数

                ave_score_title = StyledString(config, "提交平均分", 'B', 36)
                ave_score_detail_main = StyledString(config, ave_score_split[0], 'H', 72)
                ave_score_detail_sub = StyledString(config, "." + ave_score_split[1], 'H', 72)

                ac_rate_split = format(data.ac_rate * 100, '.2f').split(".")

                ac_rate_title = StyledString(config, "提交通过率", 'B', 36)
                ac_rate_detail_main = StyledString(config, ac_rate_split[0], 'H', 72)
                ac_rate_detail_sub = StyledString(config, "." + ac_rate_split[1], 'H', 72)

                verdict_detail_text = (f'收到 {data.users_submitted} 个人的提交，'
                                       f'其中包含 {pack_verdict_detail(data.verdict_data.get("verdicts"))}')
                verdict_detail = StyledString(config, verdict_detail_text, 'M', 28)

                hourly_data = pack_hourly_detail(data.hourly_data)
                hourly_text = "" if len(hourly_data) == 0 else (
                    f'提交高峰时段为 {"{:02d}:00 - {:02d}:59".format(hourly_data["hot_time"], hourly_data["hot_time"])}. '
                    f'在 {hourly_data["hot_count"]} 份提交中，通过率为 {"{:.2f}".format(hourly_data["hot_ac"] * 100)}%.')

                hourly_title = StyledString(config, "提交时间分布", 'B', 36)
                hourly_detail = StyledString(config, hourly_text, 'M', 28)

                first_ac_text = (f'在 {datetime.fromtimestamp(data.first_ac.at).strftime("%H:%M:%S")} '
                                 f'提交了 {data.first_ac.problem_name} 并通过.')

                first_ac_title = StyledString(config, "今日最速通过", 'B', 36)
                first_ac_who = StyledString(config, data.first_ac.user.name, 'H', 72)
                first_ac_detail = StyledString(config, first_ac_text, 'M', 28)

                top_five = slice_ranking_data(rank_data, 5)
                top_5_subtitle = StyledString(config, "训练榜单", "B", 36)
                top_5_title = StyledString(config, "题数排名", "H", 72)
                top_5_mark = StyledString(config, "Top 5th", "H", 48)
                top_5_tip = StyledString(config, "为存在\"重复提交往日已AC的题目\"条件下的过题数理论值", 'M', 28)
                top_5_detail = pack_ranking_list(config, top_five, verdict)

                cp = StyledString(config, f'Generated from {config.get_config()["board_name"]}.\n'
                                          f'©Peeper-Board-Generator Dev Team.\n'
                                          f'At {datetime.now().strftime("%Y/%m/%d %H:%M:%S")}', 'B', 24,
                                  line_multiplier=1.32)
                total_height = (
                        calculate_height([title, eng_full_name]) +
                        (
                            calculate_height([submission_none_subtitle, submission_none_title]) + 124
                            if not has_ac_submission
                            else (calculate_height([tops_subtitle, tops_title,
                                                    total_submits_title, total_submits_detail, verdict_detail,
                                                    first_ac_title, first_ac_who, first_ac_detail,
                                                    hourly_title, hourly_detail]) +
                                  calculate_ranking_height(config, [tops_detail]) + 842)
                        ) + (
                            calculate_height([ranking_none_subtitle, ranking_none_title]) + 124
                            if len(rank) == 0
                            else (calculate_height([top_5_subtitle, top_5_title, top_5_tip]) +
                                  calculate_ranking_height(config, [top_5_detail]) + 148)
                        ) +
                        calculate_height([cp])
                ) + 180

                output_img = pixie.Image(1280, total_height + 300)
                current_y = draw_basic_content(output_img, total_height, title, eng_full_name, 168, logo_path)

                if not has_ac_submission:
                    current_y = draw_text(output_img, submission_none_subtitle, 16, current_y)
                    current_y = draw_text(output_img, submission_none_title, 108, current_y)
                else:
                    current_y = draw_text(output_img, tops_subtitle, 16, current_y)
                    current_y = draw_text(output_img, tops_title, 16, current_y)
                    current_y = draw_rank_detail(config, output_img, tops_detail, 108, current_y)

                    current_y = draw_submit_detail(output_img,
                                                   total_submits_title, total_submits_detail,
                                                   ave_score_title, ave_score_detail_main, ave_score_detail_sub,
                                                   ac_rate_title, ac_rate_detail_main, ac_rate_detail_sub,
                                                   verdict_detail,
                                                   hourly_title, hourly_data, hourly_detail,
                                                   first_ac_title, first_ac_who, first_ac_detail,
                                                   current_y)

                if len(rank) == 0:
                    current_y = draw_text(output_img, ranking_none_subtitle, 16, current_y)
                    current_y = draw_text(output_img, ranking_none_title, 108, current_y)
                else:
                    current_y = draw_text(output_img, top_5_subtitle, 16, current_y)
                    current_y = draw_text(output_img, top_5_title, 16, current_y)
                    current_y -= 86
                    current_y = draw_text(output_img, top_5_mark, 20, current_y,
                                          x=ImgConvert.calculate_string_width(top_5_title) + 128 + 28)
                    top_5_tip.set_font_color(Color(0, 0, 0, 136 / 255))
                    current_y = draw_text(output_img, top_5_tip, 32, current_y)
                    current_y = draw_rank_detail(config, output_img, top_5_detail, 108, current_y)

                draw_text(output_img, cp, 108, current_y)

                return output_img
            else:
                title = StyledString(config, f"今日当前{alias[verdict]}榜单", 'H', 96)
                data = generate_board_data(today.submissions, verdict)
                rank = (rank_by_verdict([s for s in today.submissions if s.verdict == verdict])
                        .get(verdict))  # { username: submissionCnt}
                # 对于分 verdict 的 now 榜单的图形逻辑
                rank_data = pack_verdict_rank_data(rank, verdict)

                total_submits_title = StyledString(config, "提交总数", 'B', 36)
                total_submits_detail = StyledString(config, str(data.total_submits), 'H', 72)

                prop_val = 0 if data.total_submits == 0 else (
                        sum(item[verdict][1] for item in data.total_board) / data.total_submits * 100)
                prop_split = format(prop_val, '.2f').split(".")  # 分割小数

                prop_title = StyledString(config, f"{verdict} 占比", 'B', 36)
                prop_detail_main = StyledString(config, prop_split[0], 'H', 72)
                prop_detail_sub = StyledString(config, "." + prop_split[1], 'H', 72)

                top_ten = slice_ranking_data(rank_data, 10)
                top_10_subtitle = StyledString(config, "分类型提交榜单", "B", 36)
                top_10_title = StyledString(config, f"{alias[verdict]} 排行榜", "H", 72)
                top_10_mark = StyledString(config, "Top 10th", "H", 48)
                top_10_detail = pack_ranking_list(config, top_ten, verdict)

                cp = StyledString(config, f'Generated from {config.get_config()["board_name"]}.\n'
                                          f'©Peeper-Board-Generator Dev Team.\n'
                                          f'At {datetime.now().strftime("%Y/%m/%d %H:%M:%S")}', 'B', 24,
                                  line_multiplier=1.32)

                total_height = (
                        calculate_height([title, eng_full_name]) +
                        (
                            calculate_height([submission_none_subtitle, submission_none_title]) + 124
                            if not rank or len(rank) == 0
                            else (calculate_height([total_submits_title, total_submits_detail,
                                                    top_10_subtitle, top_10_title]) +
                                  calculate_ranking_height(config, [top_10_detail]) + 272)
                        ) +
                        calculate_height([cp])
                ) + 180

                output_img = pixie.Image(1280, total_height + 300)
                current_y = draw_basic_content(output_img, total_height, title, eng_full_name, 168, logo_path)

                if not rank or len(rank) == 0:
                    current_y = draw_text(output_img, submission_none_subtitle, 16, current_y)
                    current_y = draw_text(output_img, submission_none_title, 108, current_y)
                else:
                    begin_y = current_y

                    current_y = draw_text(output_img, total_submits_title, 16, current_y)
                    draw_text(output_img, total_submits_detail, 16, current_y)
                    current_y = begin_y
                    total_submits_width = max(
                        ImgConvert.calculate_string_width(total_submits_title),
                        ImgConvert.calculate_string_width(total_submits_detail)
                    )

                    current_y = draw_text(output_img, prop_title, 16, current_y, x=total_submits_width + 128 + 150)
                    # 保持在同一行
                    draw_text(output_img, prop_detail_main, 32, current_y, x=total_submits_width + 128 + 150)
                    prop_detail_sub.set_font_color(Color(0, 0, 0, 64 / 255))
                    current_y = draw_text(output_img, prop_detail_sub, 108, current_y,
                                          x=ImgConvert.calculate_string_width(
                                              prop_detail_main) + total_submits_width + 128 + 150)

                    current_y = draw_text(output_img, top_10_subtitle, 16, current_y)
                    current_y = draw_text(output_img, top_10_title, 16, current_y)
                    current_y -= 86
                    current_y = draw_text(output_img, top_10_mark, 32, current_y,
                                          x=ImgConvert.calculate_string_width(top_10_title) + 128 + 28)
                    current_y = draw_rank_detail(config, output_img, top_10_detail, 108, current_y)

                draw_text(output_img, cp, 108, current_y)

                return output_img
