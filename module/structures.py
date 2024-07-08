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
