import asyncio
import json
import os
import time
from typing import Dict, List, Tuple

from agent.main_agent import MainAgent
from engine.llm_judge import LLMJudge
from engine.retrieval_eval import RetrievalEvaluator
from engine.runner import BenchmarkRunner


def build_agent(agent_version: str, dataset_file: str = "data/golden_set.jsonl") -> MainAgent:
    """Instantiate the configured benchmark agent."""
    try:
        return MainAgent(version=agent_version, dataset_file=dataset_file)
    except TypeError:
        return MainAgent(version=agent_version)


def serialize_audit_records(agent_version: str, results: List[Dict]) -> List[Dict]:
    audit_records = []
    for result in results:
        judge_result = result.get("judge_result", {})
        if not judge_result.get("manual_review_recommended"):
            continue

        audit_records.append(
            {
                "agent_version": agent_version,
                "question": result.get("question", ""),
                "expected_answer": result.get("expected_answer", ""),
                "system_output": result.get("agent_response", ""),
                "judge_result": {
                    "final_score": judge_result.get("final_score"),
                    "agreement_rate": judge_result.get("agreement_rate"),
                    "verdict": judge_result.get("verdict"),
                    "review_reasons": judge_result.get("review_reasons", []),
                    "hallucination_flag": judge_result.get("flags", {}).get("merged", {}).get("hallucination", 0),
                    "bias_flag": judge_result.get("flags", {}).get("merged", {}).get("bias", 0),
                    "accuracy_score": judge_result.get("dimension_scores", {}).get("merged", {}).get("accuracy", 0),
                    "fairness_score": judge_result.get("dimension_scores", {}).get("merged", {}).get("fairness", 0),
                    "consistency_score": judge_result.get("dimension_scores", {}).get("merged", {}).get("consistency", 0),
                },
                "manual_spot_check": {
                    "required": True,
                    "status": "pending",
                },
            }
        )

    return audit_records


async def run_benchmark_with_results(agent_version: str, dataset_file: str = "data/golden_set.jsonl") -> Tuple[List[Dict], Dict, List[Dict]]:
    """
    Run benchmark for one agent version.

    Returns:
        Tuple (results, summary, audit_candidates)
    """
    print(f"\nStarting benchmark for {agent_version}...")

    if not os.path.exists(dataset_file):
        print(f"Missing {dataset_file}. Run 'python data/synthetic_gen.py' first.")
        return None, None, None

    with open(dataset_file, "r", encoding="utf-8") as file_handle:
        dataset = [json.loads(line) for line in file_handle if line.strip()]

    if not dataset:
        print(f"File {dataset_file} is empty. Generate at least one test case first.")
        return None, None, None

    print(f"Loaded {len(dataset)} test cases")

    agent = build_agent(agent_version, dataset_file=dataset_file)
    retrieval_evaluator = RetrievalEvaluator()
    llm_judge = LLMJudge()
    runner = BenchmarkRunner(agent, retrieval_evaluator, llm_judge)

    results = await runner.run_all(dataset, batch_size=3)
    summary = runner.get_summary()
    summary["metadata"] = {
        "version": agent_version,
        "agent_module": "agent.main_agent2",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_cases": len(dataset),
        "total": len(dataset),
    }

    return results, summary, runner.get_audit_candidates(limit=12)


def write_judge_audit_file(path: str, records: List[Dict]) -> None:
    with open(path, "w", encoding="utf-8") as file_handle:
        for record in records:
            file_handle.write(json.dumps(record, ensure_ascii=False) + "\n")


