import logging
import sys
import time
import uuid

import requests

from learnPoints.baseLearnPoint import BaseLearnPoint
from datetime import datetime

from utils.tools import generate_original_id

logger = logging.getLogger(__name__)

PLAYBACK_SPEED = 2
HEARTBEAT_INTERVAL_SECONDS = 5.0
HEARTBEAT_PROGRESS_SECONDS = HEARTBEAT_INTERVAL_SECONDS * PLAYBACK_SPEED


class VideoLearnPoint(BaseLearnPoint):
    def __init__(self, nodes):
        super().__init__()
        self.finish = None
        self.node_id = nodes.get("id")
        self.node_name = nodes.get("name")
        self.ccid = None
        self.sku_id = None
        self.video_length = None
        self.watch_length = 0.0
        self.last_point = 0.0
        self.resume_from = 0.0
        self.next_heartbeat_sq = 1
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

    @staticmethod
    def _safe_float(value, default=0.0):
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _clamp_progress(value, total_seconds):
        value = max(float(value), 0.0)
        if total_seconds > 0:
            return min(value, float(total_seconds))
        return value

    def _select_resume_point(self, video_data, total_seconds):
        if video_data.get("completed") == 1:
            return 0.0

        if video_data.get("last_point") is not None:
            resume_from = self._safe_float(video_data.get("last_point"))
        else:
            resume_from = max(self._safe_float(video_data.get("watch_length")) - 1, 0.0)

        return self._clamp_progress(resume_from, total_seconds)

    def _set_heartbeat_state(self, event_type, cp, sq, sp=None, duration=None):
        if sp is None:
            sp = self.heartBeatBase.get("sp", 1)
        if duration is None:
            duration = self.heartBeatBase.get("d")

        self.heartBeatBase["et"] = event_type
        self.heartBeatBase["cp"] = round(float(cp), 1)
        self.heartBeatBase["sp"] = sp
        self.heartBeatBase["d"] = duration
        self.heartBeatBase["sq"] = sq
        self.heartBeatBase["ts"] = str(int(time.time() * 1000))
        return dict(self.heartBeatBase)

    def _send_video_end(self, cp, sq):
        end_packet = self._set_heartbeat_state(
            "videoend", cp, sq, sp=PLAYBACK_SPEED, duration=self.video_length
        )
        self.req.videoHeartbeat([end_packet], self.classroom_id)
        self.req.getVideoWatchProgress(
            self.course_id, self.user_id, self.classroom_id, self.node_id
        )
        self.req.train_classes(self.classroom_id)

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
        self.heartBeatBase["u"] = self.user_id
        self.heartBeatBase["c"] = self.course_id
        self.heartBeatBase["v"] = self.node_id
        self.heartBeatBase["skuid"] = self.sku_id
        self.heartBeatBase["classroomid"] = str(self.classroom_id)
        self.heartBeatBase["cc"] = self.ccid
        self.heartBeatBase["pg"] = f"{self.node_id}_{uuid.uuid4().hex[:4]}"
        heartBeatBaseList.append(
            self._set_heartbeat_state("loadstart", 0, 1, sp=1, duration=0)
        )

        data2 = self.req.getVideoWatchProgress(
            self.course_id, self.user_id, self.classroom_id, self.node_id
        )
        video_data = data2.get("data", {}).get(f"{self.node_id}", {})
        self.video_length = self._safe_float(video_data.get("video_length"))
        self.finish = video_data.get("completed")
        self.watch_length = self._safe_float(video_data.get("watch_length"))
        self.last_point = self._safe_float(video_data.get("last_point"))
        total_seconds = self.video_length
        self.resume_from = self._select_resume_point(video_data, total_seconds)
        sq = 2

        if self.resume_from > 0:
            heartBeatBaseList.append(
                self._set_heartbeat_state(
                    "seeking", self.resume_from, sq, sp=1, duration=self.video_length
                )
            )
            sq += 1

        heartBeatBaseList.append(
            self._set_heartbeat_state(
                "loadeddata", self.resume_from, sq, sp=1, duration=self.video_length
            )
        )
        sq += 1

        heartBeatBaseList.append(
            self._set_heartbeat_state(
                "ratechange",
                self.resume_from,
                sq,
                sp=PLAYBACK_SPEED,
                duration=self.video_length,
            )
        )
        sq += 1

        if self.resume_from > 0:
            startup_events = ("play", "playing")
        else:
            startup_events = ("waiting", "playing")
        for event_type in startup_events:
            heartBeatBaseList.append(
                self._set_heartbeat_state(
                    event_type,
                    self.resume_from,
                    sq,
                    sp=PLAYBACK_SPEED,
                    duration=self.video_length,
                )
            )
            sq += 1

        self.next_heartbeat_sq = sq
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

            total_seconds = self._safe_float(self.video_length)
            sq = self.next_heartbeat_sq
            resume_from = self._clamp_progress(self.resume_from, total_seconds)
            last_cp = resume_from
            heart_beat_batch = []

            if total_seconds <= 0:
                latest_progress = self.req.getVideoWatchProgress(
                    self.course_id, self.user_id, self.classroom_id, self.node_id
                )
                video_data = latest_progress.get("data", {}).get(f"{self.node_id}", {})
                self.video_length = self._safe_float(video_data.get("video_length"))
                self.watch_length = self._safe_float(video_data.get("watch_length"))
                self.last_point = self._safe_float(video_data.get("last_point"))
                total_seconds = self.video_length
                self.resume_from = self._select_resume_point(video_data, total_seconds)
                resume_from = self.resume_from
                last_cp = resume_from
                if total_seconds > 0:
                    self.heartBeatBase["d"] = total_seconds

            if total_seconds <= 0:
                logger.warning(
                    f"{self.node_name}学习点时长为0，使用最小心跳上报（不显示进度条）"
                )
                end_packet = self._set_heartbeat_state(
                    "videoend", 0, sq, sp=PLAYBACK_SPEED, duration=0
                )
                self.req.videoHeartbeat([end_packet], self.classroom_id)
                self.req.getVideoWatchProgress(
                    self.course_id, self.user_id, self.classroom_id, self.node_id
                )
                logger.info(f"{self.node_name}学习点已完成")
                return

            if resume_from > 0:
                logger.info(
                    f"{self.node_name}上次看到{resume_from:.1f}秒，从断点继续"
                )
            self._render_progress(resume_from, total_seconds)

            if resume_from >= total_seconds:
                logger.info(f"{self.node_name}已到视频末尾，补发结束心跳")
                self._send_video_end(total_seconds, sq)
                self._render_progress(total_seconds, total_seconds)
                print()
                logger.info(f"{self.node_name}学习点已完成")
                return

            current_second = round(resume_from + HEARTBEAT_PROGRESS_SECONDS, 1)
            while current_second < total_seconds:
                time.sleep(HEARTBEAT_INTERVAL_SECONDS)

                packet = self._set_heartbeat_state(
                    "heartbeat",
                    current_second,
                    sq,
                    sp=PLAYBACK_SPEED,
                    duration=self.video_length,
                )
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

                current_second = round(current_second + HEARTBEAT_PROGRESS_SECONDS, 1)

            if last_cp < total_seconds:
                wait_seconds = total_seconds - last_cp
                if wait_seconds > 0:
                    time.sleep(wait_seconds / PLAYBACK_SPEED)

                end_packet = self._set_heartbeat_state(
                    "videoend",
                    total_seconds,
                    sq,
                    sp=PLAYBACK_SPEED,
                    duration=self.video_length,
                )
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
