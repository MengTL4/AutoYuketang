import copy
import json
from pathlib import Path

from core.commonFunReq import CommonFunReq
from learnPoints import exerciseLearnPoint as exercise_module
from learnPoints.exerciseLearnPoint import (
    ExerciseLearnPoint,
    get_problem_type,
    is_problem_completed,
)
from utils.yuketang_exam_decoder import decode_exercise_payload


def load_sample_payload():
    return json.loads(Path("test/exercise.json").read_text(encoding="utf-8"))


def test_decode_exercise_payload_decodes_sample(tmp_path):
    payload = load_sample_payload()
    decoded, _ = decode_exercise_payload(payload, workdir=tmp_path)

    first_problem = decoded["data"]["problems"][0]
    multiple_problem = decoded["data"]["problems"][10]
    judgement_problem = decoded["data"]["problems"][15]

    assert first_problem["content"]["Body"] == "（）是创新的源泉，是推动社会进步和发展的重要力量。"
    assert [option["value"] for option in first_problem["content"]["Options"]] == [
        "创业",
        "想象",
        "创意",
        "实践",
    ]
    assert multiple_problem["content"]["Body"] == "按思维内容的抽象性可划分为（）。"
    assert [option["value"] for option in multiple_problem["content"]["Options"]] == [
        "形象思维",
        "抽象思维",
        "灵感思维",
        "逆向思维",
    ]
    assert judgement_problem["content"]["Body"] == "想象是创新的源泉，是推动社会进步和发展的重要力量"


def test_is_problem_completed_supports_my_answer_and_my_answers():
    payload = load_sample_payload()
    problems = payload["data"]["problems"]

    assert is_problem_completed(problems[0]) is True
    assert is_problem_completed(problems[14]) is True
    assert is_problem_completed(problems[1]) is False


def test_get_problem_type_uses_content_type_field_only():
    problem = {
        "content": {
            "Type": "SingleChoice",
            "TypeText": "这行不参与判定",
            "problem_type": 2,
            "ProblemType": 6,
        }
    }

    assert get_problem_type(problem) == "SingleChoice"


def test_normalize_exercise_answer_handles_supported_problem_types():
    assert CommonFunReq.normalize_exercise_answer(
        '{"answer":["A"]}',
        "SingleChoice",
        ["A", "B", "C", "D"],
    ) == ["A"]
    assert CommonFunReq.normalize_exercise_answer(
        '{"answer":"C、A"}',
        "MultipleChoice",
        ["A", "B", "C", "D"],
    ) == ["A", "C"]
    assert CommonFunReq.normalize_exercise_answer(
        '{"answer":["正确"]}',
        "Judgement",
        ["true", "false"],
    ) == ["true"]


def test_extract_chat_completion_text_reads_first_choice_message():
    payload = {
        "id": "chatcmpl_test",
        "object": "chat.completion",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": '{"answer":["A"]}',
                },
                "finish_reason": "stop",
            }
        ],
    }

    assert CommonFunReq._extract_chat_completion_text(payload) == '{"answer":["A"]}'


class FakeYKTMain:
    classroom_id = 28898702
    user_id = 98566638
    course_id = 123456
    university_id = 4265
    uv_id = 4265


class FakeReq:
    def __init__(self, payload):
        self.payload = copy.deepcopy(payload)
        self.context_calls = []
        self.submissions = []

    def getSkuidAndCcid(self, classroom_id, node_id):
        return {"data": {"content_info": {"leaf_type_id": 14586682}}}

    def set_exercise_request_context(self, **kwargs):
        self.context_calls.append(kwargs)

    def get_exercise_list(self, leaf_type_id):
        return copy.deepcopy(self.payload)

    def solve_exercise_problem(self, problem_type, question_text, options):
        if problem_type == "MultipleChoice":
            return ["A", "B"]
        if problem_type == "Judgement":
            return ["true"]
        raise AssertionError(f"Unexpected problem type: {problem_type}")

    def exercise_problem_apply(self, classroom_id, problem_id, answer):
        self.submissions.append(
            {
                "classroom_id": classroom_id,
                "problem_id": problem_id,
                "answer": answer,
            }
        )
        return {"success": True}


class RetryFakeReq(FakeReq):
    def __init__(self, payload, success_attempt=2):
        super().__init__(payload)
        self._attempts_by_problem = {}
        self.success_attempt = success_attempt

    def solve_exercise_problem(self, problem_type, question_text, options):
        return ["A"]

    def exercise_problem_apply(self, classroom_id, problem_id, answer):
        self.submissions.append(
            {
                "classroom_id": classroom_id,
                "problem_id": problem_id,
                "answer": answer,
            }
        )
        attempt = self._attempts_by_problem.get(problem_id, 0) + 1
        self._attempts_by_problem[problem_id] = attempt
        if attempt < self.success_attempt:
            return {"success": False, "msg": "temporary failure"}
        return {
            "msg": "",
            "data": {
                "count": 1,
                "is_show_answer": False,
                "my_score": 0.0,
                "my_count": 1,
                "is_right": False,
                "is_correct": False,
                "submit_time": "2026-03-27 23:36",
                "exercise_is_show_answer": False,
                "my_answer": ["A"],
                "is_show_explain": False,
            },
            "success": True,
        }


