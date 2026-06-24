import logging
import time

import config
from core.examClient import ExamClient

logger = logging.getLogger(__name__)

MAX_SUBMIT_ATTEMPTS = 3
DEFAULT_RETRY_DELAY_SECONDS = 20
SUBMIT_INTERVAL_SECONDS = 2


class ExamLearnPoint:
    """期末考试自动答题。"""

    def __init__(self, node):
        self.node_id = node.get("id")
        self.node_name = node.get("name", "期末考试")
        self.exam_id = None
        self.classroom_id = None
        self.university_id = None
        self.problems = []
        self.completed_problem_ids = set()

    def init_context(self, classroom_id, university_id, exam_id):
        self.classroom_id = str(classroom_id)
        self.university_id = str(university_id)
        self.exam_id = str(exam_id)

    def _get_cached_results(self, exam_client):
        try:
            resp = exam_client.cache_results(self.exam_id, self.classroom_id)
            results = resp.get("data", {}).get("results", [])
            return {r["problem_id"] for r in results if r.get("result")}
        except Exception:
            return set()

    def _build_problem_payload(self, problem):
        return {
            "problem_id": problem.get("problem_id"),
            "index": problem.get("index"),
            "type": problem.get("Type"),
            "question": problem.get("Body", ""),
            "options": [
                {"key": opt.get("key"), "value": opt.get("value")}
                for opt in problem.get("Options", [])
            ],
        }

    def run(self, ai_solver):
        if not config.X_ACCESS_TOKEN:
            logger.warning("未配置 X_ACCESS_TOKEN，跳过期末考试自动答题")
            return

        exam_client = ExamClient()

        # 先尝试获取试卷（可能考试已启动）
        paper = exam_client.show_paper(self.exam_id)
        if paper.get("errcode") == 10011:
            # 考试未启动，先开始
            logger.info("考试尚未开始，正在启动...")
            start_resp = exam_client.start_paper(self.exam_id)
            if start_resp.get("errcode") != 0:
                logger.warning(f"启动考试失败: errcode={start_resp.get('errcode')}")
                return
            paper = exam_client.show_paper(self.exam_id)

        if paper.get("errcode") != 0:
            logger.warning(f"获取试卷失败: errcode={paper.get('errcode')}, errmsg={paper.get('errmsg')}")
            return

        # 提取题目
        paper_data = paper.get("data", {})
        self.problems = paper_data.get("problems", [])
        if not self.problems:
            logger.warning("试卷无题目，跳过考试")
            return

        # 检查已提交
        self.completed_problem_ids = self._get_cached_results(exam_client)
        pending = [p for p in self.problems if p.get("problem_id") not in self.completed_problem_ids]

        if not pending:
            logger.info(f"期末考试所有题目已提交，共 {len(self.problems)} 题")
            return

        logger.info(
            f"开始{self.node_name}，共 {len(self.problems)} 题，"
            f"已完成 {len(self.completed_problem_ids)} 题，"
            f"待提交 {len(pending)} 题"
        )

        submit_count = 0
        last_refresh = time.time()
        for problem in pending:
            # 每 60 秒刷新考试心跳，防止 session 过期
            if time.time() - last_refresh > 60:
                try:
                    exam_client.refresh_time(self.exam_id)
                    last_refresh = time.time()
                except Exception:
                    pass
            payload = self._build_problem_payload(problem)
            label = (
                f"考试 题型[{problem.get('TypeText', problem.get('Type'))}] "
                f"题目[{payload['question'][:50]}...]"
            )

            # AI 求解
            try:
                valid_keys = [opt["key"] for opt in payload["options"]]
                answer = ai_solver.solve_exercise_problem(
                    problem_type=payload["type"],
                    question_text=payload["question"],
                    options=payload["options"],
                )
            except Exception as exc:
                logger.warning(f"{label} 求解失败: {exc}")
                continue

            # 提交（带重试）
            success = False
            for attempt in range(1, MAX_SUBMIT_ATTEMPTS + 1):
                try:
                    resp = exam_client.answer_problem(
                        exam_id=self.exam_id,
                        problem_id=payload["problem_id"],
                        answer=answer,
                        classroom_id=self.classroom_id,
                    )
                    if resp.get("errcode") == 0:
                        submit_count += 1
                        self.completed_problem_ids.add(payload["problem_id"])
                        logger.info(f"{label} 提交完成，答案: {answer}")
                        success = True
                        break

                    errmsg = resp.get("errmsg", str(resp))
                    logger.warning(f"{label} 第 {attempt} 次提交失败: {errmsg}")
                except Exception as exc:
                    logger.warning(f"{label} 第 {attempt} 次提交异常: {exc}")

                if attempt < MAX_SUBMIT_ATTEMPTS:
                    time.sleep(DEFAULT_RETRY_DELAY_SECONDS)

            if not success:
                logger.warning(f"{label} 提交失败，已达到最大重试次数")

            time.sleep(SUBMIT_INTERVAL_SECONDS)

        logger.info(f"{self.node_name}处理结束，本次提交 {submit_count} 题")

        # 不自动交卷，留给用户检查
        if submit_count > 0:
            logger.info("题目已全部提交，请自行在网页上确认并交卷")
