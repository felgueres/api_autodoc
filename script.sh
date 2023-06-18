python run.py \
    --task extract \
    --task_file_path extract_evals.jsonl \
    --method_retrieve top_k \
    --method_generate sample \
    --temperature 0.5 \
    --task_start_idx 0 \
    --task_end_idx 2