import pathlib, re
from lingshu_ng.integrations._configshow import check

ROOT = pathlib.Path(__file__).resolve().parent.parent
# 有校验：给非法值时 config --check 必须报错
VALIDATED = {
    "LINGSHU_NG_MAX_CONN": "x", "LINGSHU_NG_LOG_FORMAT": "xml",
    "LINGSHU_NG_STRICT_UNSUPPORTED": "maybe", "LINGSHU_NG_MAX_BODY": "abc",
    "LINGSHU_NG_BUSY_TIMEOUT": "abc", "LINGSHU_NG_RERANK_TOPN": "abc", "LINGSHU_NG_SLOW_MS": "abc",
}
# 显式豁免：路径/开关/密钥/URL/模型名，无统一取值约束或由专门检查覆盖
EXEMPT = {
    "LINGSHU_NG_DB", "LINGSHU_NG_TOKEN_FILE", "LINGSHU_NG_TOKEN", "LINGSHU_NG_LLM_KEY",
    "LINGSHU_NG_ALLOW_NEWER_SCHEMA", "LINGSHU_NG_ASSOC", "LINGSHU_NG_CHAIN", "LINGSHU_NG_CHAIN_LLM",
    "LINGSHU_NG_CHAIN_LLM_COSTLOG", "LINGSHU_NG_CHAIN_LLM_URL", "LINGSHU_NG_CHAIN_V",
    "LINGSHU_NG_DENSE_MODEL", "LINGSHU_NG_EMBED_CACHE", "LINGSHU_NG_EMBED_MODEL", "LINGSHU_NG_LEXICAL",
    "LINGSHU_NG_LOG", "LINGSHU_NG_NEURAL", "LINGSHU_NG_RERANK_MODEL", "LINGSHU_NG_SEM",
    "LINGSHU_NG_SEM_CACHE", "LINGSHU_NG_SEM_CASC_MODEL", "LINGSHU_NG_SEM_MODEL",
    "LINGSHU_NG_SEM_THREADS", "LINGSHU_NG_SOURCE_PLUGINS",
}


def test_every_documented_var_validated_or_exempt():
    text = "".join(p.read_text(encoding="utf-8", errors="ignore")
                   for p in [ROOT / "README.md", *(ROOT / "docs").rglob("*.md")])
    documented = set(re.findall(r"LINGSHU_NG_[A-Z_]+", text))
    missing = documented - set(VALIDATED) - EXEMPT
    assert not missing, f"未分类的文档化环境变量: {sorted(missing)}"


def test_validated_vars_flag_bad_value():
    for k, v in VALIDATED.items():
        r = check({k: v})
        assert any(b["name"] == k for b in r["problems"]), (k, r)
