import learnPoints.videoLearnPoint as video_module
from learnPoints.videoLearnPoint import VideoLearnPoint


class FakeVideoReq:
    def __init__(self, progress_payload=None):
        self.progress_payload = progress_payload or {}
        self.heartbeats = []
        self.progress_calls = 0
        self.train_calls = 0

    def videoHeartbeat(self, payload, classroom_id=None):
        self.heartbeats.append((payload, classroom_id))
        return {"success": True}

    def getVideoWatchProgress(self, *args, **kwargs):
        self.progress_calls += 1
        return self.progress_payload

    def train_classes(self, classroom_id):
        self.train_calls += 1
        return {"success": True}


def make_video_point(req, video_length=100.0, resume_from=0.0):
    point = VideoLearnPoint({"id": "v1", "name": "demo"})
    point.req = req
    point.course_id = 1
    point.user_id = 2
    point.classroom_id = 3
    point.node_id = "v1"
    point.finish = 0
    point.video_length = video_length
    point.resume_from = resume_from
    point.next_heartbeat_sq = 7
    point.heartBeatBase.update(
        {
            "u": point.user_id,
            "c": point.course_id,
            "v": point.node_id,
            "classroomid": str(point.classroom_id),
            "d": video_length,
        }
    )
    return point


def flatten_heartbeat_payloads(req):
    packets = []
    for payload, _ in req.heartbeats:
        packets.extend(payload)
    return packets


def test_init_process_resumes_from_last_point_and_sends_ratechange():
    req = FakeVideoReq(
        {
            "data": {
                "v1": {
                    "completed": 0,
                    "watch_length": 49,
                    "last_point": 44.1,
                    "video_length": 528.0,
                }
            }
        }
    )
    point = make_video_point(req)

    point.initProcess()

    packets = req.heartbeats[0][0]
    assert [(p["et"], p["cp"], p["sp"]) for p in packets] == [
        ("loadstart", 0.0, 1),
        ("seeking", 44.1, 1),
        ("loadeddata", 44.1, 1),
        ("ratechange", 44.1, 2),
        ("play", 44.1, 2),
        ("playing", 44.1, 2),
    ]
    assert point.resume_from == 44.1
    assert point.next_heartbeat_sq == 7


def test_run_finish_uses_five_second_heartbeat_at_2x(monkeypatch):
    sleeps = []
    monkeypatch.setattr(video_module.time, "sleep", sleeps.append)
    req = FakeVideoReq({"data": {"v1": {"video_length": 30.0}}})
    point = make_video_point(req, video_length=30.0, resume_from=10.0)

    point.runFinish()

    packets = flatten_heartbeat_payloads(req)
    assert sleeps == [5.0, 5.0]
    assert [(p["et"], p["cp"], p["sp"]) for p in packets] == [
        ("heartbeat", 20.0, 2),
        ("videoend", 30.0, 2),
    ]


def test_run_finish_sends_videoend_when_resume_is_at_video_end(monkeypatch):
    sleeps = []
    monkeypatch.setattr(video_module.time, "sleep", sleeps.append)
    req = FakeVideoReq({"data": {"v1": {"video_length": 100.0}}})
    point = make_video_point(req, video_length=100.0, resume_from=100.0)

    point.runFinish()

    packets = flatten_heartbeat_payloads(req)
    assert sleeps == []
    assert [(p["et"], p["cp"], p["sp"]) for p in packets] == [
        ("videoend", 100.0, 2),
    ]
    assert req.progress_calls == 1
    assert req.train_calls == 1
