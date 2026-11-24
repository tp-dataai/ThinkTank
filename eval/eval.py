# -*- coding: utf-8 -*-
"""
基于 ragas 的 RAG 检索增强流程评估程序。

【功能】
1. 从 eval/qa.csv 读取黄金问题集（question 问题、ground_truth 参考答案，兼容中文列头）。
2. 逐条调用 thinktank.query_process.main_graph.QueryMainGraphRunner.create_and_run() 跑真实 RAG 流程，
   从返回 state 的 reranked_docs 中提取上下文，并取 state 的 answer 作为生成答案。
3. 使用项目内的 BGEM3 嵌入工具（thinktank.tool.bgem3_embedding_tool）与
   项目内的大模型工具（thinktank.tool.tool_llm_init）作为 ragas 的评估模型/向量模型。
4. 计算 5 个指标：Faithfulness、Answer Relevancy、Context Precision、Context Recall、Answer Correctness。
5. 将逐条明细写入 eval/qa_result.csv（UTF-8 BOM，Excel 可直接打开）。

【依赖】
    uv pip install ragas            # 已按 ragas 0.4.4 源码核对，同时兼容 0.2 / 0.3 的经典指标命名
    （项目自身依赖见 pyproject.toml；运行前请确认 .env 中的 LLM / Milvus / BGE-M3 配置可用）

【运行】
    python eval/eval.py
    python eval/eval.py --limit 2 --keep-history     # 只跑前 2 条，并保留 MongoDB 聊天历史读写

【注意】
    评估会真实调用 LLM、Milvus、BGE-M3、rerank 等外部服务，请确保相应服务已启动。
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import math
import sys
import warnings
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

# ---------------------------------------------------------------------------
# 路径与环境：保证从任意工作目录运行 eval.py 时都能 import thinktank.*
# ---------------------------------------------------------------------------
EVAL_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = EVAL_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from dotenv import load_dotenv

    load_dotenv(PROJECT_ROOT / ".env", override=True)
except ImportError:
    pass

# ragas 0.4 中从 ragas.metrics 导入经典指标、包装 LLM 都会触发弃用告警；
# 告警的 stacklevel 指向本文件，按 module 过滤不生效，这里按消息内容统一静默，避免刷屏
warnings.filterwarnings("ignore", message=".*deprecated.*", category=DeprecationWarning)

# 输出 CSV 的 9 个列（顺序与需求一致）
RESULT_COLUMNS = [
    "question",
    "context",
    "answer",
    "ground_truth",
    "faithfulness",
    "answer_relevancy",
    "context_precision",
    "context_recall",
    "answer_correctness",
]

# 5 个指标的「输出列名 -> 候选类名」：兼容 ragas 0.2 / 0.3 / 0.4 的命名差异
METRIC_CANDIDATES = {
    "faithfulness": ("Faithfulness",),
    "answer_relevancy": ("AnswerRelevancy", "ResponseRelevancy"),
    "context_precision": ("ContextPrecision", "LLMContextPrecisionWithReference"),
    "context_recall": ("ContextRecall", "LLMContextRecall"),
    "answer_correctness": ("AnswerCorrectness", "FactualCorrectness"),
}

# 结果 DataFrame 中分数列的可能名称（用于兜底取值）
METRIC_ALIASES = {
    "faithfulness": ("faithfulness",),
    "answer_relevancy": ("answer_relevancy", "response_relevancy"),
    "context_precision": ("context_precision", "llm_context_precision_with_reference"),
    "context_recall": ("context_recall", "llm_context_recall"),
    "answer_correctness": ("answer_correctness", "factual_correctness"),
}

# ragas 的 embedding 基类选择。
# 说明：Pylance / pyright 不允许把「多个分支赋值得到的联合类型」当作类定义的基类，
# 会报「类的参数必须是基类」。因此这里用 TYPE_CHECKING 让类型检查器只看到
# ragas 0.4 的现代基类 BaseRagasEmbedding（一个确定的类），运行时再按实际安装版本回退：
# 0.4 -> BaseRagasEmbedding；0.2/0.3 -> BaseRagasEmbeddings；未安装 ragas -> object
# （真正评估前 _require_ragas() 会给出安装提示）。
if TYPE_CHECKING:
    from ragas.embeddings.base import BaseRagasEmbedding as _RagasEmbeddingBase
else:
    try:
        from ragas.embeddings.base import BaseRagasEmbedding as _RagasEmbeddingBase
    except ImportError:
        try:
            from ragas.embeddings.base import BaseRagasEmbeddings as _RagasEmbeddingBase
        except ImportError:
            _RagasEmbeddingBase = object


def _require_ragas() -> None:
    """检查 ragas 是否已安装，未安装时给出明确的安装命令后退出。"""
    try:
        import ragas  # noqa: F401
    except ImportError as exc:
        raise SystemExit(
            "未检测到 ragas，请先在项目虚拟环境执行：uv pip install ragas\n"
            "（本程序按 ragas 0.4.4 源码编写，兼容 0.2 / 0.3 的经典指标类名）"
        ) from exc


def _is_fatal_llm_error(exc: BaseException) -> bool:
    """
    判断异常是否属于「全局性、不可重试」的大模型服务错误。

    额度耗尽（insufficient_quota / 403）和鉴权失败（401 / invalid_api_key）对每条问题、
    每个指标都会复现，继续跑完只会得到一份全空结果，因此应当立即中止。
    """
    class_name = type(exc).__name__.lower()
    if any(key in class_name for key in ("permissiondenied", "authenticationerror")):
        return True
    message = str(exc).lower()
    return any(
        key in message
        for key in (
            "insufficient_quota",
            "free quota exhausted",
            "exceeded your current quota",
            "invalid_api_key",
            "incorrect api key",
            "401",
            "403",
        )
    )


def _fatal_llm_error_hint() -> str:
    """生成大模型额度/鉴权问题的排查提示（不输出密钥）。"""
    import os

    api_base = os.getenv("OPENAI_API_BASE", "") or "未配置"
    model = os.getenv("LLM_DEFAULT_MODEL", "") or "未配置"
    return (
        "检测到大模型接口返回额度耗尽或鉴权失败，评估无法继续。\n"
        f"当前接口：{api_base}，默认模型：{model}。\n"
        "处理方式（任选其一）：\n"
        "  1. 登录阿里云百炼控制台充值，或关闭「仅使用免费额度」模式；\n"
        "  2. 修改 .env 中的 OPENAI_API_KEY，换成仍有额度的 API Key；\n"
        "  3. 修改 .env 中的 LLM_DEFAULT_MODEL / ITEM_MODEL / VL_MODEL，换成仍有额度的模型。\n"
        "为避免产出全空的 qa_result.csv 造成误判，本次评估已中止。"
    )


def _no_op(*args: Any, **kwargs: Any) -> None:
    """替代 MongoDB 写入函数：评估时不落库，返回空值。"""
    return None


def _empty_history(*args: Any, **kwargs: Any) -> list:
    """替代 MongoDB 历史读取函数：评估时返回空历史，保证每道题独立、不受会话历史影响。"""
    return []


def _patch_chat_history_side_effects() -> None:
    """屏蔽 RAG 主流程里的 MongoDB 聊天历史读写副作用，避免评估污染线上会话数据或连接失败。"""
    from thinktank.query_process.nodes import node_answer_output, node_item_name_confirm

    node_item_name_confirm.get_recent_message = _empty_history  # type: ignore[assignment]
    node_item_name_confirm.save_chat_message = _no_op  # type: ignore[assignment]
    node_item_name_confirm.update_history_item_names = _no_op  # type: ignore[assignment]
    node_answer_output.save_chat_message = _no_op  # type: ignore[assignment]


def _load_project_llm() -> Any:
    """
    从 thinktank.tool.tool_llm_init 取得评估用大模型对象。

    说明：当前仓库该模块暴露的是 get_llm_init()（各节点 process 方法中也是用它拿 llm）；
    若后续版本改名为 process()，这里会优先使用 process()，以兼容需求描述中的写法。
    """
    from thinktank.tool import tool_llm_init

    process = getattr(tool_llm_init, "process", None)
    if callable(process):
        try:
            llm = process()
            if llm is not None:
                return llm
        except TypeError:
            # process 需要参数时（例如需要 state），回退到仓库现有的稳定接口
            pass

    getter = getattr(tool_llm_init, "get_llm_init", None)
    if callable(getter):
        return getter()

    raise RuntimeError("tool_llm_init.py 中未找到 process() 或 get_llm_init()，无法取得 LLM")


def _resolve_metric_class(output_name: str) -> Any:
    """按候选名称解析 ragas 指标类，并把指标 name 统一成需求要求的输出列名。"""
    import ragas.metrics as ragas_metrics

    for class_name in METRIC_CANDIDATES[output_name]:
        metric_cls = getattr(ragas_metrics, class_name, None)
        if metric_cls is None:
            continue
        metric = metric_cls()
        try:
            # 不同版本同类指标的 name 可能不同（如 factual_correctness），统一成用户要求的列名
            metric.name = output_name
        except Exception:
            pass
        return metric

    raise RuntimeError(
        f"当前 ragas 版本未提供 {output_name} 对应的指标类，候选：{METRIC_CANDIDATES[output_name]}"
    )


def _normalize_header(name: str) -> str:
    """清洗 CSV 列头：去掉 BOM、首尾空格并转小写，便于兼容 question / 问题 等写法。"""
    return (name or "").replace("\ufeff", "").strip().lower()


def _join_contexts(contexts: list[str]) -> str:
    """把多段检索上下文拼成 CSV 的单个单元格文本，带序号便于在 Excel 中阅读。"""
    return "\n\n".join(f"【上下文 {i}】{text}" for i, text in enumerate(contexts, start=1))


def _format_score(value: Any) -> str:
    """把指标分数格式化成 4 位小数；None / NaN / 非数值统一写成空字符串。"""
    if value is None:
        return ""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return ""
    if math.isnan(number) or math.isinf(number):
        return ""
    return f"{number:.4f}"


def _extract_score_rows(result: Any) -> list[dict[str, Any]]:
    """把 ragas 的 EvaluationResult 转成按行排列的分数字典列表。"""
    df = result.to_pandas()
    return df.to_dict("records")


def _align_score_rows(
    records: list[dict[str, Any]], score_rows: list[dict[str, Any]]
) -> list[dict[str, str]]:
    """按问题文本把 ragas 分数行与原始样本对齐，并取出 5 个指标分数。"""
    question_key = "user_input" if score_rows and "user_input" in score_rows[0] else "question"
    by_question: dict[str, dict[str, Any]] = {}
    if question_key:
        for row in score_rows:
            by_question[str(row.get(question_key, ""))] = row

    aligned: list[dict[str, str]] = []
    for index, record in enumerate(records):
        row = by_question.get(record["question"]) or (
            score_rows[index] if index < len(score_rows) else {}
        )
        scores: dict[str, str] = {}
        for output_name, aliases in METRIC_ALIASES.items():
            value = None
            for alias in aliases:
                if alias in row and row[alias] is not None:
                    value = row[alias]
                    break
            scores[output_name] = _format_score(value)
        aligned.append(scores)
    return aligned


class Bgem3RagasEmbeddings(_RagasEmbeddingBase):
    """把项目内 BGEM3 稠密向量工具包装成 ragas 可直接使用的 embeddings 对象。"""

    @staticmethod
    def _encode(texts: list[str]) -> list[list[float]]:
        """调用项目内 get_bgem3_embeddings 批量生成稠密向量，并转成纯 Python 浮点列表。"""
        if not texts:
            return []
        from thinktank.tool.bgem3_embedding_tool import get_bgem3_embeddings

        dense = get_bgem3_embeddings([str(text) for text in texts])["dense"]
        return [[float(value) for value in vector] for vector in dense]

    def embed_text(self, text: str, **kwargs: Any) -> list[float]:
        """嵌入单条文本（ragas 0.4 现代接口）。"""
        return self.embed_texts([text])[0]

    def embed_texts(self, texts: list[str], **kwargs: Any) -> list[list[float]]:
        """批量嵌入文本（ragas 0.4 现代接口，走 BGEM3 一次编码以降低开销）。"""
        return self._encode(list(texts))

    async def aembed_text(self, text: str, **kwargs: Any) -> list[float]:
        """异步嵌入单条文本：BGEM3 为本地同步模型，放入线程池避免阻塞事件循环。"""
        return await asyncio.to_thread(self.embed_text, text)

    async def aembed_texts(self, texts: list[str], **kwargs: Any) -> list[list[float]]:
        """异步批量嵌入文本：放入线程池执行同步编码。"""
        return await asyncio.to_thread(self.embed_texts, list(texts))

    def embed_query(self, text: str) -> list[float]:
        """嵌入查询文本（LangChain / ragas 旧接口，AnswerRelevancy 使用）。"""
        return self.embed_text(text)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """批量嵌入文档（LangChain / ragas 旧接口，AnswerRelevancy 使用）。"""
        return self.embed_texts(list(texts))

    async def aembed_query(self, text: str) -> list[float]:
        """异步嵌入查询文本（ragas 旧接口）。"""
        return await self.aembed_text(text)

    async def aembed_documents(self, texts: list[str]) -> list[list[float]]:
        """异步批量嵌入文档（ragas 旧接口）。"""
        return await self.aembed_texts(list(texts))

    def set_run_config(self, run_config: Any) -> None:
        """接收并保存 ragas 的运行配置（旧版指标初始化时会调用）。"""
        self.run_config = run_config


def step1_load_qa_pairs(qa_path: Path) -> list[dict[str, str]]:
    """
    步骤一：读取 eval/qa.csv，返回统一的 question / ground_truth 问答列表。

    同时兼容「问题 / 参考答案」中文列头、UTF-8 BOM 以及列名两侧空格。
    """
    if not qa_path.exists():
        raise SystemExit(f"找不到问题集文件：{qa_path}")

    with qa_path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        headers = [name for name in (reader.fieldnames or []) if name is not None]
        normalized = {_normalize_header(name): name for name in headers}

        question_col = next(
            (normalized[key] for key in ("question", "问题", "q") if key in normalized), None
        )
        truth_col = next(
            (
                normalized[key]
                for key in ("ground_truth", "参考答案", "answer_reference", "gt")
                if key in normalized
            ),
            None,
        )
        if question_col is None or truth_col is None:
            raise SystemExit(f"qa.csv 缺少必要列，实际列头为：{headers}")

        pairs = []
        for row in reader:
            question = (row.get(question_col) or "").strip()
            ground_truth = (row.get(truth_col) or "").strip()
            if question:
                pairs.append({"question": question, "ground_truth": ground_truth})

    if not pairs:
        raise SystemExit(f"qa.csv 中没有可评估的问题：{qa_path}")
    print(f"[step1] 读取黄金问题集完成：{len(pairs)} 条，来源 {qa_path}")
    return pairs


def step2_init_evaluator_models() -> tuple[Any, Any]:
    """
    步骤二：初始化 ragas 的评估模型。

    LLM 取自 thinktank.tool.tool_llm_init（用 LangchainLLMWrapper 包装），
    embeddings 取自 thinktank.tool.bgem3_embedding_tool（封装为 Bgem3RagasEmbeddings）。
    """
    from ragas.llms.base import LangchainLLMWrapper

    llm = _load_project_llm()
    evaluator_llm = LangchainLLMWrapper(llm)
    evaluator_embeddings = Bgem3RagasEmbeddings()
    print("[step2] 评估模型初始化完成：LLM = tool_llm_init，Embedding = BGEM3")
    return evaluator_llm, evaluator_embeddings


def step3_run_rag_for_questions(
    qa_pairs: list[dict[str, str]], keep_history: bool = False
) -> list[dict[str, Any]]:
    """
    步骤三：逐条启动 RAG 主流程，收集生成答案与检索上下文。

    流程入口：QueryMainGraphRunner.create_and_run(state)；
    上下文来源：state["reranked_docs"] 中每个文档的 content 字段；
    答案来源：state["answer"]。
    """
    if not keep_history:
        _patch_chat_history_side_effects()

    from thinktank.query_process.main_graph import QueryMainGraphRunner

    records: list[dict[str, Any]] = []
    total = len(qa_pairs)
    for index, pair in enumerate(qa_pairs, start=1):
        question = pair["question"]
        task_id = f"ragas_eval_{index}"
        state: dict[str, Any] = {
            "original_query": question,
            "session_id": task_id,
            "task_id": task_id,
        }

        print(f"[step3] ({index}/{total}) 正在运行 RAG：{question[:40]}...")
        try:
            final_state = QueryMainGraphRunner.create_and_run(state)
        except Exception as exc:  # 单条偶发失败不中断整批评估
            # 额度耗尽 / 鉴权失败属于全局性故障，后续所有问题都会同样失败，立即中止
            if _is_fatal_llm_error(exc):
                raise SystemExit(f"[step3] {_fatal_llm_error_hint()}\n原始错误：{type(exc).__name__}: {exc}") from exc
            print(f"[step3] 警告：该问题 RAG 流程执行失败（{type(exc).__name__}: {exc}），按空结果记录")
            final_state = {}

        contexts: list[str] = []
        for doc in final_state.get("reranked_docs") or []:
            text = doc.get("content", "") if isinstance(doc, dict) else str(doc)
            text = (text or "").strip()
            if text:
                contexts.append(text)

        records.append(
            {
                "question": question,
                "ground_truth": pair["ground_truth"],
                "answer": (final_state.get("answer") or "").strip(),
                "contexts": contexts,
            }
        )
        print(f"[step3] ({index}/{total}) 完成：{len(contexts)} 段上下文，答案 {len(records[-1]['answer'])} 字")

    return records


def step4_build_ragas_dataset(records: list[dict[str, Any]]) -> Any:
    """
    步骤四：把 RAG 输出转换成 ragas 的 EvaluationDataset。

    字段映射：question -> user_input，answer -> response，
    contexts -> retrieved_contexts，ground_truth -> reference。
    """
    from ragas import EvaluationDataset

    dataset = EvaluationDataset.from_list(
        [
            {
                "user_input": record["question"],
                "response": record["answer"],
                "retrieved_contexts": record["contexts"],
                "reference": record["ground_truth"],
            }
            for record in records
        ]
    )
    print(f"[step4] 构建 ragas 评估数据集完成：{len(records)} 个样本")
    return dataset


def step5_evaluate_metrics(dataset: Any, evaluator_llm: Any, evaluator_embeddings: Any) -> Any:
    """
    步骤五：执行 5 个 ragas 指标评估。

    Faithfulness、Answer Relevancy、Context Precision、Context Recall、Answer Correctness。
    raise_exceptions=False 保证个别样本打分失败时其余样本仍能产出结果（失败项留空）。
    """
    from ragas import evaluate

    metrics = [_resolve_metric_class(name) for name in METRIC_CANDIDATES]
    print("[step5] 开始评估指标：" + "、".join(METRIC_CANDIDATES.keys()))
    result = evaluate(
        dataset=dataset,
        metrics=metrics,
        llm=evaluator_llm,
        embeddings=evaluator_embeddings,
        raise_exceptions=False,
        show_progress=True,
    )

    # raise_exceptions=False 会把打分异常吞掉并写成 NaN；
    # 若 5 个指标全部无分数，说明评估 LLM 本身不可用，不应把这份结果当作评估结论落盘
    score_df = cast(Any, result).to_pandas()
    metric_columns = [column for column in score_df.columns if str(column) in METRIC_CANDIDATES]
    if metric_columns and all(score_df[column].isna().all() for column in metric_columns):
        raise SystemExit(
            "[step5] 5 个指标均未产生有效分数，评估大模型很可能不可用（额度耗尽或鉴权失败）。\n"
            + _fatal_llm_error_hint()
        )

    print("[step5] 指标评估完成")
    return result


def step6_save_result_csv(records: list[dict[str, Any]], result: Any, output_path: Path) -> None:
    """
    步骤六：把逐条明细与 5 个指标分数写入 qa_result.csv（UTF-8 BOM，9 列）。

    context 列由 reranked_docs 的多段文本拼接而成；分数统一保留 4 位小数。
    """
    score_rows = _extract_score_rows(result)
    aligned_scores = _align_score_rows(records, score_rows)

    with output_path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=RESULT_COLUMNS, lineterminator="\r\n")
        writer.writeheader()
        for record, scores in zip(records, aligned_scores):
            writer.writerow(
                {
                    "question": record["question"],
                    "context": _join_contexts(record["contexts"]),
                    "answer": record["answer"],
                    "ground_truth": record["ground_truth"],
                    **scores,
                }
            )

    print(f"[step6] 评估结果已保存：{output_path}（UTF-8 BOM，{len(records)} 行 × {len(RESULT_COLUMNS)} 列）")

    # 顺带输出 5 个指标的均值，便于快速判断整体质量（空值不计入）
    for name in METRIC_CANDIDATES:
        values = [float(scores[name]) for scores in aligned_scores if scores[name]]
        if values:
            print(f"        均值 {name}: {sum(values) / len(values):.4f}")
        else:
            print(f"        均值 {name}: 无有效分数")


def main() -> None:
    """主流程：解析参数，并按 step1 ~ step6 顺序完成读取、跑 RAG、评估与落盘。"""
    parser = argparse.ArgumentParser(description="基于 ragas 的 RAG 评估程序")
    parser.add_argument("--qa", default=str(EVAL_DIR / "qa.csv"), help="输入问题集路径（默认 eval/qa.csv）")
    parser.add_argument(
        "--output", default=str(EVAL_DIR / "qa_result.csv"), help="输出结果路径（默认 eval/qa_result.csv）"
    )
    parser.add_argument("--limit", type=int, default=0, help="只评估前 N 条问题，0 表示全部")
    parser.add_argument(
        "--keep-history",
        action="store_true",
        help="保留 RAG 流程中的 MongoDB 聊天历史读写（默认屏蔽，避免污染线上数据）",
    )
    args = parser.parse_args()

    _require_ragas()
    qa_pairs = step1_load_qa_pairs(Path(args.qa))
    if args.limit > 0:
        qa_pairs = qa_pairs[: args.limit]

    evaluator_llm, evaluator_embeddings = step2_init_evaluator_models()
    records = step3_run_rag_for_questions(qa_pairs, keep_history=args.keep_history)
    if not any(record["answer"] or record["contexts"] for record in records):
        raise SystemExit(
            "[step4] 所有样本的 RAG 输出均为空（无上下文、无答案），通常是上游检索或大模型服务不可用；"
            "跳过评估，不写入 qa_result.csv。"
        )
    dataset = step4_build_ragas_dataset(records)
    result = step5_evaluate_metrics(dataset, evaluator_llm, evaluator_embeddings)
    step6_save_result_csv(records, result, Path(args.output))


if __name__ == "__main__":
    main()
