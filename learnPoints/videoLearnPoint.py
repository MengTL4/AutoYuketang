import logging
import sys
import time
import uuid

import requests

from learnPoints.baseLearnPoint import BaseLearnPoint
from datetime import datetime

from utils.tools import generate_original_id

logger = logging.getLogger(__name__)


class VideoLearnPoint(BaseLearnPoint):
    def __init__(self, nodes):
        super().__init__()
        self.finish = None
        self.node_id = nodes.get("id")
        self.node_name = nodes.get("name")
        self.ccid = None
        self.sku_id = None
        self.video_length = None
        self.heartBeatBase = {
            "i": 5,
            "et": None,
            "p": "web",
            "n": "ali-cdn.xuetangx.com",
            "lob": "ykt",
            "cp": 0,
            "fp": 0,
            "tp": 0,
            "sp": 1,
            "ts": str(int(datetime.now().timestamp() * 1000)),
            "u": self.user_id,
            "uip": "",
            "c": self.course_id,
            "v": self.node_id,
            "skuid": self.sku_id,
            "classroomid": self.classroom_id,
            "cc": self.ccid,
            "d": self.video_length,
            "pg": f"{self.node_id}_{uuid.uuid4().hex[:4]}",
            "sq": None,
            "t": "video",
            "cards_id": 0,
            "slide": 0,
            "v_url": "",
        }

    def _render_progress(self, current_second, total_seconds):
        if not sys.stdout.isatty():
            return

        bar_width = 30
        if total_seconds <= 0:
            percent = 0.0
            display_current = 0.0
            display_total = 0.0
        else:
            display_total = float(total_seconds)
            display_current = min(max(float(current_second), 0.0), display_total)
            percent = display_current / display_total

        filled = int(bar_width * percent)
        bar = "#" * filled + "-" * (bar_width - filled)
        print(
            f"\r{self.node_name} [{bar}] {percent * 100:6.2f}% ({display_current:.1f}/{display_total:.1f}s)",
            end="",
            flush=True,
        )

    def preInit(self):
        if self.req is None:
            raise RuntimeError("Request client is not initialized")

        self.req.headers["classroom-id"] = str(self.classroom_id)
        self.req.headers["Referer"] = (
            f"https://www.yuketang.cn/v2/web/xcloud/video-student/{self.classroom_id}/{self.node_id}"
        )
        self.req.headers["university-id"] = str(self.university_id)
        self.req.headers["uv-id"] = str(self.uv_id)
        self.req.session.headers.update(self.req.headers)

        self.req.leaf_level_info(self.node_id, self.university_id, self.classroom_id)
        self.req.extra_info(self.classroom_id)
        login_user_id = (
            self.req.getLoginUserId(self.classroom_id).get("data").get("login_user_id")
        )
        self.req.settings(self.classroom_id)
        data = self.req.getSkuidAndCcid(self.classroom_id, self.node_id)
        self.sku_id = data.get("data", {}).get("sku_id")
        self.ccid = (
            data.get("data", {}).get("content_info", {}).get("media", {}).get("ccid")
        )
        self.req.drag(self.sku_id)
        self.req.getVideoWatchProgress(
            self.course_id, self.user_id, self.classroom_id, self.node_id
        )
        self.req.watermark(self.uv_id, self.classroom_id)
        self.req.playurl(self.ccid)
        jsonData = {
            "uip": "",
            "data": {
                "platform": 2,
                "terminal_type": "Web",
                "time": int(datetime.now().timestamp() * 1000),
                "language": "zh_CN",
                "original_id": generate_original_id(),
                "distinct_id": str(login_user_id),
                "event": "page_view",
                "properties": {
                    "channel": "",
                    "classroom_id": self.classroom_id,
                    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36",
                    "page_name": "雨课堂",
                    "host": "www.yuketang.cn",
                    "url": f"https://www.yuketang.cn/v2/web/xcloud/video-student/{self.classroom_id}/{self.node_id}",
                    "referer": f"https://www.yuketang.cn/v2/web/studentLog/{self.classroom_id}?university_id={self.university_id}&platform_id=3&classroom_id={self.classroom_id}&content_url=",
                    "original_referrer": f"https://www.yuketang.cn/v2/web/studentLog/{self.classroom_id}?university_id={self.university_id}&platform_id=3&classroom_id={self.classroom_id}&content_url=",
                },
            },
            "ts_ms": int(datetime.now().timestamp() * 1000),
        }
        self.req.videoTrack(jsonData)
        self.req.subtitle_list(self.ccid)
        self.req.s_t_g_p(self.ccid)
        self.req.s_t_c(self.node_id)
        hd = {"heart_data": []}
        self.req.videoHeartbeat(hd, self.classroom_id)
        self.req.subtitle_parse(self.ccid)
        # login_user_id = self.req.getLoginUserId(self.classroom_id).get("data").get("login_user_id")

    def initProcess(self):
        if self.req is None:
            raise RuntimeError("Request client is not initialized")

        heartBeatBaseList = []
        # data = self.req.getSkuidAndCcid(self.classroom_id, self.node_id)
        # self.sku_id = data.get("data", {}).get("sku_id")
        # self.ccid = (
        #     data.get("data", {}).get("content_info", {}).get("media", {}).get("ccid")
        # )
        self.heartBeatBase["et"] = "loadstart"
        self.heartBeatBase["ts"] = str(int(datetime.now().timestamp() * 1000))
        self.heartBeatBase["u"] = self.user_id
        self.heartBeatBase["c"] = self.course_id
        self.heartBeatBase["v"] = self.node_id
        self.heartBeatBase["skuid"] = self.sku_id
        self.heartBeatBase["classroomid"] = str(self.classroom_id)
        self.heartBeatBase["cc"] = self.ccid
        self.heartBeatBase["d"] = 0
        self.heartBeatBase["pg"] = f"{self.node_id}_{uuid.uuid4().hex[:4]}"
        self.heartBeatBase["sq"] = 1
        heartBeatBaseList.append(dict(self.heartBeatBase))

        data2 = self.req.getVideoWatchProgress(
            self.course_id, self.user_id, self.classroom_id, self.node_id
        )
        self.video_length = (
            data2.get("data").get(f"{self.node_id}", {}).get("video_length")
        )
        self.finish = data2.get("data").get(f"{self.node_id}", {}).get("completed")
        self.heartBeatBase["d"] = self.video_length
        self.heartBeatBase["et"] = "loadeddata"
        self.heartBeatBase["sq"] = 2
        heartBeatBaseList.append(dict(self.heartBeatBase))

        self.heartBeatBase["et"] = "play"
        self.heartBeatBase["sq"] = 3
        heartBeatBaseList.append(dict(self.heartBeatBase))

        self.heartBeatBase["et"] = "playing"
        self.heartBeatBase["sq"] = 4
        heartBeatBaseList.append(dict(self.heartBeatBase))

        self.heartBeatBase["et"] = "waiting"
        self.heartBeatBase["sq"] = 5
        heartBeatBaseList.append(dict(self.heartBeatBase))

        self.heartBeatBase["et"] = "playing"
        self.heartBeatBase["sq"] = 6
        heartBeatBaseList.append(dict(self.heartBeatBase))
        self.req.videoHeartbeat(heartBeatBaseList, self.classroom_id)
        self.req.getVideoWatchProgress(
            self.course_id, self.user_id, self.classroom_id, self.node_id
        )

    def runFinish(self):
        if self.req is None:
            raise RuntimeError("Request client is not initialized")

        if self.checkFinish():
            logger.info(f"{self.node_name}学习点已完成，跳过")

            return
        else:
            logger.info(f"开始刷{self.node_name}学习点")

            total_seconds = float(self.video_length or 0)
            sq = 7
            last_cp = 0.0
            heart_beat_batch = []

            if total_seconds <= 0:
                latest_progress = self.req.getVideoWatchProgress(
                    self.course_id, self.user_id, self.classroom_id, self.node_id
                )
                total_seconds = float(
                    latest_progress.get("data", {})
                    .get(f"{self.node_id}", {})
                    .get("video_length")
                    or 0
                )
                if total_seconds > 0:
                    self.video_length = total_seconds
                    self.heartBeatBase["d"] = total_seconds

            if total_seconds <= 0:
                logger.warning(
                    f"{self.node_name}学习点时长为0，使用最小心跳上报（不显示进度条）"
                )
                end_packet = dict(self.heartBeatBase)
                end_packet["cp"] = 0
                end_packet["et"] = "videoend"
                end_packet["sq"] = sq
                end_packet["ts"] = str(int(time.time() * 1000))
                self.req.videoHeartbeat([end_packet], self.classroom_id)
                self.req.getVideoWatchProgress(
                    self.course_id, self.user_id, self.classroom_id, self.node_id
                )
                logger.info(f"{self.node_name}学习点已完成")
                return

            self._render_progress(0, total_seconds)
            current_second = 5.0
            while current_second < total_seconds:
                wait_seconds = current_second - last_cp
                if wait_seconds > 0:
                    time.sleep(wait_seconds)

                packet = dict(self.heartBeatBase)
                packet["cp"] = round(current_second, 1)
                packet["et"] = "heartbeat"
                packet["sq"] = sq
                packet["ts"] = str(int(time.time() * 1000))
                heart_beat_batch.append(packet)
                sq += 1
                last_cp = packet["cp"]
                self._render_progress(last_cp, total_seconds)

                if len(heart_beat_batch) == 6:
                    self.req.videoHeartbeat(heart_beat_batch, self.classroom_id)
                    self.req.getVideoWatchProgress(
                        self.course_id, self.user_id, self.classroom_id, self.node_id
                    )
                    logger.info(
                        f"{self.node_name}学习点进度 {last_cp:.1f}/{total_seconds:.1f}s"
                    )
                    heart_beat_batch = []

                current_second = round(current_second + 5.0, 1)

            if last_cp < total_seconds:
                wait_seconds = total_seconds - last_cp
                if wait_seconds > 0:
                    time.sleep(wait_seconds)

                end_packet = dict(self.heartBeatBase)
                end_packet["cp"] = total_seconds
                end_packet["et"] = "videoend"
                end_packet["sq"] = sq
                end_packet["ts"] = str(int(time.time() * 1000))
                heart_beat_batch.append(end_packet)
            elif heart_beat_batch:
                heart_beat_batch[-1]["et"] = "videoend"
                heart_beat_batch[-1]["cp"] = total_seconds
                heart_beat_batch[-1]["ts"] = str(int(time.time() * 1000))

            if heart_beat_batch:
                self.req.videoHeartbeat(heart_beat_batch, self.classroom_id)
                self.req.getVideoWatchProgress(
                    self.course_id, self.user_id, self.classroom_id, self.node_id
                )
                logger.info(
                    f"{self.node_name}学习点进度 {total_seconds:.1f}/{total_seconds:.1f}s"
                )
                self.req.train_classes(self.classroom_id)

            self._render_progress(total_seconds, total_seconds)
            print()
            logger.info(f"{self.node_name}学习点已完成")

    def checkFinish(self):
        if self.finish == 1:
            return True
        else:
            return False
