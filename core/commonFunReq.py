import requests
from datetime import datetime
import os
from openai import OpenAI
import config

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
        client = OpenAI(
            api_key=config.api_key,
            base_url="https://api.deepseek.com")
        # text = '''
        # <div class="custom_ueditor_cn_body"><ol class=" list-paddingleft-2" style="list-style-type: decimal;"><li><p>结合自己的工作、学习和生活，谈谈如何用“创+”适应“新常态”？</p></li><li><p>从工作、学习和生活等角度看，请指出当下创新创业面临的3-5个痛点、堵点。</p></li><li><p>根据小米生态链模式及AIOT生态圈，请谈一谈小米创新所需的技术因素、市场因素、设计因素、战略因素、组织管理因素等分别体现在哪些地方？<br /></p></li></ol></div>
        # '''
        promote = '''
        请回答以下问题，输出要求：
1. 去掉所有Markdown格式符号（包括#、##、###、**、---、- 列表符号、## 二级标题等）；
2. 输出纯文本内容，段落之间用换行分隔，保持内容的逻辑结构完整；
'''
        response = client.chat.completions.create(model="deepseek-chat",messages=[{"role": "user", "content": f"{promote}+{text}"},],stream=False)
        return response.choices[0].message.content

    def commentList(self,topic_id):
        resp = self.session.get(self.baseUrl + f"/v/discussion/v2/comment/list/{topic_id}/?offset=0&limit=100&web=web")
        return resp.json()

    def get_exercise_list(self,leaf_type_id):
        resp = self.session.get(self.baseUrl + f"/mooc-api/v1/lms/exercise/get_exercise_list/{leaf_type_id}/")
        return resp.json()



if __name__ == "__main__":
    c = CommonFunReq()
    # print(c.getCourseList())
    data = c.discussionInfo(28898702,14586682,74729388)
    print(data)

