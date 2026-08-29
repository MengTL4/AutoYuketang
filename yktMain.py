import requests
import ctypes
import logging
import sys

import config
from core.commonFunReq import CommonFunReq
from learnPoints.discussLearnPoint import DiscussLearnPoint
from learnPoints.exerciseLearnPoint import ExerciseLearnPoint
from learnPoints.examLearnPoint import ExamLearnPoint
from learnPoints.videoLearnPoint import VideoLearnPoint
from utils.tools import handleNodes
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)

logger = logging.getLogger(__name__)


def _prevent_system_sleep():
    """阻止系统自动睡眠（屏幕允许关闭）。"""
    if sys.platform != "win32":
        return
    ES_CONTINUOUS = 0x80000000
    ES_SYSTEM_REQUIRED = 0x00000001
    ctypes.windll.kernel32.SetThreadExecutionState(
        ES_CONTINUOUS | ES_SYSTEM_REQUIRED
    )


def _allow_system_sleep():
    """恢复系统正常睡眠策略。"""
    if sys.platform != "win32":
        return
    ES_CONTINUOUS = 0x80000000
    ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)

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
        self._leaf_5_nodes = []

    def _handle_exam(self, node):
        if not config.api_key:
            logger.warning("未配置 api_key，跳过期末考试自动答题")
            return
        if not config.X_ACCESS_TOKEN:
            logger.warning("未配置 X_ACCESS_TOKEN，跳过期末考试自动答题")
            return

        node_id = node.get("id")
        self.req.headers["classroom-id"] = str(self.classroom_id)
        self.req.session.headers.update(self.req.headers)

        try:
            leaf_info = self.req.getSkuidAndCcid(self.classroom_id, node_id)
            exam_id = (
                leaf_info.get("data", {})
                .get("content_info", {})
                .get("leaf_type_id")
            )
        except Exception as exc:
            logger.warning(f"获取期末考试信息失败: {exc}")
            return

        if not exam_id:
            logger.warning("未找到期末考试 ID")
            return

        logger.info(f"发现期末考试，exam_id={exam_id}")
        exam = ExamLearnPoint(node)
        exam.init_context(self.classroom_id, self.university_id, exam_id)
        exam.run(self.req)

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
            elif node.get("leaf_type") == 5:
                # 期末考试
                self._leaf_5_nodes.append(node)

        # 处理期末考试（优先）
        for node in getattr(self, "_leaf_5_nodes", []):
            self._handle_exam(node)

        if config.api_key:
            for _ in self.discussLearnPoints:
                _.initProcess()
                _.runFinish()
            for _ in self.exerciseLearnPoints:
                _.initProcess()
                _.runFinish()
        else:
            if self.discussLearnPoints:
                logger.warning("未配置api_key，跳过讨论学习点")
            if self.exerciseLearnPoints:
                logger.warning("未配置api_key，跳过练习学习点")

        for _ in self.videoLearnPoints:
            _.preInit()
            _.initProcess()
            _.runFinish()


if __name__ == "__main__":
    logger.info("已阻止系统自动睡眠（屏幕可正常关闭），脚本结束后自动恢复")
    _prevent_system_sleep()
    try:
        ykt = YKTMain()
        ykt.initCourseInfo(2)
    finally:
        _allow_system_sleep()
        logger.info("已恢复系统正常睡眠策略")
