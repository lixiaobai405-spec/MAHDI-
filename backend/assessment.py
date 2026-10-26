from __future__ import annotations

import json
import math
from functools import lru_cache
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
TYPES = ("M", "A", "H", "D", "I")
DIMS = ("E", "K", "I", "L", "P")
LEVELS = ("AI通用底座", "AI基础应用", "AI专业深化", "AI体系创新")
STYLES = {"social": "社交型", "practice": "实践型", "structure": "结构型", "research": "钻研型"}
FEATURES = {
    "M": ["关注组织整体方向与战略落地", "倾向统筹团队和跨部门资源", "重视在变化中形成决策与共识", "适合推动人机协同和组织转型", "发展重点是AI项目治理与领导力"],
    "A": ["喜欢探索AI工具与应用方法", "倾向把技术能力连接到业务场景", "重视流程优化和知识分享", "适合推动内部AI应用与赋能", "发展重点是工具搭建与场景验证"],
    "H": ["关注日常工作的实际推进", "重视人与人之间的连接与协作", "倾向把AI用于效率提升", "适合在人机协同中发挥执行优势", "发展重点是岗位流程与AI实践"],
    "D": ["关注信息和数据的质量", "倾向以清晰结构组织资料", "重视数据可靠性和使用规范", "适合维护与治理企业数据资产", "发展重点是数据全生命周期管理"],
    "I": ["喜欢深入分析专业问题", "倾向独立钻研复杂情境", "重视专业判断和跨领域理解", "适合处理例外问题与专业攻坚", "发展重点是专业知识与AI的结合"],
}
MIXED_FEATURES = ["多个类型的得分接近，暂未形成单一倾向", "可以结合不同角色的任务继续观察", "建议用实际项目表现补充自我判断", "类型组合可能随经验和目标变化", "本次结果用于发展参考，不代表能力高低"]


def rounded(value: float) -> int:
    return math.floor(value + .5)


@lru_cache(maxsize=1)
def load_bank() -> dict[str, Any]:
    return json.loads((ROOT / "assessment_bank.json").read_text(encoding="utf-8"))


def get_config() -> dict[str, Any]:
    config = json.loads((ROOT / "assessment_config.json").read_text(encoding="utf-8"))
    validate_config(config)
    return config


def validate_config(config: dict[str, Any]) -> None:
    count = config["lite_question_count"]
    if isinstance(count, bool) or not isinstance(count, int) or not 10 <= count <= 20:
        raise ValueError("精简版题量须为10至20的整数")
    if config["algorithm_version"] not in ("legacy_v1", "standard_v2", "standard_v3"):
        raise ValueError("未知评分算法版本")
    if not 0 <= config["mixed_gap"] <= config["moderate_gap"] <= config["strong_gap"]:
        raise ValueError("倾向阈值配置无效")
    if not 0 <= config["score_min"] < config["score_max"] <= 100:
        raise ValueError("评分范围配置无效")
    weights = config["dimension_weights"]
    if set(weights) != set(DIMS) or any(value <= 0 for value in weights.values()) or not math.isclose(sum(weights.values()), 1):
        raise ValueError("五维权重须为正数且合计为1")


def discrimination(question: dict[str, Any]) -> float:
    variances = []
    for option in question["sc"]:
        values = [option.get(kind, 0) for kind in TYPES]
        mean = sum(values) / len(values)
        variances.append(sum((value - mean) ** 2 for value in values) / len(values))
    return sum(variances) / len(variances)


def select_question_ids(config: dict[str, Any]) -> list[str]:
    validate_config(config)
    questions = load_bank()["questions"]
    desired = {"E": 3, "K": 2, "I": 3, "L": 1, "P": 3}
    counts = dict.fromkeys(DIMS, 1)
    count = config["lite_question_count"]
    while sum(counts.values()) < count:
        dim = max(DIMS, key=lambda key: desired[key] * count / 12 - counts[key])
        counts[dim] += 1
    selected = set()
    for dim in DIMS:
        candidates = [q for q in questions if q["dim"] == dim]
        candidates.sort(key=lambda q: -discrimination(q))
        selected.update(q["key"] for q in candidates[:counts[dim]])
    return [q["key"] for q in questions if q["key"] in selected]


