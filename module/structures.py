class UserData:
    def __init__(self, name: str, uid: str):
        self.name = name
        self.uid = uid
        self.status = ""
        self.progress = ""
        self.mail = ""
        self.qq = ""
        self.qq_name = ""
        self.description = ""


class SubmissionData:

    def __init__(self, user: UserData, score: int, verdict: str, problem_name: str, at: int):
        self.user = user
        self.score = score
        self.verdict = verdict
        self.problem_name = problem_name
        self.at = at

    @classmethod
    def from_json(cls, json_data:dict):
        return SubmissionData(UserData(json_data['user']['name'], json_data['user']['uid']),
                              json_data['score'], json_data['verdict'], json_data['problem_name'],
                              json_data['at'])


class RankingData:

    def __init__(self, user_name: str, accepted: str, uid: str, rank: str):
        self.user_name = user_name
        self.accepted = accepted
        self.uid = uid
        self.rank = rank

    @classmethod
    def from_json(cls, json_data:dict):
        return RankingData(json_data['user_name'], json_data['accepted'], json_data['uid'], json_data['rank'])




class DailyJson:

    def __init__(self, submissions: list[SubmissionData], rankings: list[RankingData]):
        self.submissions = submissions
        self.rankings = rankings

    @classmethod
    def from_json(cls, json_data: dict):

        return DailyJson([SubmissionData.from_json(item) for item in json_data['submissions']],
                         [RankingData.from_json(item) for item in json_data['rankings']])
