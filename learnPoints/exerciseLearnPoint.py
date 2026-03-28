import logging
import re
import time
from html import unescape
from pathlib import Path

import config
from learnPoints.baseLearnPoint import BaseLearnPoint
from utils.yuketang_exam_decoder import decode_exercise_payload

logger = logging.getLogger(__name__)

HTML_TAG_RE = re.compile(r"<[^>]+>")
LINE_BREAK_RE = re.compile(r"<br\s*/?>", re.IGNORECASE)
WHITESPACE_RE = re.compile(r"\s+")
PROBLEM_TYPE_LABELS = {
    "SingleChoice": "单选题",
    "MultipleChoice": "多选题",
    "Judgement": "判断题",
}
MAX_SUBMIT_ATTEMPTS = 2
SUBMIT_RETRY_DELAY_SECONDS = 20


def clean_rich_text(value):
    if not value:
        return ""
    cleaned = LINE_BREAK_RE.sub("\n", str(value))
    cleaned = HTML_TAG_RE.sub(" ", cleaned)
    cleaned = unescape(cleaned).replace("\xa0", " ")
    cleaned = WHITESPACE_RE.sub(" ", cleaned)
    return cleaned.strip()


def is_problem_completed(problem):
    user = problem.get("user") or {}
    if user.get("my_answer"):
        return True
    my_answers = user.get("my_answers")
    if isinstance(my_answers, dict):
        return bool(my_answers)
    return bool(my_answers)


def get_problem_type(problem):
    content = problem.get("content") or {}
    problem_type = str(content.get("Type") or "").strip()
    if problem_type not in PROBLEM_TYPE_LABELS:
        raise ValueError(f"Unsupported exercise type: {problem_type or 'EMPTY'}")
    return problem_type


