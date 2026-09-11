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

    def __init__(self, user: UserData, accepted: str, rank: str, unrated: bool):
        self.user = user
        self.accepted = accepted
        self.rank = rank
        self.unrated = unrated

    # 兼容旧的访问方式，uid / user_name 现在统一存放在 user 中
    @property
    def uid(self) -> str:
        return self.user.uid

    @property
    def user_name(self) -> str:
        return self.user.name

    @classmethod
    def from_json(cls, json_data: dict):
        if 'user' in json_data:
            user = UserData.from_json(json_data['user'])
        else:
            # 兼容历史数据：旧 json 直接平铺 user_name / uid，且没有 register_at
            user = UserData(json_data['user_name'], json_data['uid'],
                            json_data.get('register_at', 0))
        return RankingData(user, json_data['accepted'],
                           json_data['rank'], json_data['unrated'])


class DailyJson:

    def __init__(self, submissions: list[SubmissionData], rankings: list[RankingData]):
        self.submissions = submissions
        self.rankings = rankings

    @classmethod
    def from_json(cls, json_data: dict):
        return DailyJson([SubmissionData.from_json(item) for item in json_data['submissions']],
                         [RankingData.from_json(item) for item in json_data['rankings']])
