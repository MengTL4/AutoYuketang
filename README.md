# AutoYuketang 使用教程

本文档基于当前仓库代码编写，目标是让你从 0 到可运行。

## 1. 功能说明

- 自动处理视频学习点（发送心跳、推进视频进度）
- 自动处理讨论学习点（调用大模型生成评论并提交）

说明：讨论学习点依赖 `config.py` 里的 `api_key`（DeepSeek）。

## 2. 环境要求

- Python 3.11 及以上
- 可访问雨课堂网络环境
- 有效的雨课堂登录 Cookie

## 3. 安装依赖

你可以用 `uv` 或 `pip`。

### 方式 A：uv

```bash
uv sync
```

### 方式 B：pip

```bash
python -m pip install -U requests openai pytest
```

## 4. 配置 `config.py`

编辑根目录 `config.py`：

```python
Cookie = "你的完整Cookie字符串"
api_key = "你的DeepSeek API Key"
```

### 4.1 Cookie 如何准备

建议从浏览器开发者工具复制当前登录态 Cookie（雨课堂域名下）。

至少要保证 Cookie 里有：

- `sessionid`
- `csrftoken`

当前代码会自动从 Cookie 中提取 `csrftoken`，并设置 `X-CSRFToken` 请求头。

### 4.2 api_key 是否必须

- 如果课程里存在未完成的讨论学习点，`api_key` 必须填写。
- 如果你只想跑视频学习点，可在 `yktMain.py` 里临时注释讨论学习点循环。

## 5. 选择课程

入口在 `yktMain.py`：

```python
if __name__ == "__main__":
    ykt = YKTMain()
    ykt.initCourseInfo(1)
```

`initCourseInfo(indexNum)` 使用课程列表下标（从 0 开始）。

例如：

- `0` = 第 1 门课
- `1` = 第 2 门课

你可以先用下面脚本打印课程索引：

```python
from core.commonFunReq import CommonFunReq

req = CommonFunReq()
courses = req.getCourseList().get("data", {}).get("list", [])
for i, item in enumerate(courses):
    name = item.get("name") or item.get("course", {}).get("name")
    classroom_id = item.get("classroom_id")
    print(i, name, classroom_id)
```

## 6. 运行项目

在项目根目录执行：

```bash
python yktMain.py
```

如果你使用虚拟环境：

```bash
.venv\Scripts\python.exe yktMain.py
```

## 7. 运行日志说明

你会看到类似日志：

- `学习点已完成，跳过`：该节点已完成，不再重复提交
- `开始刷xxx学习点`：开始处理当前学习点
- `学习点进度 a/b s`：视频学习点按批次上报进度
- `学习点已完成`：当前节点处理结束

### 关于进度条

- 交互终端（TTY）会显示实时进度条。
- 非交互环境（如日志采集、重定向）默认不绘制覆盖式进度条，改看 `学习点进度 a/b s` 日志即可。

### 关于 `时长为0`

如果出现：

- `学习点时长为0，使用最小心跳上报（不显示进度条）`

说明服务端返回该视频时长为 0。代码会走最小上报流程，避免卡死。

## 8. 常见问题

### 8.1 运行后没有课程或报登录相关错误

通常是 Cookie 失效。重新从浏览器复制最新 Cookie 到 `config.py`。

### 8.2 视频看起来跑了，但后台进度不变

按顺序检查：

1. Cookie 是否最新（`sessionid`、`csrftoken`）
2. 是否被风控/限流（请求返回异常）
3. 网络是否稳定
4. 课程索引是否选错

### 8.3 讨论学习点报错

常见原因：

- `api_key` 未填或无效
- 模型接口不可达

可以先注释讨论学习点循环，仅验证视频流程。

## 9. 安全建议

- 不要把 `config.py` 提交到公共仓库
- 不要在日志中公开你的 Cookie 或 API Key
- 建议使用仅个人可访问的私有环境运行

## 10. 快速自检清单

- [ ] 已安装 Python 3.11+
- [ ] 已安装依赖
- [ ] `config.py` 已填写有效 Cookie
- [ ] 如需讨论功能，已填写 `api_key`
- [ ] `yktMain.py` 课程索引设置正确
- [ ] 运行后能看到正常日志输出
