# E-MATHTOCO Dataset Splitting & Train/Test Isolation Methodology

This document outlines the strict validation methodology used during the development of E-MATHTOCO grading models to prevent label leakage and ensure scientific validity.

## The Leakage Risk: Split-by-Sheet vs. Split-by-Student

In handwriting and answer sheet evaluation models, the most common source of inflated accuracy (and a key target for examiners) is **data leakage**:
- **Split-by-Sheet (Vulnerable)**: If we randomly split individual answer sheet images into train/test sets, sheets belonging to the same student (e.g., student A's sheets for S-1A in train, and S-1B in test) will be split across sets.
  - *Why this is bad*: The CNN model memorizes the unique handwriting style, pen ink color, and scanner artifact patterns of student A. When evaluating student A's S-1B sheet in the test set, the model relies on memorized handwriting style rather than generalized mathematical symbol recognition. This leads to artificially high test accuracy that fails in real-world use.
- **Split-by-Student/Mahasiswa (Isolated & Valid)**: We group the entire dataset by `mahasiswa_id` (student identity) first. All answer sheets belonging to a specific student are kept together in either the training set or the test set.
  - *Why this is correct*: The test set contains only answer sheets from students the model has **never** seen during training. This forces the CNN to learn generic mathematical patterns (e.g., stroke geometry and structural characteristics) rather than individual handwriting styles, ensuring authentic out-of-distribution accuracy.

## The Partitioning Strategy

1. **Student Grouping**: Retrieve all available answer sheet records grouped by `mahasiswa_id`.
2. **Hold-out Splitting**:
   - **Training Set (80%)**: Assigned to optimize weights.
   - **Validation Set (10%)**: Assigned for hyperparameter tuning.
   - **Held-out Test Set (10%)**: Used for final evaluation metrics (as reported in `ai_evaluation_report.md`).
3. **No Overlap Constraint**:
   $$\text{Train Students} \cap \text{Test Students} = \emptyset$$
   This ensures that no student's handwriting from the training set ever leaks into the test set.

## Demonstration Verification Script

We have provided a verification script [train_split_validation.py](file:///d:/PTA/Emathtoco_Project/Emathoco_BackEnd/scripts/train_split_validation.py) that demonstrates this group-based splitting technique. Examiners can execute this script to verify that:
1. Students are divided without overlap.
2. The split ratio is strictly maintained.
3. Confusion matrices can be generated per model without any leakage-induced bias.
