# Ablation Spec — Task 2 Citation Mapping (M4 Pro)

## 1. Fixed Config

Không thay đổi giữa các run, trừ khi được đưa vào phase ablation:

```python
model_name             = "bert-base-uncased"
max_length             = 512
seed                   = 42
num_train_epochs       = 3
eval_strategy          = "epoch"
save_strategy          = "epoch"
save_total_limit       = 3
load_best_model_at_end = True
metric_for_best_model  = "f1"
greater_is_better      = True
fp16                   = False
bf16                   = False        # tắt để ổn định trên MPS; bật lại nếu đã test ổn
dataloader_num_workers = 0            # macOS MPS: tránh lỗi fork
logging_steps          = 50
```

---

## 2. Derived Config

Tự suy ra từ config khác, không hardcode:

```python
effective_batch_size = per_device_train_batch_size * gradient_accumulation_steps

total_steps = ceil(num_train_samples / effective_batch_size) * num_train_epochs

warmup_steps = warmup_ratio * total_steps

run_name = f"task2-m4pro-bert-lr{lr}-bs{effective_batch_size}-ep{epochs}-{context_mode}"
# Thêm suffix khi vào phase sau:
# -neg{neg_ratio}
# -wu{warmup_ratio}
# -wd{weight_decay}
```

---

## 3. Batch Derivation Policy (Mac M4 Pro)

Ưu tiên `per_device_train_batch_size` nhỏ để tránh swap trên unified memory:

```
default: per_device_train_batch_size = 8
gradient_accumulation_steps = effective_batch_size / per_device_train_batch_size

eff=16 → per_device=8,  grad_accum=2
eff=32 → per_device=8,  grad_accum=4
eff=64 → per_device=8,  grad_accum=8
```

---

## 4. Baseline Config

Dùng làm mốc ban đầu cho toàn bộ sequential ablation:

```python
BASELINE_CONFIG = {
    "model_name":                  "bert-base-uncased",
    "learning_rate":               3e-5,
    "num_train_epochs":            3,
    "per_device_train_batch_size": 8,
    "gradient_accumulation_steps": 4,
    "effective_batch_size":        32,
    "max_length":                  512,
    "context_mode":                "window_1",
    "neg_ratio":                   3,
    "warmup_ratio":                0.1,
    "weight_decay":                0.01,
    "seed":                        42,
}
```

---

## 5. Sequential Ablation Phases

**Rule:** Mỗi phase chỉ thay đổi **1 tham số**. Các tham số còn lại kế thừa từ **best config của phase trước**, không quay về baseline.

| Phase | Tham số        | Giá trị thử                              | Fix từ phase trước |
|-------|----------------|------------------------------------------|--------------------|
| 1     | learning_rate  | `[1e-5, 3e-5, 5e-5]`                    | baseline           |
| 2     | context_mode   | `['full', 'window_2', 'window_1', 'window_0']` | best LR       |
| 3     | effective_batch| `[16, 32, 64]`                           | best LR + context  |
| 4     | neg_ratio      | `[1, 3, 5]`                              | best LR + context + batch |
| 5     | warmup_ratio   | `[0.05, 0.1, 0.15]`                      | best 4 trên        |
| 6     | weight_decay   | `[0.0, 0.01, 0.1]`                       | best 5 trên        |
| 7     | model_name     | `['bert-base-uncased', 'roberta-base', 'allenai/scibert_scivocab_uncased']` | best config từ phase 1-6 |

**Lưu ý phase 7:** Không ablation lại hyperparameter. Chỉ swap `model_name`, giữ nguyên toàn bộ config tốt nhất từ phase 1-6.

---

## 6. Model Selection Rule

```
primary metric:  f1 (cao hơn là tốt hơn)
tie-breaker:     eval_loss (thấp hơn là tốt hơn)

best_run = run có f1 cao nhất trong phase
           nếu f1 bằng nhau → chọn run có eval_loss thấp hơn
```

---

## 7. Naming Convention

### Notebook file name
```
task2-m4pro-bert-phase{phase}-{param_name}.ipynb
```
Ví dụ:
```
task2-m4pro-bert-phase1-lr.ipynb
task2-m4pro-bert-phase2-context.ipynb
```

### Run name (wandb + output dir)
```
task2-m4pro-bert-lr{lr}-bs{eff_batch}-ep{epochs}-{context_mode}
```
Thêm suffix khi vào phase 4+:
```
task2-m4pro-bert-lr3e-5-bs32-ep3-window_1-neg3-wu0.1-wd0.01
```

---

## 8. Output Structure

```
outputs/
  checkpoints/{run_name}/     ← checkpoint từng epoch
  models/{run_name}/          ← best model sau training
  configs/{run_name}.json     ← full config của run đó
  results/
    ablation_summary.csv      ← tổng hợp tất cả run: run_name, f1, eval_loss, ...
```

---

## 9. Notebook Template Structure

Mỗi notebook sinh ra phải có đúng thứ tự cell:

1. Setup & Imports
2. Wandb Login
3. Data Paths
4. **Config Block** ← chỉ cần thay đổi block này giữa các run
5. Load Data
6. Tokenization
7. Load Model
8. Metrics
9. Training Arguments ← tự tính từ config block
10. Train
11. Evaluation
12. Save Model & Report → ghi vào `ablation_summary.csv`
