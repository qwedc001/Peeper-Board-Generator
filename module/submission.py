import logging
import time

from module.structures import SubmissionData, UserData


def get_first_ac(submission_list: list[SubmissionData]) -> SubmissionData:
    for submission in submission_list[::-1]:
        if submission.verdict == 'Accepted':
            return submission
    return SubmissionData(UserData("好像今天没有人AC", "-1"), 0, "Wait WHAT",
                          "114514", "Never gonna give you up", 1919810)


def get_hourly_submissions(submission_list: list[SubmissionData]) -> dict:
    result = {}
    for i in range(24):
        result[str(i)] = [0, 0]
    for submission in submission_list:
        hour = time.localtime(submission.at).tm_hour
        if submission.verdict == 'Accepted':
            result[str(hour)][0] += 1
        result[str(hour)][1] += 1
    # 0: AC, 1: 总数
    for i in range(24):
        if result[str(i)][1] == 0:
            result[str(i)][0] = 0
        else:
            result[str(i)][0] /= result[str(i)][1]
    # 0: AC 率, 1: 总数
    return result


def get_most_popular_problem(submission_list: list[SubmissionData]) -> tuple[str, int]:
    problem_dict = {}
    submission_user_dict = {}
    for submission in submission_list:
        if submission.problem_name not in problem_dict:
            problem_dict[submission.problem_name] = 0
            submission_user_dict[submission.problem_name] = [submission.user.name]
        if submission.user.name not in submission_user_dict[submission.problem_name]:
            problem_dict[submission.problem_name] += 1
            submission_user_dict[submission.problem_name].append(submission.user.name)
            logging.debug(f"检测到新提交用户{submission.user.name}，题目{submission.problem_name}，已记录。")
        else:
            continue
    max_problem = max(problem_dict, key=problem_dict.get)
    return max_problem, problem_dict[max_problem]


def classify_by_verdict(submission_list: list[SubmissionData]) -> dict:
    result = {
        "avg_score": 0,
        "ac_rate": 0.0,
        "verdicts": {}
    }
    for submission in submission_list:
        if submission.verdict not in result['verdicts']:
            result['verdicts'][submission.verdict] = 0
        result['verdicts'][submission.verdict] += 1
        result['avg_score'] += submission.score
        result['ac_rate'] += 1 if submission.verdict == 'Accepted' else 0
    result['avg_score'] /= len(submission_list)
    result['ac_rate'] /= len(submission_list)
    return result


def rank_by_verdict(submission_list: list[SubmissionData]) -> dict:
    result: dict[str, dict[str, tuple[int, int]]] = {}  # 外层str: verdict, 内层str: user_name
    problem_ac_list: list[tuple[str, str]] = []  # uid, pid

    for submission in submission_list:
        if submission.verdict not in result:
            result[submission.verdict] = {}
        if submission.user.name not in result[submission.verdict]:
            result[submission.verdict][submission.user.name] = (submission.at, 0)
        earliest_submission, cnt = result[submission.verdict][submission.user.name]

        if submission.verdict == "Accepted" and (submission.user.uid, submission.problem_id) not in problem_ac_list:
            cnt += 1  # 去除同一道题的重复AC (本函数不影响AC率计算，所以直接不算个数即可)
            problem_ac_list.append((submission.user.uid, submission.problem_id))

        if submission.at < earliest_submission:
            result[submission.verdict][submission.user.name] = (submission.at, cnt)
        else:
            result[submission.verdict][submission.user.name] = (earliest_submission, cnt)

    for verdict in result:
        # 先按照提交次数降序，同次数再按照提交时间升序
        result[verdict] = dict(sorted(result[verdict].items(), key=lambda x: (-x[1][1], x[1][0])))
    return result


def count_users_submitted(submission_list: list[SubmissionData]) -> int:
    return len(set([submission.user.name for submission in submission_list]))
