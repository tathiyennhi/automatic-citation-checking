# 📋 Decision Log: Val/Poor Manual Labeling

**Date:** 2026-03-17
**Topic:** Có nên manual label 205 files trong `val/poor/` hay không?

---

## 🎯 Context

- **Val hiện tại:** 2,794 files (0% short spans, PERFECT quality)
- **Val/poor:** 205 files (2.1% short spans, lower quality)
- **Tổng val:** 2,999 files
- **Train:** 54,993 files
- **Tỉ lệ Train:Val:** 95.2:4.8

---

## ⚖️ DEBATE: Manual Label val/poor?

### ✅ Arguments FOR (Ủng hộ manual label)

1. **Tăng val size:**
   - Val: 2,794 → 2,999 (+7.3%)
   - Tỉ lệ: 4.8% → 5.2%

2. **Val set lớn hơn = evaluation chính xác hơn:**
   - Margin of error giảm
   - Có thể tune hyperparameters tốt hơn

3. **Tận dụng data có sẵn:**
   - 205 files đã được extract và annotate (partial)
   - Chỉ cần fix annotation

### ❌ Arguments AGAINST (Phản đối manual label)

#### 1. **Effort quá cao, gain quá thấp**
```
Effort: 10-17 giờ (2-3 ngày full-time)
Gain:   +7.3% val (205 files)
ROI:    0.43% gain per hour (VERY LOW!)
```

#### 2. **Val hiện tại ĐÃ ĐỦ TỐT**
```
Size:   2,794 files (trong "Good" range: 2,000-5,000)
Quality: 0% short spans (PERFECT!)
Margin of error: ±3.7% (acceptable)
Statistical power: Đủ để evaluate model
```

#### 3. **Val/poor có quality issues**
```
- 2.1% short spans (vs 0% trong val/)
- 19% lowercase fragments
- Avg span: 168 chars (vs 210 trong val/)
- 56% từ ollama:llama3.1:8b (LLM yếu)
```

**Ví dụ poor quality:**
- File 793.label: `"the serine 5 phosphorylation marks..."` ← Lowercase start
- File 260.label: Text chỉ 97 chars, span = toàn bộ text

#### 4. **Có alternatives tốt hơn**

| Option | Effort | Gain | ROI |
|--------|--------|------|-----|
| **A. Manual label val/poor** | **17h** | **+7.3% val** | **0.43%/h** |
| B. Move train→val (1k files) | 0.5h | +35.8% val | 71.6%/h |
| C. Giữ nguyên, train model | 0h | Có model! | ∞ |

#### 5. **Precedent từ famous datasets**
```
ImageNet: 1.28M train / 50k val = 96:4 (3.9% val)
COCO:     118k train / 5k val   = 96:4 (4.1% val)
Current:  55k train / 2.8k val  = 95:5 (4.8% val)

→ Val% hiện tại CAO HƠN ImageNet & COCO!
```

#### 6. **Val quality > Val quantity**
```
Val phải sạch để đánh giá model chính xác
Validation set quality RẤT QUAN TRỌNG
Nếu merge poor → làm GIẢM val quality
```

---

## 🔍 Logic Detect "Poor" Files

### Data Source Issues (Text bị lỗi):
1. Text < 50 chars → Poor
2. Câu bắt đầu lowercase (trừ "e.g.", "i.e.") → Poor
3. Không có dấu câu (. ! ?) → Poor
4. Encoding error (�, \ufffd) → Poor
5. >10% special characters → Poor

### Annotation Issues (Gán nhãn sai):
1. Không có citation spans → Poor
2. Span text rỗng → Poor
3. s_span/e_span không khớp text → Poor
4. Citation marker không trong span → Poor
5. Span text không tồn tại trong text → Poor

**Classification:**
```
File → Check text → Text issues?
                    ├─ YES → "data_source_issue"
                    └─ NO  → Check annotation → Annotation issues?
                                                 ├─ YES → "annotation_issue"
                                                 └─ NO  → "looks_good"
```

---

## 📊 Statistical Analysis

### Val set size guidelines:
```
Minimum (unreliable):   100-500 samples
Acceptable:           1,000-2,000 samples
Good:                 2,000-5,000 samples  ← CURRENT: 2,794
Excellent:            5,000+ samples
```

### Margin of Error (95% CI):
```
Current (2,794):  ±3.7%  (acceptable, close to excellent)
After (+205):     ±3.6%  (marginal improvement)

Difference: 0.1% improvement NOT worth 17 hours!
```

---

## 🎯 FINAL DECISION: ❌ KHÔNG manual label

### Khuyến nghị:

#### **Option 1: XÓA val/poor/ (RECOMMENDED!)**
```bash
rm -rf data_outputs/data/task3/val/poor/
```

**Lý do:**
- Giữ val sạch 100% (0% short spans)
- 2,794 files ĐỦ cho evaluation
- Ready to train ngay
- Priority: Train model > Tăng val

#### **Option 2: Train trước, đánh giá sau**
- Train với 2,794 val files
- Monitor model performance
- **CHỈ tăng val NẾU:**
  - Model overfit nhanh trên val
  - Val metrics không stable
  - Thực sự cần thêm val data (rare!)

#### **Option 3: Nếu thực sự cần thêm val**
- Move 1,000-2,000 files từ train → val
- Effort: 0.5h vs 17h
- Gain: +35-71% vs +7.3%
- Better ROI: 70%/h vs 0.43%/h

---

## 💡 Key Takeaways

1. **Val quality > Val quantity** (especially for validation set!)
2. **2,794 files ĐỦ** cho dataset 55k samples (precedent: ImageNet, COCO)
3. **ROI của manual label RẤT THẤP:** 0.43%/h
4. **17 giờ effort không đáng với +7.3% gain**
5. **Val hiện tại ĐÃ PERFECT** (0% short spans) - đừng làm hỏng!

---

## 📝 Next Steps

### Immediate (Cleanup):
1. ✅ Xóa `val/poor/` (205 files)
2. ✅ Xóa `manual_review/` (189 files LLM-generated)
3. ✅ Final dataset:
   - Train: 54,993 files
   - Val: 2,794 files
   - Ratio: 95.2:4.8

### After Training:
- Monitor validation metrics
- CHỈ tăng val nếu thấy issues
- Otherwise: SHIP IT! 🚀

---

## 🔗 References

- `classify_poor_files.py` - Logic detect poor files
- `analyze_val_poor.py` - Val/poor quality analysis
- `analyze_train_val_ratio.py` - Train/val ratio analysis
- `poor_files_classification.json` - Classification results

---

## 📌 Conclusion

**17 hours manual label để được +7.3% val = NOT WORTH IT!**

✅ **XÓA val/poor, train model ngay!**

**Val quality matters more than val size.**

---

_End of Decision Log_
