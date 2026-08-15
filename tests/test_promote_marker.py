#!/usr/bin/env python3
"""reusable-promote-image.yml 里源提交记号的读写回归测试。

这条流水线的两处解析必须对「什么算一条记号」看法一致，且必须认得**接入链接之前**
写下的那些行：不认的话它们不会被替换，而是被再插一行，于是同一份文件里出现两条记号，
下一轮判成歧义、四个消费方的镜像提升全部停摆——而现场只有一句报错，改起来要人工。

两段逻辑都从 workflow 里现取现跑，不在这里抄一份：抄一份就有两个真源，改了那边不改
这边时测试照样绿，恰好挡不住它本要挡的那类漂移。

跑法：python3 tests/test_promote_marker.py
"""

import pathlib
import re
import subprocess
import sys
import tempfile
import textwrap

WORKFLOW = pathlib.Path(__file__).resolve().parents[1] / ".github/workflows/reusable-promote-image.yml"
PRODUCER = "pipelines"
PRODUCER_URL = "https://github.com/UNILUME-AI/pipelines"
KEY = "normalizer_image"
HEAD = f"# 源提交（本行由 {PRODUCER} 的发布流水线自动维护，取记号以它为准）："
OLD_SHA = "0566ccef79e74ae4f5932bd2b48945dc0f7cde79"
NEW_SHA = "1234567890abcdef1234567890abcdef12345678"
IMAGE = "539796311778.dkr.ecr.ap-southeast-1.amazonaws.com/silver-normalizer@sha256:" + "e" * 64


def extract(start: str, end: str) -> str:
    """取 workflow 里 start 与 end 两行之间的原文，并去掉 YAML 块标量的基准缩进。

    dedent 去的是这一段的公共前缀，正好等于 `run: |` 的基准缩进，故不必把缩进宽度写死。
    """
    lines = WORKFLOW.read_text().splitlines()
    begin = next(i for i, ln in enumerate(lines) if start in ln)
    stop = next(i for i in range(begin + 1, len(lines)) if lines[i].strip() == end)
    return textwrap.dedent("\n".join(lines[begin + 1:stop])) + "\n"


def tfvars(*extra_lines: str) -> str:
    """一份最小的 tfvars，可选地在镜像行上方带上若干行。"""
    body = "\n".join([*extra_lines, f'{KEY} = "old-image@sha256:{"a" * 64}"'])
    return f'workos_org_id = "org_dev_placeholder"\n\n# 归一化镜像。\n{body}\n\n# 尾部注释\n'


def write_marker(content: str, sha: str = NEW_SHA):
    """跑 workflow 里那段 python，返回 (退出码, 新文件内容, stdout, stderr)。"""
    with tempfile.TemporaryDirectory() as d:
        script = pathlib.Path(d) / "rewrite.py"
        script.write_text(extract("<<'PYEOF'", "PYEOF"))
        target = pathlib.Path(d) / "dev.tfvars"
        target.write_text(content)
        r = subprocess.run(
            [sys.executable, script, str(target), IMAGE, sha, KEY, PRODUCER, PRODUCER_URL],
            capture_output=True, text=True,
        )
        return r.returncode, target.read_text(), r.stdout.strip(), r.stderr.strip()


def read_marker(content: str):
    """跑 workflow 里的 marker_in，返回 (退出码, 取到的记号)。"""
    func = extract("marker_in() { # $1=文件内容", "}")
    script = f'producer={PRODUCER}\nmarker_in() {{ # $1\n{func}}}\nmarker_in "$1"\n'
    r = subprocess.run(["bash", "-c", script, "_", content], capture_output=True, text=True)
    return r.returncode, r.stdout.strip()


def marker_lines(content: str) -> list[str]:
    return [ln for ln in content.splitlines() if ln.startswith(HEAD)]


failures = []


def check(name: str, cond: bool, detail: str = ""):
    if cond:
        print(f"  ok   {name}")
    else:
        print(f"  FAIL {name} {detail}")
        failures.append(name)


print("写入：")

# 接入链接之前写下的那种行——必须被**替换**，不能被再插一行。这是本文件存在的首要理由。
legacy = tfvars(f"{HEAD}{PRODUCER}@{OLD_SHA}")
rc, out, state, err = write_marker(legacy)
lines = marker_lines(out)
check("旧格式（无链接）的记号被替换而不是重复", rc == 0 and len(lines) == 1, f"rc={rc} 共 {len(lines)} 条 {err}")
check("替换后带上链接", lines[:1] == [f"{HEAD}{PRODUCER}@{NEW_SHA} {PRODUCER_URL}/commit/{NEW_SHA}"], lines[:1])
check("旧格式替换后报告为 changed", state == "changed", state)

