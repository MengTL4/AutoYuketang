from __future__ import annotations
from typing import TYPE_CHECKING

from core.commonFunReq import CommonFunReq
# if TYPE_CHECKING:
#     from yktMain import YKTMain

class BaseLearnPoint:
    def __init__(self) -> None:
        self.uv_id = None
        self.university_id = None
        self.course_id = None
        self.user_id = None
        self.classroom_id = None
        self.ykt_main = None
        self.req = None
        self.node_id = None
        self.node_name = None

    def initContext(self, yktMain: "YKTMain", req: CommonFunReq):
        self.ykt_main = yktMain
        self.req = req
        self.classroom_id = yktMain.classroom_id
        self.user_id = yktMain.user_id
        self.course_id = yktMain.course_id
        self.university_id = yktMain.university_id
        self.uv_id = yktMain.uv_id

    def runFinish(self):
        pass