class ExerciseLearnPoint(BaseLearnPoint):
    def __init__(self, nodes):
        super().__init__()
        self.decoded_homeworkInfo = []
        self.decoded_mapping = {}
        self.exercise_id = None
        self.exercise_payload = None
        self.font_url = None
        self.homeworkInfo = []
        self.leaf_type_id = None
        self.node_id = nodes.get("id")
        self.node_name = nodes.get("name")
        self.pending_problems = []
        self.skipped_problem_count = 0

    def _prepare_request_context(self):
        self.req.set_exercise_request_context(
            classroom_id=self.classroom_id,
            university_id=self.university_id,
            uv_id=self.uv_id,
            node_id=self.node_id,
            leaf_type_id=self.leaf_type_id,
        )

    def _load_problem_data(self):
        data = (self.exercise_payload or {}).get("data", {})
        self.exercise_id = data.get("exercise_id")
        self.font_url = data.get("font")
        self.homeworkInfo = data.get("problems") or []

    def initProcess(self):
        leaf_info = self.req.getSkuidAndCcid(self.classroom_id, self.node_id)
        self.leaf_type_id = (
            leaf_info.get("data", {})
            .get("content_info", {})
            .get("leaf_type_id")
        )
        self._prepare_request_context()
        self.exercise_payload = self.req.get_exercise_list(self.leaf_type_id)
        self._load_problem_data()

    def _ensure_decoded_problems(self):
        if self.decoded_homeworkInfo:
            return
        decoded_payload, mapping = decode_exercise_payload(
            self.exercise_payload,
            workdir=Path(".cache") / "yuketang_exam_fonts",
        )
        self.decoded_mapping = mapping
        self.decoded_homeworkInfo = decoded_payload.get("data", {}).get("problems") or []

    def _iter_pending_problems(self):
        self._ensure_decoded_problems()
        pending_problems = []
        skipped_problem_count = 0
        for problem in self.decoded_homeworkInfo:
            if is_problem_completed(problem):
                skipped_problem_count += 1
                continue
            pending_problems.append(problem)
        self.pending_problems = pending_problems
        self.skipped_problem_count = skipped_problem_count
        return pending_problems

    def _problem_prompt_payload(self, problem):
        content = problem.get("content") or {}
        problem_type = get_problem_type(problem)
        options = [
            {
                "key": option.get("key"),
                "value": clean_rich_text(option.get("value")),
            }
            for option in content.get("Options") or []
        ]
        return {
            "problem_id": problem.get("problem_id") or content.get("ProblemID"),
            "index": problem.get("index"),
            "type": problem_type,
            "type_text": PROBLEM_TYPE_LABELS[problem_type],
            "question": clean_rich_text(content.get("Body")),
            "options": options,
        }

    def _mark_problem_submitted(self, problem, answer):
        content = problem.get("content") or {}
        user = problem.setdefault("user", {})
        if get_problem_type(problem) == "MultipleChoice":
            selected = set(answer)
            user["my_answers"] = {
                str(option.get("key")): str(option.get("key")) in selected
                for option in content.get("Options") or []
            }
            return
        user["my_answer"] = answer

    def _build_problem_log_label(self, prompt_payload):
        return (
            f"作业[{self.node_name}] "
            f"题型[{prompt_payload['type_text']}] "
            f"题目[{prompt_payload['question']}]"
        )

    def _submit_problem_with_retry(self, prompt_payload, answer):
        last_error = None
        for attempt in range(1, MAX_SUBMIT_ATTEMPTS + 1):
            try:
                self._prepare_request_context()
                response = self.req.exercise_problem_apply(
                    self.classroom_id,
                    prompt_payload["problem_id"],
                    answer,
                )
            except Exception as exc:
                last_error = exc
                logger.warning(
                    f"{self._build_problem_log_label(prompt_payload)} "
                    f"第{attempt}次提交异常: {exc}"
                )
                continue

            if response.get("success") is True:
                return response

            last_error = response
            logger.warning(
                f"{self._build_problem_log_label(prompt_payload)} "
                f"第{attempt}次提交失败: "
                f"{response.get('msg') or response.get('message') or response}"
            )

            if attempt < MAX_SUBMIT_ATTEMPTS:
                logger.warning(
                    f"{self._build_problem_log_label(prompt_payload)} "
                    f"{SUBMIT_RETRY_DELAY_SECONDS}秒后重试一次"
                )
                time.sleep(SUBMIT_RETRY_DELAY_SECONDS)

        return last_error

    def _refresh_after_submit(self):
        self._prepare_request_context()
        self.exercise_payload = self.req.get_exercise_list(self.leaf_type_id)
        self.decoded_homeworkInfo = []
        self.decoded_mapping = {}
        self._load_problem_data()

    def runFinish(self):
        if not self.exercise_payload:
            self.initProcess()

        if self.checkFinish():
            logger.info(f"{self.node_name}学习点已完成，跳过")
            return
        if not config.api_key:
            logger.warning(f"{self.node_name}需要api_key，跳过练习自动答题")
            return

        try:
            pending_problems = self._iter_pending_problems()
        except Exception as exc:
            logger.warning(f"{self.node_name}题目解码失败: {exc}")
            return
        if not pending_problems:
            logger.info(f"{self.node_name}学习点已完成，跳过")
            return

        logger.info(
            f"开始{self.node_name}，共{len(self.decoded_homeworkInfo)}题，"
            f"已完成{self.skipped_problem_count}题，待提交{len(pending_problems)}题"
        )
        submit_count = 0
        for problem in pending_problems:
            prompt_payload = self._problem_prompt_payload(problem)
            problem_label = self._build_problem_log_label(prompt_payload)
            try:
                answer = self.req.solve_exercise_problem(
                    problem_type=prompt_payload["type"],
                    question_text=prompt_payload["question"],
                    options=prompt_payload["options"],
                )
            except Exception as exc:
                logger.warning(
                    f"{problem_label} 求解失败: {exc}"
                )
                continue

            response = self._submit_problem_with_retry(prompt_payload, answer)
            if not isinstance(response, dict) or response.get("success") is not True:
                logger.warning(
                    f"{problem_label} 提交失败，已达到最大重试次数"
                )
                continue

            submit_count += 1
            self._mark_problem_submitted(problem, answer)
            logger.info(
                f"{problem_label} 提交完成，答案: {answer}"
            )

        if submit_count:
            self._refresh_after_submit()
        logger.info(f"{self.node_name}处理结束，本次提交{submit_count}题")

    def checkFinish(self):
        problem_list = self.homeworkInfo or self.decoded_homeworkInfo
        if not problem_list:
            return False
        return all(is_problem_completed(problem) for problem in problem_list)


