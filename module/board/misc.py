import logging
import os
import sys

from datetime import datetime

from PIL import Image, ImageDraw
from pixie import pixie

from module.ImgConvert import StyledString, ImgConvert, Color
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


def generate_board_data(submissions: list[SubmissionData]) -> MiscBoard:
    result = {}
    accepted_desc = rank_by_verdict(submissions)['Accepted']
    result['play_of_the_oj'] = max(accepted_desc, key=accepted_desc.get)  # 昨日
    total_board = []
    rank = 1
    for i, (user, ac) in enumerate(accepted_desc.items()):
        if i > 0 and ac != accepted_desc[list(accepted_desc.keys())[i - 1]]:
            rank = i + 1
        total_board.append({"user": user, "ac": ac, "rank": rank})
    result['top_five'] = total_board[:5]  # 昨日
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
    max_val = tops[0][key]  # 以key作为排名依据
    ranking_list = []

    for top in tops:
        record = {'progress': str(int(top[key]) / int(max_val)),
                  'unrated': False,
                  'rank': StyledString(config, str(top['rank']), 'H', 64),
                  'user': StyledString(config, str(top['user']), 'B', 36),
                  'val': StyledString(config, str(top[key]), 'H', 64)}
        ranking_list.append(record)

    return ranking_list


def pack_verdict_detail(verdict_data: dict) -> str:
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
    max_hourly_submit = max(hourly[1] for (time, hourly) in hourly_data.items())
    hourly_detail = {'distribution': [], 'hot_time': 0, 'hot_count': 0, 'hot_ac': 0.0}

    for (time, hourly) in hourly_data.items():
        hourly_detail['distribution'].append({'hot_prop': hourly[1] / max_hourly_submit,  # 这个用来画柱状图
                                              'ac_prop': hourly[0]})
        if hourly[1] == max_hourly_submit:
            hourly_detail['hot_time'] = int(time)  # 所以为什么要转str呢？
            hourly_detail['hot_count'] = hourly[1]
            hourly_detail['hot_ac'] = max(hourly_detail['hot_ac'], hourly[0])

    return hourly_detail


def pack_rank_data(rank: list[RankingData]) -> list[dict]:
    # 封装一下
    rank_data = []
    for ranking_data in rank:
        rank_data.append({'user': ranking_data.user_name, 'rank': ranking_data.rank, 'ac': ranking_data.accepted})
    return rank_data


def calculate_height(strings: list[StyledString]) -> int:
    height = 0
    for string in strings:
        height += string.height
    return height


def calculate_ranking_height(rankings: list[list[dict]]) -> int:
    height = 0
    for ranking in rankings:
        for item in ranking:
            height += item['user'].height + 40 + 32
        height -= 32
    return height


def draw_text(draw: ImageDraw, content: StyledString, padding_bottom: int, current_y: int, x: int = 128) -> int:
    ImgConvert.draw_string(draw, content, x, current_y)
    return current_y + calculate_height([content]) + padding_bottom


# 这个java自带 (Color.darker)
def darken_color(color: tuple[int, int, int]) -> tuple[int, int, int]:
    return int(color[0] * 0.7), int(color[1] * 0.7), int(color[2] * 0.7)


def get_background(width, height, colors: list[str], positions: list[float]) -> pixie.Image:
    image = pixie.Image(width, height)
    image.fill(pixie.Color(0, 0, 0, 1))  # 填充黑色背景
    paint = pixie.Paint(pixie.LINEAR_GRADIENT_PAINT if len(colors) == 2 else pixie.RADIAL_GRADIENT_PAINT)  # 准备渐变色画笔
    paint_mask = pixie.Paint(pixie.SOLID_PAINT)  # 准备蒙版画笔
    paint_mask.color = pixie.Color(1, 1, 1, 0.7)  # 设置蒙版颜色
    for i in range(len(colors)):
        color = pixie.parse_color(colors[i])
        paint.gradient_handle_positions.append(pixie.Vector2(width * positions[i], height * positions[i]))
        paint.gradient_stops.append(pixie.ColorStop(color, i))
    ctx = image.new_context()
    ctx.fill_style = paint
    ctx.rounded_rect(32, 32, width - 64, height - 64, 192, 192, 192, 192)
    ctx.fill()
    mask = pixie.Image(width, height)
    ctx = mask.new_context()
    ctx.fill_style = paint_mask
    ctx.rounded_rect(32, 32, width - 64, height - 64, 192, 192, 192, 192)
    ctx.fill()
    image.draw(mask, blend_mode=pixie.NORMAL_BLEND)
    return image


