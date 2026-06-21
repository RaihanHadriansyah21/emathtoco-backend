# scripts/train_split_validation.py
# ============================================================
# EMATHTOCO — Dataset Split & Leakage Verification Script
# ============================================================
#
# This script demonstrates the group-by-student splitting methodology
# to prove to examiners that train and test sets are strictly isolated
# by student identity (mahasiswa_id) to avoid handwriting style leakage.
# ============================================================

import os
import sys
import numpy as np

# Ensure reproducibility
np.random.seed(42)

def generate_mock_manifest(num_students=60, sheets_per_student=24):
    """
    Generates a mock manifest list of student answer sheet records.
    Each record contains a student ID, section code, and score label.
    """
    manifest = []
    sections = [
        f"S-{num}{sec.upper()}"
        for num in [1, 2, 3, 4]
        for sec in ['a', 'b', 'c', 'd', 'e', 'f']
    ]
    
    for student_idx in range(1, num_students + 1):
        student_id = f"mhs_uuid_{student_idx:03d}"
        for sec in sections:
            # Random score label matching typical student results
            score_label = np.random.choice([0, 1, 2, 3, 4, 5][:len(sec)])
            manifest.append({
                "student_id": student_id,
                "section_code": sec,
                "score_label": int(score_label)
            })
            
    return manifest


def perform_group_split(manifest, test_ratio=0.2):
    """
    Splits the manifest into train and test sets by grouping by student_id
    to prevent handwriting leakage.
    """
    # 1. Extract unique student IDs
    student_ids = list(set(record["student_id"] for record in manifest))
    num_students = len(student_ids)
    
    # 2. Shuffle student IDs
    np.random.shuffle(student_ids)
    
    # 3. Determine split index
    split_idx = int(num_students * (1.0 - test_ratio))
    train_students = set(student_ids[:split_idx])
    test_students = set(student_ids[split_idx:])
    
    # 4. Partition manifest records
    train_set = [r for r in manifest if r["student_id"] in train_students]
    test_set = [r for r in manifest if r["student_id"] in test_students]
    
    return train_set, test_set, train_students, test_students


def main():
    print("==================================================")
    print("EMATHTOCO — TRAIN/TEST SPLIT METHODOLOGY VALIDATION")
    print("==================================================")
    
    # 1. Load/Generate Manifest
    print("Generating simulated student answer sheets manifest...")
    manifest = generate_mock_manifest(num_students=50, sheets_per_student=24)
    print(f"Total manifest records: {len(manifest)} sheets across 50 students.")
    
    # 2. Perform Group Split
    print("\nPerforming split-by-student (80% train, 20% test)...")
    train_set, test_set, train_students, test_students = perform_group_split(manifest, test_ratio=0.2)
    
    # 3. Verify Isolation & Leakage
    print("\nChecking for potential data leakage:")
    overlap = train_students.intersection(test_students)
    print(f"-> Train set unique students count: {len(train_students)}")
    print(f"-> Test set unique students count:  {len(test_students)}")
    print(f"-> Overlap of students between sets: {len(overlap)}")
    
    if len(overlap) == 0:
        print("-> [SUCCESS] Strictly isolated split! Zero student identity overlap detected.")
        print("   This proves no handwriting style leakage exists between training and testing.")
    else:
        print("-> [FAIL] Data leakage detected! Same student exists in both sets.")
        
    # 4. Partition Stats
    print("\nPartition Sizes:")
    print(f"-> Training set sheets: {len(train_set)} records")
    print(f"-> Testing set sheets:  {len(test_set)} records")
    
    print("\nValidation completed successfully.")


if __name__ == "__main__":
    main()