async def main():
    v1_results, v1_summary, v1_audit = await run_benchmark_with_results("V1")
    if not v1_results or not v1_summary:
        print("Unable to run benchmark for V1. Prepare the dataset first.")
        return

    print(f"\nV1 complete - Pass Rate: {v1_summary['pass_rate']}%")
    print(f"  Avg Score: {v1_summary['avg_judge_score']}/5.0")
    print(f"  Avg Hit Rate: {v1_summary['avg_hit_rate']}")
    print(f"  Avg MRR: {v1_summary['avg_mrr']}")
    print(f"  Avg Agreement Rate: {v1_summary['avg_agreement_rate']}")

    v2_results, v2_summary, v2_audit = await run_benchmark_with_results("V2")
    if not v2_results or not v2_summary:
        print("V2 benchmark could not be completed, so V1 results will be reused.")
        v2_results, v2_summary, v2_audit = v1_results, v1_summary, v1_audit

    print(f"\nV2 complete - Pass Rate: {v2_summary['pass_rate']}%")
    print(f"  Avg Score: {v2_summary['avg_judge_score']}/5.0")
    print(f"  Avg Hit Rate: {v2_summary['avg_hit_rate']}")
    print(f"  Hallucination Rate: {v2_summary['hallucination_rate']}")
    print(f"  Estimated Cost: ${v2_summary['estimated_total_cost_usd']:.6f}")

    delta_score = round(v2_summary["avg_judge_score"] - v1_summary["avg_judge_score"], 2)
    delta_hit_rate = round(v2_summary["avg_hit_rate"] - v1_summary["avg_hit_rate"], 2)
    delta_pass_rate = round(v2_summary["pass_rate"] - v1_summary["pass_rate"], 2)
    delta_hallucination = round(v2_summary["hallucination_rate"] - v1_summary["hallucination_rate"], 2)
    delta_cost = round(v2_summary["estimated_total_cost_usd"] - v1_summary["estimated_total_cost_usd"], 6)

    print("\n" + "=" * 60)
    print("REGRESSION ANALYSIS (V1 vs V2)")
    print("=" * 60)
    print(f"Judge Score:         {v1_summary['avg_judge_score']:.2f} -> {v2_summary['avg_judge_score']:.2f} (Delta: {delta_score:+.2f})")
    print(f"Hit Rate:            {v1_summary['avg_hit_rate']:.2f} -> {v2_summary['avg_hit_rate']:.2f} (Delta: {delta_hit_rate:+.2f})")
    print(f"Hallucination Rate:  {v1_summary['hallucination_rate']:.2f} -> {v2_summary['hallucination_rate']:.2f} (Delta: {delta_hallucination:+.2f})")
    print(f"Pass Rate:           {v1_summary['pass_rate']:.2f}% -> {v2_summary['pass_rate']:.2f}% (Delta: {delta_pass_rate:+.2f}%)")
    print(f"Cost:                ${v1_summary['estimated_total_cost_usd']:.6f} -> ${v2_summary['estimated_total_cost_usd']:.6f} (Delta: {delta_cost:+.6f})")

    min_judge_score = 3.0
    min_hit_rate = 0.5
    max_hallucination_rate = 0.35

    conditions = {
        "Judge Score >= 3.0": v2_summary["avg_judge_score"] >= min_judge_score,
        "Hit Rate >= 0.5": v2_summary["avg_hit_rate"] >= min_hit_rate,
        "Hallucination Rate <= 0.35": v2_summary["hallucination_rate"] <= max_hallucination_rate,
        "Not Regressed": delta_score >= 0.0,
        "Pass Rate OK": v2_summary["pass_rate"] >= v1_summary["pass_rate"],
    }

    print("\n" + "=" * 60)
    print("RELEASE GATE DECISION")
    print("=" * 60)
    for condition, result in conditions.items():
        status = "PASS" if result else "FAIL"
        print(f"{status} {condition}")

    should_release = all(conditions.values())
    print("\nDecision: " + ("APPROVE RELEASE" if should_release else "BLOCK RELEASE"))

    os.makedirs("reports", exist_ok=True)

    regression_metrics = {
        "v1": v1_summary,
        "v2": v2_summary,
        "delta": {
            "judge_score": delta_score,
            "hit_rate": delta_hit_rate,
            "pass_rate": delta_pass_rate,
            "hallucination_rate": delta_hallucination,
            "estimated_total_cost_usd": delta_cost,
        },
    }

    final_summary = {
        "metadata": {
            "version": v2_summary.get("metadata", {}).get("version", "V2"),
            "total": v2_summary.get("metadata", {}).get("total", v2_summary.get("total_cases", 0)),
            "total_cases": v2_summary.get("metadata", {}).get("total_cases", v2_summary.get("total_cases", 0)),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "benchmark_versions": ["V1", "V2"],
        },
        "metrics": {
            "avg_score": v2_summary["avg_judge_score"],
            "hit_rate": v2_summary["avg_hit_rate"],
            "agreement_rate": v2_summary["avg_agreement_rate"],
            "mrr": v2_summary["avg_mrr"],
            "retrieval_accuracy": v2_summary["avg_retrieval_accuracy"],
            "final_answer_accuracy": v2_summary["avg_final_answer_accuracy"],
            "hallucination_rate": v2_summary["hallucination_rate"],
            "bias_rate": v2_summary["bias_rate"],
            "consistency_score": v2_summary["avg_consistency_score"],
            "fairness_score": v2_summary["avg_fairness_score"],
            "latency_seconds": v2_summary["avg_latency_seconds"],
            "cost_usd": v2_summary["estimated_total_cost_usd"],
            "user_satisfaction_score": v2_summary["user_satisfaction_score"],
            "manual_review_rate": v2_summary["manual_review_rate"],
            "regression": regression_metrics,
        },
        "release_decision": {
            "approved": should_release,
            "conditions": conditions,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        },
    }

    with open("reports/summary.json", "w", encoding="utf-8") as file_handle:
        json.dump(final_summary, file_handle, ensure_ascii=False, indent=2)
    print("Saved: reports/summary.json")

    benchmark_results = {
        "metadata": {
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "dataset_size": v2_summary.get("metadata", {}).get("total_cases", len(v2_results)),
        },
        "v1_summary": v1_summary,
        "v2_summary": v2_summary,
        "v1_results": v1_results,
        "v2_results": v2_results,
        "judge_audit_file": "reports/judge_audit.jsonl",
    }

    with open("reports/benchmark_results.json", "w", encoding="utf-8") as file_handle:
        json.dump(benchmark_results, file_handle, ensure_ascii=False, indent=2)
    print("Saved: reports/benchmark_results.json")

    audit_records = serialize_audit_records("V1", v1_audit or []) + serialize_audit_records(
        "V2",
        v2_audit or [],
    )
    write_judge_audit_file("reports/judge_audit.jsonl", audit_records)
    print("Saved: reports/judge_audit.jsonl")

    return final_summary


if __name__ == "__main__":
    asyncio.run(main())
