import logging
import requests
import config

logger = logging.getLogger(__name__)
EXAM_HOST = "https://examination.xuetangx.com"


class ExamClient:
    """期末考试 API 客户端，使用 x_access_token 认证。"""

    def __init__(self):
        if not config.X_ACCESS_TOKEN:
            raise ValueError(
                "config.X_ACCESS_TOKEN 未设置，请从浏览器 cookies 复制 x_access_token 的值"
            )
        self.session = requests.Session()
        self.session.cookies.set("x_access_token", config.X_ACCESS_TOKEN, domain=".xuetangx.com")
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0",
                "x-client": "web",
                "xtbz": "cloud",
                "Origin": EXAM_HOST,
            }
        )

    def cover(self, exam_id):
        resp = self.session.get(f"{EXAM_HOST}/exam_room/cover?exam_id={exam_id}")
        resp.raise_for_status()
        return resp.json()

    def start_paper(self, exam_id):
        resp = self.session.post(
            f"{EXAM_HOST}/exam_room/start_paper",
            json={"exam_id": str(exam_id)},
        )
        data = resp.json()
        logger.info(f"start_paper: status={resp.status_code}, errcode={data.get('errcode')}, data={data.get('data')}")
        resp.raise_for_status()
        return data

    def show_paper(self, exam_id):
        resp = self.session.get(f"{EXAM_HOST}/exam_room/show_paper?exam_id={exam_id}")
        data = resp.json()
        logger.info(f"show_paper: status={resp.status_code}, errcode={data.get('errcode')}, errmsg={data.get('errmsg')}, data_keys={list(data.get('data', {}).keys())}")
        resp.raise_for_status()
        return data

    def answer_problem(self, exam_id, problem_id, answer, classroom_id):
        resp = self.session.post(
            f"{EXAM_HOST}/exam_room/answer_problem",
            json={
                "exam_id": str(exam_id),
                "problem_id": problem_id,
                "answer": answer,
                "classroom_id": str(classroom_id),
            },
        )
        resp.raise_for_status()
        return resp.json()

    def cache_results(self, exam_id, classroom_id):
        resp = self.session.get(
            f"{EXAM_HOST}/exam_room/cache_results"
            f"?exam_id={exam_id}&classroom_id={classroom_id}"
        )
        resp.raise_for_status()
        return resp.json()

    def submit_paper(self, exam_id, classroom_id):
        resp = self.session.post(
            f"{EXAM_HOST}/exam_room/submit_paper",
            json={"exam_id": str(exam_id), "classroom_id": str(classroom_id)},
        )
        resp.raise_for_status()
        return resp.json()

    def refresh_time(self, exam_id):
        resp = self.session.get(f"{EXAM_HOST}/exam_room/refresh_time?exam_id={exam_id}")
        resp.raise_for_status()
        return resp.json()
