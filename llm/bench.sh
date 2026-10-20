#!/bin/bash
set -e

echo '=== vLLM Benchmark (random dataset, isl=8192, osl=1024, 20 qps) ==='
DATE=$(date +%Y%m%d-%H%M%S)
RESULT_FILE="bench-${DATE}.json"
echo "Result file: ${RESULT_FILE}"

vllm bench serve --backend openai-chat \
  --base-url http://vllm:8000 \
  --model falcon-llm \
  --endpoint /v1/chat/completions \
  --tokenizer Qwen/Qwen3.6-35B-A3B-FP8 \
  --label bench \
  --dataset-name random \
  --random-input-len 8192 \
  --random-output-len 1024 \
  --num-prompts 1000 \
  --max-concurrency 128 \
  --request-rate 20 \
  --seed 42 \
  --save-result \
  # --save-detailed \
  --result-dir /results \
  --result-filename "${RESULT_FILE}" \
  --metric-percentiles 50,90,99 \
  --percentile-metrics ttft,tpot,itl,e2el

echo ''
echo "Results: /results/${RESULT_FILE}"