def draw_basic_content(config: Config, total_height: int, title: StyledString,
                       subtitle: StyledString, current_y: int, logo_path: str) -> tuple[Image, ImageDraw, int]:
    current_gradient,gradient_positions = ImgConvert.GradientColors.generate_gradient()
    # 先暂时混用Pillow和pixie，根据后续情况再决定是否全部换用pixie
    background = get_background(1280, total_height + 300, current_gradient,gradient_positions)
    bg_path = os.path.join(config.work_dir, config.get_config('data'), "background.png")
    background.write_file(bg_path)
    output_img = Image.open(bg_path)
    draw = ImageDraw.Draw(output_img)
    accent_color = Color.from_hex(current_gradient[0]).rgb
    accent_dark_color = darken_color(darken_color(darken_color(accent_color)))

    logo_tinted = ImgConvert.apply_tint(logo_path, accent_color)
    logo_tinted.resize((140, 140))
    output_img.paste(logo_tinted, (90,90),logo_tinted)
    title.font_color = accent_dark_color
    current_y = draw_text(draw, title, 32, current_y, x=290)
    subtitle.font_color = (accent_dark_color[0], accent_dark_color[1], accent_dark_color[2], 136)
    current_y = draw_text(draw, subtitle, 108, current_y)

    return output_img, draw, current_y


