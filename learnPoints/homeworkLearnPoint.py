# import logging
#
# from learnPoints.baseLearnPoint import BaseLearnPoint
#
# logger = logging.getLogger(__name__)
# class HomeWorkLearnPoint(BaseLearnPoint):
#     def __init__(self, nodes):
#         super().__init__()
#         self.homeworkInfo = None
#         self.leaf_type_id = None
#         self.node_id = nodes.get("id")
#         self.node_name = nodes.get("name")
#
#     def initProcess(self):
#         self.leaf_type_id = self.req.getSkuidAndCcid(self.classroom_id, self.node_id).get("data").get("content_info").get("leaf_type_id")
#         self.homeworkInfo = self.req.get_exercise_list(self.leaf_type_id).get("data").get("problems")
#
#
#     def runFinish(self):
#
#         if self.checkFinish():
#             logger.info(f"{self.node_name}学习点已完成，跳过")
#             return
#         else:
#             logger.info(f"开始{self.node_name}")
#             result = self.req.dsResult(self.discussText)
#             message = self.req.comment(self.user_id, self.topic_id, result).get("data").get("message")
#             logger.info(f"{self.node_name}完成，状态{message}")
#
#     def checkFinish(self):
#         data = self.req.commentList(self.topic_id).get("new_comment_list").get("results")
#         for _ in data:
#             if _.get("user_info").get("user_id") == self.user_id:
#                 return True
#             else:
#                 return False
#         return None
#
#
