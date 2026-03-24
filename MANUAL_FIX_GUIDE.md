# 🔧 Manual Fix Guide - Poor Quality Citation Spans

## 📊 Current Status

- **Files to fix:** 227 files
- **Poor quality spans:** 263 spans
  - Very short (<15 chars): 41 spans
  - Short (15-30 chars): 222 spans

## 🚀 Quick Start

### 1. Start Manual Annotation

```bash
python fix_poor_spans.py
```

**Controls during annotation:**
- Type `full` → Use the suggested full sentence
- Copy-paste → Enter your own custom span text
- Press `Enter` → Skip this span (keep as is)
- Type `quit` → Save progress and exit

### 2. Resume Later (if you quit)

```bash
python fix_poor_spans.py --resume
```

This will skip all already-fixed spans and continue where you left off.

### 3. Copy Fixed Files Back

After you're done fixing all spans:

```bash
python copy_fixed_back.py
```

This copies all fixed files from `manual_review/` back to `done/`.

## 📝 Annotation Tips

### What to look for:

**❌ TOO SHORT - These are poor quality:**
```
"[CITATION_1]"                    # Only citation marker
", lower-limb"                    # Fragment only
"Adapted from [CITATION_2] ."     # Too brief
```

**✅ GOOD - These are acceptable:**
```
"The model shows significant improvement in accuracy compared to baseline methods [CITATION_1] ."

"As demonstrated in previous work [CITATION_2], the approach yields better results."
```

### General Rules:

1. **Include full sentence** - The span should be a complete, meaningful sentence
2. **Remove citation markers** - The tool will show you the sentence with citations removed
3. **Context matters** - Read the surrounding text to understand what the citation supports
4. **When in doubt** - Include more context rather than less

## 📂 File Locations

- **Source files:** `data_outputs/data/task3/done/`
- **Manual review:** `data_outputs/data/task3/manual_review/` (working copy)
- **Log file:** `data_outputs/data/task3/manual_review_log.json`
- **Poor files list:** `data_outputs/data/task3/done/POOR_FILES_TO_FIX.json`

## 🎯 Example Session

```
$ python fix_poor_spans.py

================================================================================
📊 Progress: 1/263 (0%) | Fixed: 0 | Skipped: 0
================================================================================

📄 Doc ID: 9747
🔖 Citation: [CITATION_6]
📏 Current span: 12 chars

📝 CURRENT SPAN (TOO SHORT):
   "[CITATION_6]"

📖 CONTEXT (citation marked with >>>...<<<):
--------------------------------------------------------------------------------
The experimental results are shown in Table 2. We compare our method against
several baselines >>>[CITATION_6]<<< including traditional approaches and
recent deep learning methods. Our approach achieves state-of-the-art performance
across all metrics.
--------------------------------------------------------------------------------

💡 SUGGESTED: Full sentence (citations removed):
   "We compare our method against several baselines including traditional
   approaches and recent deep learning methods."

OPTIONS:
  1. Type 'full' → Use suggested full sentence
  2. Copy-paste → Enter your own span text
  3. Press Enter → Keep current (skip this one)
  4. Type 'quit' → Save progress and exit

Your choice: full

✅ Fixed! (12 → 138 chars)
```

## 🔄 Workflow

```
1. Setup (Done) ✅
   ├── Found 263 poor quality spans
   ├── Copied 227 files to manual_review/
   └── Created annotation tools

2. Manual Annotation (Your turn!) ⏳
   ├── Run: python fix_poor_spans.py
   ├── Review each span
   ├── Fix or skip
   └── Save progress (can quit anytime)

3. Resume (if needed)
   └── Run: python fix_poor_spans.py --resume

4. Copy Back (After done)
   ├── Run: python copy_fixed_back.py
   ├── Verifies quality
   └── Updates done/ folder

5. Final Check ✨
   └── All poor quality spans fixed!
```

## 💡 Pro Tips

1. **Work in batches** - Fix 20-30 spans, take a break, resume later
2. **Use 'full' option** - The suggested sentence is usually correct
3. **Save often** - Type 'quit' to save progress anytime
4. **Check context** - Make sure the span makes sense on its own

## 🆘 Troubleshooting

**Q: I accidentally quit, will I lose progress?**
A: No! All changes are saved immediately. Use `--resume` to continue.

**Q: Can I edit the files manually instead?**
A: Yes, but the tool makes it easier and logs all changes automatically.

**Q: What if I make a mistake?**
A: Check the log file (`manual_review_log.json`) - it records all changes with timestamps.

**Q: How long will this take?**
A: About 1-2 minutes per span on average. Total: ~4-8 hours for all 263 spans. You can do it in multiple sessions!

## 📞 Ready to Start?

```bash
cd /Users/tathiyennhi/Documents/automatic-citation-checking
python fix_poor_spans.py
```

Good luck! 🍀