class MiscBoardGenerator:

    @staticmethod
    def generate_image(config: Config, board_type: str, logo_path: str, verdict: str = "Accepted"):
        today = load_json(config, False)
        if board_type == "full":
            title = StyledString(config, "昨日卷王天梯榜", 'H', 96)
            subtitle = StyledString(config, f'{get_date_string(True)} {config.get_config("oj_name")} Rank List', 'H',
                                    36)

            try:
                yesterday = load_json(config, True)
            except FileNotFoundError:
                logging.error("未检测到昨日榜单文件，请改用--now参数生成今日榜单")
                sys.exit(1)
            data = generate_board_data(yesterday.submissions)
            rank = today.rankings
            # 对于 full 榜单的图形逻辑
            rank_data = pack_rank_data(rank)

            play_of_the_oj_title = StyledString(config, f"昨日卷王", 'B', 36)
            play_of_the_oj = StyledString(config, data.play_of_the_oj, 'H', 72)

            top_5_subtitle = StyledString(config, "过题数榜单", "B", 36)
            top_5_title = StyledString(config, "昨日过题数", "H", 72)
            top_5_mark = StyledString(config, "Top 5th", "H", 48)
            top_5_detail = pack_ranking_list(config, data.top_five, 'ac')

            total_submits_title = StyledString(config, "提交总数", 'B', 36)
            total_submits_detail = StyledString(config, str(data.total_submits), 'H', 72)

            ave_score_split = format(data.avg_score, '.2f').split(".")  # 分割小数

            ave_score_title = StyledString(config, "提交平均分", 'B', 36)
            ave_score_detail_main = StyledString(config, ave_score_split[0], 'H', 72)
            ave_score_detail_sub = StyledString(config, ave_score_split[0], 'H', 72)

            ac_rate_split = format(data.avg_score, '.2f').split(".")

            ac_rate_title = StyledString(config, "提交通过率", 'B', 36)
            ac_rate_detail_main = StyledString(config, ac_rate_split[0], 'H', 72)
            ac_rate_detail_sub = StyledString(config, ac_rate_split[0], 'H', 72)

            verdict_detail_text = (f'收到 {data.users_submitted} 个人的提交，'
                                   f'其中包含 {pack_verdict_detail(data.verdict_data["verdicts"])}')
            verdict_detail = StyledString(config, verdict_detail_text, 'M', 28)

            hourly_data = pack_hourly_detail(data.hourly_data)
            hourly_text = (
                f'提交高峰时段为 {"%02d:00 - %02d:59".format(hourly_data["hot_time"], hourly_data["hot_time"])}. '
                f'在 {hourly_data["hot_count"]} 份提交中，通过率为 {".2f%".format(hourly_data["hot_ac"])}.')

            hourly_title = StyledString(config, "提交时间分布", 'B', 36)
            hourly_detail = StyledString(config, hourly_text, 'M', 28)

            first_ac_text = (f'在 {datetime.fromtimestamp(data.first_ac.at).strftime("%H:%M:%S")} '
                             f'提交了 {data.first_ac.problem_name} 并通过.')

            first_ac_title = StyledString(config, "昨日最速通过", 'B', 36)
            first_ac_who = StyledString(config, data.first_ac.user.name, 'B', 36)
            first_ac_detail = StyledString(config, first_ac_text, 'M', 28)

            popular_problem_title = StyledString(config, "昨日最受欢迎的题目", 'B', 36)
            popular_problem_name = StyledString(config, data.popular_problem[0], 'M', 72)
            popular_problem_detail = StyledString(config, f'共有 {data.popular_problem[1]} 个人提交本题', 'M', 28)

            top_ten = rank_data[:10]
            top_10_subtitle = StyledString(config, "训练榜单", "B", 36)
            top_10_title = StyledString(config, "题数排名", "H", 72)
            top_10_mark = StyledString(config, "Top 10th", "H", 48)
            top_10_detail = pack_ranking_list(config, top_ten, 'ac')

            full_rank_subtitle = StyledString(config, "完整榜单", "B", 36)
            full_rank_title = StyledString(config, "昨日 OJ 总榜", "H", 72)
            full_rank_detail = pack_ranking_list(config, data.total_board, 'ac')

            cp = StyledString(config, f'Generated by xxx.\n'
                                      f'©xxx.\n'
                                      f'At yyyy/MM/dd HH:mm:ss', 'B', 24, line_multiplier=1.32)

            total_height = (calculate_height([
                title, subtitle,
                play_of_the_oj_title, play_of_the_oj,
                top_5_subtitle, top_5_title,
                total_submits_title, total_submits_detail, verdict_detail,
                first_ac_title, first_ac_who, first_ac_detail,
                popular_problem_title, popular_problem_name, popular_problem_detail,
                hourly_title, hourly_detail,
                top_10_subtitle, top_10_title,
                full_rank_subtitle, full_rank_title,
                cp
            ]) + calculate_ranking_height([top_5_detail, top_10_detail, full_rank_detail])
                            + 1380 + 200)  # 1380是所有padding

            image, draw, current_y = draw_basic_content(config, total_height, title, subtitle, 134, logo_path)

            current_y = draw_text(draw, play_of_the_oj_title, 8, current_y)
            current_y = draw_text(draw, play_of_the_oj, 108, current_y)

            # to be continued.

            return image

        if board_type == "now":
            if verdict == "Accepted":
                title = StyledString(config, "今日当前提交榜", 'H', 96)
                subtitle = StyledString(config, f'{get_date_string(True)} {config.get_config("oj_name")} Rank List',
                                        'H', 36)

                data = generate_board_data(today.submissions)
                rank = today.rankings[:5]
                # 对于 now 榜单的图形逻辑
            else:
                title = StyledString(config, f"今日当前{verdict}榜", 'H', 96)
                subtitle = StyledString(config, f'{get_date_string(True)} {config.get_config("oj_name")} Rank List',
                                        'H', 36)
                data = generate_board_data([s for s in today.submissions if s.verdict == verdict])
                rank = rank_by_verdict([s for s in today.submissions if s.verdict == verdict])
                # 对于分 verdict 的 now 榜单的图形逻辑
