import json
import re
import requests
from datetime import datetime
import config


AI_CHAT_COMPLETIONS_URL = "https://api.deepseek.com/chat/completions"
AI_MODEL = "deepseek-chat"
PROBLEM_TYPE_LABELS = {
    "SingleChoice": "单选题",
    "MultipleChoice": "多选题",
    "Judgement": "判断题",
}


class CommonFunReq:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,ja;q=0.7,zh-TW;q=0.6",
            "Connection": "keep-alive",
            "xtbz": "ykt",
            "Cookie": config.Cookie,
        }
        cookie_header = self.headers.get("Cookie", "")
        for cookie_item in cookie_header.split(";"):
            cookie_item = cookie_item.strip()
            if cookie_item.startswith("csrftoken="):
                self.headers["X-CSRFToken"] = cookie_item.split("=", 1)[1]
                break
        self.baseUrl = "https://www.yuketang.cn"
        self.session = requests.session()
        self.session.headers.update(self.headers)

    @staticmethod
    def _extract_chat_completion_text(payload):
        choices = payload.get("choices")
        if not isinstance(choices, list) or not choices:
            raise ValueError(f"Chat completions payload is missing choices: {payload}")

        message = choices[0].get("message") or {}
        content = message.get("content")
        if isinstance(content, str) and content.strip():
            return content.strip()

        if isinstance(content, list):
            texts = []
            for item in content:
                if isinstance(item, dict) and item.get("text"):
                    texts.append(str(item["text"]))
            if texts:
                return "".join(texts).strip()

        raise ValueError(f"Unable to extract text from chat completions payload: {payload}")

    def _request_model_text(self, prompt):
        if not config.api_key:
            raise ValueError("config.api_key is required for AI requests")

        response = requests.post(
            AI_CHAT_COMPLETIONS_URL,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {config.api_key}",
            },
            json={
                "model": AI_MODEL,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                "stream": False,
            },
            timeout=120,
        )

        try:
            payload = response.json()
        except ValueError as exc:
            raise ValueError(
                f"AI gateway returned a non-JSON response: {response.text[:500]}"
            ) from exc

        if not response.ok:
            error_payload = payload.get("error")
            if isinstance(error_payload, dict):
                message = error_payload.get("message") or error_payload
            else:
                message = error_payload or payload
            raise ValueError(f"AI request failed ({response.status_code}): {message}")

        return self._extract_chat_completion_text(payload)

    def getCourseList(self):
        resp = self.session.get(self.baseUrl + "/v2/api/web/courses/list?identity=2")
        return resp.json()

    def getCourseInfo(self, cid, sign, uv_id, classroom_id):
        resp = self.session.get(
            self.baseUrl
            + f"/mooc-api/v1/lms/learn/course/chapter?cid={cid}&sign={sign}&term=latest&uv_id={uv_id}&classroom_id={classroom_id}"
        )
        return resp.json()

    def getCourseDetail(self, classroom_id):
        resp = self.session.get(
            self.baseUrl + f"/v2/api/web/classrooms/{classroom_id}?role=5"
        )
        return resp.json()

    def videoHeartbeat(self, heart_data, classroom_id=None):
        if isinstance(heart_data, dict) and "heart_data" in heart_data:
            payload = heart_data
        else:
            payload = {"heart_data": heart_data}

        if classroom_id is None:
            packet_list = payload.get("heart_data", [])
            if packet_list:
                classroom_id = packet_list[0].get("classroomid")

        params = None
        if classroom_id is not None:
            params = {"classroom_id": str(classroom_id)}

        resp = self.session.post(
            self.baseUrl + "/video-log/heartbeat/", params=params, json=payload
        )
        return resp.json()

    def videoTrack(self, data):
        classroom_id = data.get("data", {}).get("properties", {}).get("classroom_id")
        params = None
        if classroom_id is not None:
            params = {"classroom_id": str(classroom_id)}

        resp = self.session.post(
            self.baseUrl + "/video-log/log/track/", params=params, json=data
        )
        return resp.json()

    def getVideoWatchProgress(self, course_id, user_id, classroom_id, video_id):
        resp = self.session.get(
            self.baseUrl
            + f"/video-log/get_video_watch_progress?cid={course_id}&user_id={user_id}&classroom_id={classroom_id}&video_type=video&vtype=rate&video_id={video_id}&snapshot=1"
        )
        return resp.json()

    def getSkuidAndCcid(self, classroom_id, node_id):
        self.headers["classroom-id"] = str(classroom_id)
        self.session.headers.update(self.headers)
        resp = self.session.get(
            self.baseUrl + f"/mooc-api/v1/lms/learn/leaf_info/{classroom_id}/{node_id}/"
        )
        return resp.json()

    def getUserBasicInfo(self, uv_id, classroom_id):
        resp = self.session.get(
            self.baseUrl
            + f"/edu_admin/get_user_basic_info/?no_loading=true&term=latest&uv_id={uv_id}&classroom_id={classroom_id}"
        )
        return resp.json()

    def getLoginUserId(self, classroom_id):
        resp = self.session.get(
            self.baseUrl
            + f"/c27/online_courseware/agent/entity_agents/?entity_type=1&entity_id={classroom_id}&category=1&has_role=1"
        )
        return resp.json()

    def leaf_level_info(self, node_id, uv_id, classroom_id):
        resp = self.session.get(
            self.baseUrl
            + f"/edu_admin/leaf_level_info/?leaf_level_id={node_id}&no_loading=false&term=latest&uv_id={uv_id}&classroom_id={classroom_id}"
        )
        return resp.json()

    def extra_info(self, classroom_id):
        resp = self.session.get(
            self.baseUrl
            + f"/v/course_meta/v2/classroom/extra-info/?classroom_id={classroom_id}"
        )
        return resp.json()

    def settings(self, classroom_id):
        resp = self.session.get(
            self.baseUrl
            + f"/v/course_meta/v2/university/settings?source_type=1&source_id={classroom_id}"
        )
        return resp.json()

    def drag(self, sku_id):
        resp = self.session.get(
            self.baseUrl + f"/mooc-api/v1/lms/learn/video/drag?sku_id={sku_id}"
        )
        return resp.json()

    def watermark(self, uv_id, classroom_id):
        resp = self.session.get(
            self.baseUrl
            + f"/c27/api/v1/platfrom/watermark?uv_id={uv_id}&classroom_id={classroom_id}"
        )
        return resp.json()

    def playurl(self, ccid):
        resp = self.session.get(
            self.baseUrl
            + f"/api/open/audiovideo/playurl?video_id={ccid}&provider=cc&file_type=1&is_single=0&domain=www.yuketang.cn"
        )
        return resp.json()

    def subtitle_list(self, cc_id):
        resp = self.session.get(
            self.baseUrl + f"/api/open/yunpan/video/subtitle/list?cc_id={cc_id}"
        )
        return resp.json()

    def s_t_g_p(self, ccid):
        data = {"c_d": f"{ccid}"}
        resp = self.session.post(
            self.baseUrl + f"/mooc-api/v1/lms/service/s_t_g_p/", json=data
        )
        return resp.json()

    def s_t_c(self, node_id):
        resp = self.session.get(
            self.baseUrl + f"/c27/online_courseware/instance/s_t_c/{node_id}/"
        )
        return resp.json()

    def subtitle_parse(self, ccid):
        resp = self.session.get(
            self.baseUrl
            + f"/mooc-api/v1/lms/service/subtitle_parse/?c_d={ccid}&lg=0&_={int(datetime.now().timestamp() * 1000)}"
        )
        return resp.json()

    def train_classes(self, classroom_id):
        data = {"classroom_id": classroom_id, "no_loading": True}
        resp = self.session.post(
            self.baseUrl + f"/train_platform/v1/classroom/train_classes/", json=data
        )
        return resp.json()

    def discussionInfo(self, classroom_id,sku_id,node_id):
        resp = self.session.get(self.baseUrl+f"/v/discussion/v2/unit/discussion/?classroom_id={classroom_id}&sku_id={sku_id}&leaf_id={node_id}&topic_type=4&channel=xt")
        return resp.json()

    def comment(self,user_id,topic_id,text):
        data = {"to_user": user_id, "topic_id": topic_id,"content":{"text":text,"upload_images":[],"accessory_list":[]}}
        resp = self.session.post(self.baseUrl + f"/v/discussion/v2/comment/", json=data)
        return resp.json()

    def dsResult(self,text):
        # text = '''
        # <div class="custom_ueditor_cn_body"><ol class=" list-paddingleft-2" style="list-style-type: decimal;"><li><p>结合自己的工作、学习和生活，谈谈如何用“创+”适应“新常态”？</p></li><li><p>从工作、学习和生活等角度看，请指出当下创新创业面临的3-5个痛点、堵点。</p></li><li><p>根据小米生态链模式及AIOT生态圈，请谈一谈小米创新所需的技术因素、市场因素、设计因素、战略因素、组织管理因素等分别体现在哪些地方？<br /></p></li></ol></div>
        # '''
        promote = '''
        请回答以下问题，输出要求：
1. 去掉所有Markdown格式符号（包括#、##、###、**、---、- 列表符号、## 二级标题等）；
2. 输出纯文本内容，段落之间用换行分隔，保持内容的逻辑结构完整；
'''
        return self._request_model_text(f"{promote}+{text}")

    def set_exercise_request_context(
        self,
        classroom_id,
        university_id,
        uv_id,
        node_id=None,
        leaf_type_id=None,
    ):
        referer = None
        if node_id is not None and leaf_type_id is not None:
            referer = (
                f"{self.baseUrl}/v2/web/cloud/student/exercise/"
                f"{classroom_id}/{node_id}/{leaf_type_id}"
            )

        self.headers.update(
            {
                "classroom-id": str(classroom_id),
                "university-id": str(university_id),
                "uv-id": str(uv_id),
                "Xt-Agent": "web",
                "X-Client": "web",
                "Origin": self.baseUrl,
            }
        )
        if referer:
            self.headers["Referer"] = referer
        self.session.headers.update(self.headers)

    @staticmethod
    def _strip_code_fences(text):
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)
        return cleaned.strip()

    @staticmethod
    def _extract_first_json_block(text):
        cleaned = CommonFunReq._strip_code_fences(text)
        for opening, closing in (("{", "}"), ("[", "]")):
            start = cleaned.find(opening)
            if start == -1:
                continue
            depth = 0
            for index in range(start, len(cleaned)):
                char = cleaned[index]
                if char == opening:
                    depth += 1
                elif char == closing:
                    depth -= 1
                    if depth == 0:
                        return cleaned[start : index + 1]
        return None

    @staticmethod
    def _coerce_answer_value(raw_answer):
        if raw_answer is None:
            return []
        if isinstance(raw_answer, bool):
            return ["true" if raw_answer else "false"]
        if isinstance(raw_answer, dict):
            if "answer" in raw_answer:
                return CommonFunReq._coerce_answer_value(raw_answer.get("answer"))
            if "answers" in raw_answer:
                return CommonFunReq._coerce_answer_value(raw_answer.get("answers"))
            if "result" in raw_answer:
                return CommonFunReq._coerce_answer_value(raw_answer.get("result"))
            truthy_keys = [str(key).strip() for key, value in raw_answer.items() if value]
            if truthy_keys:
                return truthy_keys
            return []
        if isinstance(raw_answer, list):
            values = []
            for item in raw_answer:
                values.extend(CommonFunReq._coerce_answer_value(item))
            return values
        return [str(raw_answer).strip()]

    @staticmethod
    def _normalize_judgement_value(value):
        lowered = value.strip().lower()
        if lowered in {"true", "t", "yes", "y", "对", "正确", "是"}:
            return "true"
        if lowered in {"false", "f", "no", "n", "错", "错误", "否"}:
            return "false"
        if "正确" in value or "对" in value:
            return "true"
        if "错误" in value or "错" in value:
            return "false"
        return None

    @staticmethod
    def normalize_exercise_answer(response_text, problem_type, valid_keys):
        if problem_type not in PROBLEM_TYPE_LABELS:
            raise ValueError(f"Unsupported exercise type: {problem_type}")
        if not response_text or not response_text.strip():
            raise ValueError("AI did not return an answer")

        parsed_payload = CommonFunReq._strip_code_fences(response_text)
        json_block = CommonFunReq._extract_first_json_block(response_text)
        if json_block:
            try:
                parsed_payload = json.loads(json_block)
            except json.JSONDecodeError:
                parsed_payload = CommonFunReq._strip_code_fences(response_text)

        values = CommonFunReq._coerce_answer_value(parsed_payload)
        if problem_type == "Judgement":
            normalized = []
            for value in values:
                judgement_value = CommonFunReq._normalize_judgement_value(value)
                if judgement_value:
                    normalized.append(judgement_value)
            if len(normalized) != 1:
                raise ValueError(f"Invalid judgement answer: {response_text}")
            if normalized[0] not in valid_keys:
                raise ValueError(f"Unsupported judgement key: {normalized[0]}")
            return normalized

        extracted = []
        for value in values:
            extracted.extend(re.findall(r"[A-Z]", value.upper()))

        valid_key_order = {key: index for index, key in enumerate(valid_keys)}
        seen = set()
        normalized = []
        for key in extracted:
            if key not in valid_key_order or key in seen:
                continue
            seen.add(key)
            normalized.append(key)

        normalized.sort(key=valid_key_order.__getitem__)

        if problem_type == "SingleChoice" and len(normalized) != 1:
            raise ValueError(f"Invalid single choice answer: {response_text}")
        if problem_type == "MultipleChoice" and not normalized:
            raise ValueError(f"Invalid multiple choice answer: {response_text}")
        return normalized

    def solve_exercise_problem(self, problem_type, question_text, options):
        if problem_type not in PROBLEM_TYPE_LABELS:
            raise ValueError(f"Unsupported exercise type: {problem_type}")
        option_lines = "\n".join(
            f"{option.get('key')}. {option.get('value')}" for option in options
        )
        valid_keys = [
            str(option.get("key")).strip() for option in options if option.get("key") is not None
        ]
        prompt = (
            "你正在回答雨课堂客观题。\n"
            f"题型: {PROBLEM_TYPE_LABELS[problem_type]} ({problem_type})\n"
            f"题目: {question_text}\n"
            f"选项:\n{option_lines}\n\n"
            "只返回 JSON，不要解释，不要 Markdown，不要额外文字。\n"
            '返回格式必须是 {"answer":["..."]}。\n'
            "规则:\n"
            f"- 合法答案键只能来自: {', '.join(valid_keys)}\n"
            "- 单选题只能返回 1 个答案键。\n"
            "- 多选题返回多个答案键。\n"
            "- 判断题只能返回 true 或 false。\n"
        )
        response_text = self._request_model_text(prompt)
        return self.normalize_exercise_answer(response_text, problem_type, valid_keys)

    def commentList(self,topic_id):
        resp = self.session.get(self.baseUrl + f"/v/discussion/v2/comment/list/{topic_id}/?offset=0&limit=100&web=web")
        return resp.json()

    def get_exercise_list(self,leaf_type_id):
        resp = self.session.get(self.baseUrl + f"/mooc-api/v1/lms/exercise/get_exercise_list/{leaf_type_id}/")
        return resp.json()

    def exercise_problem_apply(self,classroom_id,problem_id,answer):
        send_data = {"classroom_id":classroom_id,"problem_id":problem_id,"answer":answer}
        resp = self.session.post(self.baseUrl + "/mooc-api/v1/lms/exercise/problem_apply/", json=send_data)
        return resp.json()

