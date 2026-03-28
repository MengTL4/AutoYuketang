import requests
import logging

import config
from core.commonFunReq import CommonFunReq
from learnPoints.discussLearnPoint import DiscussLearnPoint
from learnPoints.exerciseLearnPoint import ExerciseLearnPoint
from learnPoints.videoLearnPoint import VideoLearnPoint
from utils.tools import handleNodes
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)

logger = logging.getLogger(__name__)

class YKTMain:
    def __init__(self):
        self.exerciseLearnPoints = []
        self.discussLearnPoints = []
        self.university_id = None
        self.videoLearnPoints = []
        self.req = CommonFunReq()
        self.courseList = None
        self.courseInfo = None
        self.cid = None
        self.sign = None
        self.uv_id = None
        self.classroom_id = None
        self.courseDetail = None
        self.courseNodeInfo = None
        self.userInfo = None
        self.user_id = None
        self.course_id = None

    def initCourseInfo(self, indexNum):
        self.courseList = self.req.getCourseList().get("data").get("list")[indexNum]
        self.university_id = self.courseList.get("course").get("university_id")

        self.req.headers["university-id"] = str(self.university_id)
        self.req.session.headers.update(self.req.headers)

        self.cid = self.courseList.get("classroom_id")
        self.classroom_id = self.courseList.get("classroom_id")

        self.courseDetail = self.req.getCourseDetail(self.classroom_id).get("data")
        self.course_id = self.courseDetail.get("course_id")
        self.uv_id = self.courseDetail.get("uv_id")
        self.sign = self.courseDetail.get("course_sign")
        self.userInfo = self.req.getUserBasicInfo(self.uv_id, self.classroom_id).get("data").get("user_info")
        self.user_id = self.userInfo.get("user_id")

        self.courseNodeInfo = (
            self.req.getCourseInfo(
                cid=self.cid,
                sign=self.sign,
                uv_id=self.uv_id,
                classroom_id=self.classroom_id,
            )
            .get("data")
            .get("course_chapter")
        )
        # 扁平化学习点
        learnPoint = handleNodes(self.courseNodeInfo)
        for node in learnPoint:
            if node.get("leaf_type") == 0:
                videoLearnPoint = VideoLearnPoint(node)
                videoLearnPoint.initContext(self, self.req)
                self.videoLearnPoints.append(videoLearnPoint)
            elif node.get("leaf_type") == 4:
                discussLearnPoint = DiscussLearnPoint(node)
                discussLearnPoint.initContext(self, self.req)
                self.discussLearnPoints.append(discussLearnPoint)
            elif node.get("leaf_type") == 6:
                exerciseLearnPoint = ExerciseLearnPoint(node)
                exerciseLearnPoint.initContext(self, self.req)
                self.exerciseLearnPoints.append(exerciseLearnPoint)

        # if config.api_key:
        #     for _ in self.discussLearnPoints:
        #         _.initProcess()
        #         _.runFinish()
        #     for _ in self.exerciseLearnPoints:
        #         _.initProcess()
        #         _.runFinish()
        # else:
        #     if self.discussLearnPoints:
        #         logger.warning("未配置api_key，跳过讨论学习点")
        #     if self.exerciseLearnPoints:
        #         logger.warning("未配置api_key，跳过练习学习点")

        for _ in self.videoLearnPoints:
            _.preInit()
            _.initProcess()
            _.runFinish()


if __name__ == "__main__":
    ykt = YKTMain()
    ykt.initCourseInfo(3)