def test_run_finish_only_submits_unfinished_questions(monkeypatch):
    raw_payload = {
        "data": {
            "exercise_id": 1,
            "font": "https://example.com/exam.ttf",
            "problems": [
                {
                    "index": 1,
                    "problem_id": 101,
                    "content": {
                        "Body": "encrypted single",
                        "Options": [{"key": "A", "value": "encrypted"}],
                        "Type": "SingleChoice",
                        "TypeText": "单选题",
                        "ProblemID": 101,
                    },
                    "user": {"my_answer": ["A"]},
                },
                {
                    "index": 2,
                    "problem_id": 202,
                    "content": {
                        "Body": "encrypted multi",
                        "Options": [
                            {"key": "A", "value": "encrypted"},
                            {"key": "B", "value": "encrypted"},
                            {"key": "C", "value": "encrypted"},
                        ],
                        "Type": "MultipleChoice",
                        "TypeText": "多选题",
                        "ProblemID": 202,
                    },
                    "user": {},
                },
                {
                    "index": 3,
                    "problem_id": 303,
                    "content": {
                        "Body": "encrypted judgement",
                        "Options": [
                            {"key": "true", "value": "正确"},
                            {"key": "false", "value": "错误"},
                        ],
                        "Type": "Judgement",
                        "TypeText": "判断题",
                        "ProblemID": 303,
                    },
                    "user": {},
                },
            ],
        }
    }
    decoded_payload = {
        "data": {
            "exercise_id": 1,
            "problems": [
                {
                    "index": 1,
                    "problem_id": 101,
                    "content": {
                        "Body": "已完成单选题",
                        "Options": [{"key": "A", "value": "答案"}],
                        "Type": "SingleChoice",
                        "TypeText": "单选题",
                        "ProblemID": 101,
                    },
                    "user": {"my_answer": ["A"]},
                },
                {
                    "index": 2,
                    "problem_id": 202,
                    "content": {
                        "Body": "未完成多选题",
                        "Options": [
                            {"key": "A", "value": "甲"},
                            {"key": "B", "value": "乙"},
                            {"key": "C", "value": "丙"},
                        ],
                        "Type": "MultipleChoice",
                        "TypeText": "多选题",
                        "ProblemID": 202,
                    },
                    "user": {},
                },
                {
                    "index": 3,
                    "problem_id": 303,
                    "content": {
                        "Body": "未完成判断题",
                        "Options": [
                            {"key": "true", "value": "正确"},
                            {"key": "false", "value": "错误"},
                        ],
                        "Type": "Judgement",
                        "TypeText": "判断题",
                        "ProblemID": 303,
                    },
                    "user": {},
                },
            ],
        }
    }
    fake_req = FakeReq(raw_payload)

    monkeypatch.setattr(
        exercise_module,
        "decode_exercise_payload",
        lambda payload, workdir=None: (copy.deepcopy(decoded_payload), {"x": "y"}),
    )

    learn_point = ExerciseLearnPoint({"id": 74729397, "name": "课后习题"})
    learn_point.initContext(FakeYKTMain(), fake_req)
    learn_point.runFinish()

    assert [submission["problem_id"] for submission in fake_req.submissions] == [202, 303]
    assert fake_req.submissions[0]["answer"] == ["A", "B"]
    assert fake_req.submissions[1]["answer"] == ["true"]


def test_run_finish_retries_until_success(monkeypatch):
    raw_payload = {
        "data": {
            "exercise_id": 1,
            "font": "https://example.com/exam.ttf",
            "problems": [
                {
                    "index": 1,
                    "problem_id": 909,
                    "content": {
                        "Body": "encrypted single",
                        "Options": [
                            {"key": "A", "value": "encrypted"},
                            {"key": "B", "value": "encrypted"},
                        ],
                        "Type": "SingleChoice",
                        "TypeText": "单选题",
                        "ProblemID": 909,
                    },
                    "user": {},
                }
            ],
        }
    }
    decoded_payload = {
        "data": {
            "exercise_id": 1,
            "problems": [
                {
                    "index": 1,
                    "problem_id": 909,
                    "content": {
                        "Body": "需要重试的单选题",
                        "Options": [
                            {"key": "A", "value": "甲"},
                            {"key": "B", "value": "乙"},
                        ],
                        "Type": "SingleChoice",
                        "TypeText": "单选题",
                        "ProblemID": 909,
                    },
                    "user": {},
                }
            ],
        }
    }
    fake_req = RetryFakeReq(raw_payload, success_attempt=2)
    sleep_calls = []

    monkeypatch.setattr(
        exercise_module,
        "decode_exercise_payload",
        lambda payload, workdir=None: (copy.deepcopy(decoded_payload), {"x": "y"}),
    )
    monkeypatch.setattr(exercise_module.time, "sleep", lambda seconds: sleep_calls.append(seconds))

    learn_point = ExerciseLearnPoint({"id": 74729397, "name": "课后习题"})
    learn_point.initContext(FakeYKTMain(), fake_req)
    learn_point.runFinish()

    assert len(fake_req.submissions) == 2
    assert all(item["problem_id"] == 909 for item in fake_req.submissions)
    assert sleep_calls == [20]


def test_problem_log_label_contains_homework_question_and_type():
    learn_point = ExerciseLearnPoint({"id": 1, "name": "课后习题"})
    label = learn_point._build_problem_log_label(
        {
            "type_text": "单选题",
            "question": "创新是什么？",
        }
    )

    assert "课后习题" in label
    assert "创新是什么？" in label
    assert "单选题" in label
