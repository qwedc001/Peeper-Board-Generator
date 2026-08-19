class UserData:
    def __init__(self, name: str, uid: str, register_at: int):
        self.name = name
        self.uid = uid
        self.register_at = register_at
        self.status = ""
        self.progress = ""
        self.mail = ""
        self.qq = ""
        self.qq_name = ""
        self.description = ""

    @classmethod
    def from_json(cls, json_data: dict):
        # 兼容历史数据：旧 json 中 user 没有 register_at，按 0 处理
        return UserData(json_data['name'], json_data['uid'],
                        json_data.get('register_at', 0))


class SubmissionData:

    def __init__(self, user: UserData, score: int, verdict: str, problem_id: str, problem_name: str, at: int):
        self.user = user
        self.score = score
        self.verdict = verdict
        self.problem_id = problem_id
        self.problem_name = problem_name
        self.at = at

    @classmethod
    def from_json(cls, json_data: dict):
        return SubmissionData(UserData.from_json(json_data['user']),
                              json_data['score'], json_data['verdict'],
                              json_data['problem_id'] if 'problem_id' in json_data else "",  # 做个判空兼容一下
                              json_data['problem_name'], json_data['at'])


class RankingData:

    def __init__(self, user_name: str, accepted: str, uid: str, rank: str, unrated: bool):
        self.user_name = user_name
        self.accepted = accepted
        self.uid = uid
        self.rank = rank
        self.unrated = unrated

    @classmethod
    def from_json(cls, json_data: dict):
        return RankingData(json_data['user_name'], json_data['accepted'],
                           json_data['uid'], json_data['rank'], json_data['unrated'])


class DailyJson:

    def __init__(self, submissions: list[SubmissionData], rankings: list[RankingData]):
        self.submissions = submissions
        self.rankings = rankings

    @classmethod
    def from_json(cls, json_data: dict):
        return DailyJson([SubmissionData.from_json(item) for item in json_data['submissions']],
                         [RankingData.from_json(item) for item in json_data['rankings']])