# 读取侧只取第一个空格之前的提交号、其后一概不校验，写入侧就必须认得同样宽的后缀。
# 两侧不对齐时，人在链接后面补一句说明这种再普通不过的举动，就会让写入侧认不出那一行、
# 转而再插一条，下一轮直接判成歧义停摆——而读取侧一路都读得好好的，症状与原因隔了一轮。
annotated = tfvars(f"{HEAD}{PRODUCER}@{OLD_SHA} {PRODUCER_URL}/commit/{OLD_SHA} 已人工核对")
rc, out, state, err = write_marker(annotated)
check("记号后带多词说明时仍被替换而不是重复", rc == 0 and len(marker_lines(out)) == 1, f"rc={rc} 共 {len(marker_lines(out))} 条 {err}")

# 已是新格式时同样只更新那一行。
current = tfvars(f"{HEAD}{PRODUCER}@{OLD_SHA} {PRODUCER_URL}/commit/{OLD_SHA}")
rc, out, state, err = write_marker(current)
check("新格式的记号被就地更新", rc == 0 and len(marker_lines(out)) == 1, f"rc={rc} {err}")
check("更新后指向新的提交", NEW_SHA in marker_lines(out)[0] and OLD_SHA not in out, marker_lines(out))

# 首次写入：文件里还没有记号，插在镜像行上方。
rc, out, state, err = write_marker(tfvars())
check("没有记号时插入一条", rc == 0 and len(marker_lines(out)) == 1, f"rc={rc} {err}")
idx = out.splitlines().index(marker_lines(out)[0])
check("插在镜像那一行的上方", out.splitlines()[idx + 1].startswith(KEY), out.splitlines()[idx + 1])

# 已有两条同生产方的记号 ⇒ 无从判断该改哪条，必须大声失败而不是改错一条。
dupe = tfvars(f"{HEAD}{PRODUCER}@{OLD_SHA}", f"{HEAD}{PRODUCER}@{NEW_SHA} {PRODUCER_URL}/commit/{NEW_SHA}")
rc, out, state, err = write_marker(dupe)
check("两条记号时非零退出", rc != 0, f"rc={rc}")

# 路径或键漂移过一次（pipelines 仓 2026-08-12），当时构建全绿而摘要没提上去。
rc, out, state, err = write_marker('other_key = "x"\n')
check("找不到键时非零退出", rc != 0, f"rc={rc}")

print("读取：")

rc, got = read_marker(tfvars(f"{HEAD}{PRODUCER}@{OLD_SHA} {PRODUCER_URL}/commit/{OLD_SHA}"))
check("从带链接的行取出提交号", (rc, got) == (0, OLD_SHA), f"rc={rc} got={got!r}")

rc, got = read_marker(tfvars(f"{HEAD}{PRODUCER}@{OLD_SHA}"))
check("从不带链接的旧行取出提交号", (rc, got) == (0, OLD_SHA), f"rc={rc} got={got!r}")

rc, got = read_marker(tfvars())
check("没有记号时安静返回空", (rc, got) == (0, ""), f"rc={rc} got={got!r}")

# 镜像引用本身就长成 `<生产方>@sha256:…`（db-migrate 推的镜像仓正是这个名字），
# 手写注释也可能顺手引用某个提交——两者都不得被误数成记号。
noise = tfvars(
    f"# 见 {HEAD}{PRODUCER}@{OLD_SHA} 那一行",
    f'db_image = "registry/{PRODUCER}@sha256:{"b" * 64}"',
    f"{HEAD}{PRODUCER}@{OLD_SHA} {PRODUCER_URL}/commit/{OLD_SHA}",
)
rc, got = read_marker(noise)
check("行中引用与同名镜像不被误数", (rc, got) == (0, OLD_SHA), f"rc={rc} got={got!r}")

rc, got = read_marker(tfvars(f"{HEAD}{PRODUCER}@{OLD_SHA}", f"{HEAD}{PRODUCER}@{NEW_SHA}"))
check("两条记号时非零退出", rc != 0, f"rc={rc}")

# 有人手改成非提交号 ⇒ 无从判断先后，停下而不是猜。
rc, got = read_marker(tfvars(f"{HEAD}{PRODUCER}@手工改过"))
check("记号取值异常时非零退出", rc != 0, f"rc={rc}")

# 两段解析对同一行的看法必须一致：写出来的行，读回来必须取到同一个提交号。
_, out, _, _ = write_marker(tfvars(), sha=NEW_SHA)
rc, got = read_marker(out)
check("写出的行读得回同一个提交号", (rc, got) == (0, NEW_SHA), f"rc={rc} got={got!r}")

if failures:
    print(f"\n{len(failures)} 项未通过：{', '.join(failures)}")
    sys.exit(1)
print("\n全部通过")
