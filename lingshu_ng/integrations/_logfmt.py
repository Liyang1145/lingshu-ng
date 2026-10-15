# -*- coding: utf-8 -*-
"""E6-2：日志格式配置（纯标准库）。

* ``LINGSHU_NG_LOG``：级别（缺省 WARNING）。
* ``LINGSHU_NG_LOG_FORMAT``：``text``（缺省，``时间 级别 logger: 消息``）或 ``json``（每行一个 JSON 对象：
  ``ts``/``level``/``logger``/``msg``，异常时加 ``exc``），便于 ELK / Loki / CloudWatch 采集。
审计日志（logger ``lingshu_ng.audit``）的 ``msg`` 本身是 JSON 字符串，json 格式下原样嵌入 ``msg``。
"""
import json
import logging
import os
import time

LOG_ENV = "LINGSHU_NG_LOG"
FORMAT_ENV = "LINGSHU_NG_LOG_FORMAT"
TEXT_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"


class JsonFormatter(logging.Formatter):
    """每条日志一行 JSON（UTC 毫秒时间戳）。"""

    def format(self, record: logging.LogRecord) -> str:
        rec = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(record.created)) + ".%03dZ" % (record.msecs,),
               "level": record.levelname, "logger": record.name, "msg": record.getMessage()}
        if record.exc_info:
            rec["exc"] = self.formatException(record.exc_info)
        elif record.exc_text:
            rec["exc"] = record.exc_text
        return json.dumps(rec, ensure_ascii=False, default=str)


def configure_logging(stream, force: bool = False) -> None:
    """按环境变量配置根 logger；格式值非法时抛 ``ValueError``（启动即失败，不静默退回）。"""
    fmt = (os.environ.get(FORMAT_ENV) or "text").strip().lower()
    if fmt not in ("text", "json"):
        raise ValueError(f"{FORMAT_ENV} 只能是 text 或 json，收到 {fmt!r}")
    h = logging.StreamHandler(stream)
    h.setFormatter(JsonFormatter() if fmt == "json" else logging.Formatter(TEXT_FORMAT))
    logging.basicConfig(level=os.environ.get(LOG_ENV, "WARNING"), handlers=[h], force=force)