def classify_scores(scores: dict[str, int], config: dict[str, Any]) -> dict[str, Any]:
    ranked = sorted(scores.items(), key=lambda item: -item[1])
    first, second = ranked[0][0], ranked[1][0]
    gap = ranked[0][1] - ranked[1][1]
    strength = "明显倾向" if gap >= config["strong_gap"] else "中等倾向" if gap >= config["moderate_gap"] else "倾向不明显"
    mixed = gap < config["mixed_gap"]
    name = load_bank()["types"][first]["name"]
    return {
        "sorted": [[kind, value] for kind, value in ranked],
        "leadingType": first,
        "mainType": None if mixed else first,
        "secondType": None if mixed else second,
        "mainTypeName": "复合型 / 待观察" if mixed else name,
        "secondTypeName": "" if mixed else load_bank()["types"][second]["name"],
        "isDouble": mixed,
        "is_mixed": mixed,
        "tendency_strength": strength,
        "top_gap": gap,
        "conclusion": "复合型 / 待观察" if mixed else f"你最适合的类型：{name}",
        "conclusion_reason": f"前两类得分仅相差{gap}分，低于{config['mixed_gap']}分的明确类型阈值，建议结合后续经历继续观察。" if mixed else f"当前前两类得分相差{gap}分，表现为{strength}。结果反映当前特质，不代表能力高低。",
    }


def _supporting_results(answers: dict[str, int], questions: list[dict[str, Any]]) -> dict[str, Any]:
    by_id = {question["key"]: question for question in questions}
    k_questions = [q for q in questions if q["dim"] == "K"]
    rate = sum(answers[q["key"]] == q.get("correct") for q in k_questions) / len(k_questions) if k_questions else 0
    experience = answers.get("E8", 0)
    level = 4 if rate > .7 and experience >= 3 else 3 if rate > .5 and experience >= 2 else 2 if rate > .25 and experience >= 1 else 1
    learning = [q for q in questions if q["dim"] == "L"]
    style_pct = {key: rounded(100 * sum(answers[q["key"]] == index for q in learning) / len(learning)) if learning else 0 for index, key in enumerate(STYLES)}
    top_style = max(style_pct, key=style_pct.get)
    warnings = []
    def wrong(key: str) -> bool:
        return key in by_id and answers[key] != by_id[key].get("correct")
    def warn(code: str, name: str, desc: str) -> None:
        warnings.append({"code": code, "name": name, "desc": desc})
    if wrong("K3"):
        warn("W01", "AI安全风险意识不足", "Prompt注入风险判断题未答对，建议补充AI安全基础认知，了解常见的输入操控风险")
    if sum(wrong(key) for key in ("K1", "K7", "K8")) >= 2:
        warn("W02", "AI基础认知有待补强", "模型机制类基础题正确率较低，建议从AI通用底座模块开始系统学习")
    if wrong("K10"):
        warn("W05", "AI输出核验习惯待建立", "对AI生成内容的真实性核验意识不足，建议建立先核实、再采用的工作习惯")
    if answers.get("E4", 0) >= 2 and (wrong("K3") or wrong("K10")):
        warn("W06", "数据相关工作的风险组合", "数据工作占比较高，同时在安全或核验意识上存在短板，建议优先补强此方向")
    if sum(answers[q["key"]] == 0 for q in questions if q["dim"] == "P") >= 4:
        warn("W07", "发展潜能题答题偏谨慎", "在多道情境题中倾向选择较为保守的选项，如果你希望承担更多挑战，可主动寻求相关历练机会")
    return {"level": level, "levelName": LEVELS[level - 1], "kRate": rounded(rate * 100), "stylePct": style_pct, "topStyle": top_style, "topStyleName": STYLES[top_style], "warns": warnings}


def score_answers(answers: dict[str, int], version: str, config: dict[str, Any] | None = None) -> dict[str, Any]:
    config = get_config() if config is None else config
    validate_config(config)
    bank = load_bank()
    if version not in ("lite", "full"):
        raise ValueError("请选择精简版或完整版")
    ids = select_question_ids(config) if version == "lite" else [q["key"] for q in bank["questions"]]
    questions = [q for q in bank["questions"] if q["key"] in ids]
    if set(answers) != set(ids):
        raise ValueError("答案须完整对应本次测评题目")
    for question in questions:
        answer = answers[question["key"]]
        if isinstance(answer, bool) or not isinstance(answer, int) or not 0 <= answer < len(question["opts"]):
            raise ValueError(f"题目{question['key']}的答案无效")
    dim_norm = {dim: {} for dim in DIMS}
    raw = {dim: {kind: 0 for kind in TYPES} for dim in DIMS}
    final, z_scores, legacy_scores = {}, {}, {}
    for kind in TYPES:
        observed = mean = variance = legacy = 0.
        for dim in DIMS:
            group = [q for q in questions if q["dim"] == dim]
            maximum = sum(max(option.get(kind, 0) for option in q["sc"]) for q in group)
            raw[dim][kind] = sum(q["sc"][answers[q["key"]]].get(kind, 0) for q in group)
            normalized = rounded(raw[dim][kind] / maximum * 100) if maximum else 0
            dim_norm[dim][kind] = normalized
            legacy += normalized * config["dimension_weights"][dim]
            if not maximum:
                continue
            for question in group:
                values = [option.get(kind, 0) * config["dimension_weights"][dim] / maximum for option in question["sc"]]
                expected = sum(values) / len(values)
                observed += values[answers[question["key"]]]
                mean += expected
                variance += sum((value - expected) ** 2 for value in values) / len(values)
        z = (observed - mean) / math.sqrt(variance) if variance else 0
        z_scores[kind] = z
        legacy_scores[kind] = rounded(legacy)
    # Relative type direction must survive a common uplift across all types.
    # Keep v2 unchanged so saved configuration snapshots remain replayable.
    center = sum(z_scores.values()) / len(TYPES) if config["algorithm_version"] == "standard_v3" else 0
    for kind in TYPES:
        z = z_scores[kind] - center
        z_scores[kind] = round(z, 6)
        percentile = .5 * (1 + math.erf(z / math.sqrt(2)))
        final[kind] = legacy_scores[kind] if config["algorithm_version"] == "legacy_v1" else rounded(config["score_min"] + (config["score_max"] - config["score_min"]) * percentile)
    result = classify_scores(final, config)
    if config["algorithm_version"] == "legacy_v1":
        first, second = result["sorted"][0][0], result["sorted"][1][0]
        result.update(mainType=first, secondType=second, mainTypeName=bank["types"][first]["name"], secondTypeName=bank["types"][second]["name"], isDouble=result["top_gap"] <= 10, is_mixed=False, conclusion=f"你最适合的类型：{bank['types'][first]['name']}")
        result["conclusion_reason"] = f"旧版算法前两类相差{result['top_gap']}分，按不超过10分的规则显示双类型倾向。" if result["isDouble"] else f"旧版算法前两类相差{result['top_gap']}分，显示主类型与辅助倾向。"
    supporting = _supporting_results(answers, questions)
    if result["leadingType"] == "M" and "E2" in answers and answers["E2"] < 2:
        supporting["warns"].append({"code": "W03", "name": "管理经验积累较少", "desc": "当前M型倾向较高，但团队管理经验尚浅，建议先积累跨职能项目协调经验"})
    if result["leadingType"] == "I" and "E6" in answers and answers["E6"] < 1:
        supporting["warns"].append({"code": "W04", "name": "专业积累有待加深", "desc": "当前I型倾向较高，但专业领域从业年限较短，建议先持续积累专业深度"})
    features = MIXED_FEATURES if result["is_mixed"] else FEATURES[result["leadingType"]]
    total = sum(final.values())
    result.update(supporting)
    result.update(
        agent_type="mahid", version=version, algorithm_version=config["algorithm_version"],
        question_bank_version=bank["bank_version"], result_schema_version=config["result_schema_version"],
        answers=dict(answers), question_ids=ids, final=final,
        pcts={kind: rounded(value / total * 100) if total else 0 for kind, value in final.items()} if config["algorithm_version"] == "legacy_v1" else dict(final),
        dimNorm=dim_norm, raw_scores=raw, z_scores=z_scores,
        score_kind="legacy_share" if config["algorithm_version"] == "legacy_v1" else "standardized_score",
        reference_distribution="theoretical_options_centered_v1" if config["algorithm_version"] == "standard_v3" else "theoretical_options_v1",
        core_features=list(features), lite_features=list(features[:3]),
        development_advice="建议继续完成深度测评，并选择一个真实项目观察自己在不同任务中的表现。" if result["is_mixed"] else bank["types"][result["leadingType"]]["paths"][0]["c"],
    )
    return result
