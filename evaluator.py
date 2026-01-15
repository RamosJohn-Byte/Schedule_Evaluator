"""
Schedule Evaluator - Main Entry Point
Evaluates schedules against hard and soft constraints from a CP-SAT optimizer.

Usage:
    python evaluator.py [schedule_path] [reference_folder] [output_folder]
    
Defaults:
    schedule_path: INPUT/schedule.csv
    reference_folder: REFERENCE/
    output_folder: RUNS/RUN_YYYYMMDD_HHMMSS/OUTPUT/
"""

import sys
import os
import shutil
from datetime import datetime

# Import modules
from config_loader import Config
from data_loader import ReferenceData, ScheduleLoader
from section_builder import build_sections, find_lecture_lab_pairs
from hard_constraints import check_all_hard_constraints
from soft_constraints import check_all_soft_constraints
from reporter import generate_reports, print_quick_summary


def create_run_folder(schedule_path, reference_folder):
    """
    Create a timestamped folder with copies of input and reference data.
    Returns the path to the new run folder.
    """
    # Create RUNS folder if it doesn't exist
    runs_folder = "RUNS"
    os.makedirs(runs_folder, exist_ok=True)
    
    # Create timestamped folder name inside RUNS
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    run_folder = os.path.join(runs_folder, f"RUN_{timestamp}")
    
    os.makedirs(run_folder, exist_ok=True)
    
    # Copy reference folder
    ref_dest = os.path.join(run_folder, "REFERENCE")
    if os.path.isdir(reference_folder):
        shutil.copytree(reference_folder, ref_dest)
    
    # Copy input schedule
    input_dest = os.path.join(run_folder, "INPUT")
    os.makedirs(input_dest, exist_ok=True)
    
    if os.path.isfile(schedule_path):
        shutil.copy2(schedule_path, os.path.join(input_dest, os.path.basename(schedule_path)))
    elif os.path.isdir(schedule_path):
        shutil.copytree(schedule_path, input_dest, dirs_exist_ok=True)
    
    # Create output folder
    output_dest = os.path.join(run_folder, "OUTPUT")
    os.makedirs(output_dest, exist_ok=True)
    
    return run_folder, ref_dest, input_dest, output_dest


def main(schedule_path="INPUT/schedule.csv", 
         reference_folder="REFERENCE", 
         output_folder="OUTPUT",
         create_archive=True):
    """
    Main evaluation function.
    
    Args:
        schedule_path: Path to schedule CSV file
        reference_folder: Folder containing reference data CSVs and config.json
        output_folder: Folder for output reports
        create_archive: If True, creates timestamped folder with copies of all data
    """
    
    print("=" * 70)
    print("SCHEDULE EVALUATOR")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    # =========================================================================
    # PHASE 0: CREATE RUN FOLDER (if enabled)
    # =========================================================================
    if create_archive:
        print("\n[0/5] Creating Run Archive...")
        run_folder, ref_copy, input_copy, output_copy = create_run_folder(schedule_path, reference_folder)
        print(f"  ✓ Created: {run_folder}")
        
        # Update paths to use copied data
        reference_folder = ref_copy
        schedule_path = os.path.join(input_copy, os.path.basename(schedule_path))
        output_folder = output_copy
    
    # =========================================================================
    # PHASE 1: LOAD CONFIGURATION
    # =========================================================================
    print("\n[1/5] Loading Configuration...")
    config_path = os.path.join(reference_folder, "config.json")
    config = Config(config_path)
    print(f"  Penalty Exponent: {config.PENALTY_EXPONENT}")
    print(f"  Max Continuous: {config.MAX_CONTINUOUS_CLASS_HOURS}h")
    print(f"  Min Gap: {config.MIN_GAP_HOURS}h")
    
    # =========================================================================
    # PHASE 2: LOAD REFERENCE DATA
    # =========================================================================
    print("\n[2/5] Loading Reference Data...")
    reference_data = ReferenceData(reference_folder)
    
    # =========================================================================
    # PHASE 3: LOAD AND MAP SCHEDULE
    # =========================================================================
    print("\n[3/5] Loading and Mapping Schedule...")
    schedule_loader = ScheduleLoader(reference_data)
    schedule_rows = schedule_loader.load(schedule_path)
    
    if not schedule_rows:
        print("\n✗ ERROR: No valid schedule rows loaded. Cannot continue.")
        return
    
    unmapped_subjects = schedule_loader.get_unmapped_subjects()
    if unmapped_subjects:
        print(f"  ⚠ Unmapped subjects: {', '.join(list(unmapped_subjects)[:5])}" +
              (f" and {len(unmapped_subjects) - 5} more" if len(unmapped_subjects) > 5 else ""))
    
    # =========================================================================
    # PHASE 4: BUILD SECTIONS
    # =========================================================================
    print("\n[4/5] Identifying Sections...")
    sections = build_sections(schedule_rows, reference_data)
    
    # Find lecture-lab pairs
    valid_lecture_lab_pairs, error_lecture_lab_pairs = find_lecture_lab_pairs(sections, reference_data)
    print(f"  ✓ Found {len(valid_lecture_lab_pairs)} valid lecture-lab pairs")
    if error_lecture_lab_pairs:
        print(f"  ⚠ {len(error_lecture_lab_pairs)} lecture-lab pairs with different faculty (excluded)")
    
    # =========================================================================
    # PHASE 5: CHECK CONSTRAINTS
    # =========================================================================
    print("\n[5/5] Checking Constraints...")
    
    print("\n  --- HARD CONSTRAINTS ---")
    hard_violations = check_all_hard_constraints(
        schedule_rows, sections, reference_data, config, 
        valid_lecture_lab_pairs=valid_lecture_lab_pairs
    )
    
    print("\n  --- SOFT CONSTRAINTS ---")
    soft_violations = check_all_soft_constraints(schedule_rows, sections, reference_data, config)
    
    # =========================================================================
    # GENERATE REPORTS
    # =========================================================================
    print("\n" + "-" * 70)
    print("Generating Reports...")
    generate_reports(
        hard_violations, soft_violations, unmapped_subjects, output_folder, config, 
        schedule_rows, reference_data, schedule_loader, sections,
        valid_lecture_lab_pairs=valid_lecture_lab_pairs,
        error_lecture_lab_pairs=error_lecture_lab_pairs
    )
    
    # Print quick summary
    print_quick_summary(hard_violations, soft_violations)
    
    # Return results
    return {
        'hard_violations': hard_violations,
        'soft_violations': soft_violations,
        'unmapped_subjects': unmapped_subjects,
        'schedule_rows': schedule_rows,
        'sections': sections,
        'valid_lecture_lab_pairs': valid_lecture_lab_pairs,
        'error_lecture_lab_pairs': error_lecture_lab_pairs,
        'feasible': len(hard_violations) == 0
    }


if __name__ == "__main__":
    # Parse command line arguments
    args = sys.argv[1:]
    
    schedule_path = args[0] if len(args) > 0 else "INPUT/schedule.csv"
    reference_folder = args[1] if len(args) > 1 else "REFERENCE"
    output_folder = args[2] if len(args) > 2 else None  # Will be set by create_run_folder
    
    # Check if archive creation should be disabled (use --no-archive flag)
    create_archive = "--no-archive" not in args
    
    # Run evaluation
    result = main(schedule_path, reference_folder, output_folder, create_archive=create_archive)
    
    # Exit with appropriate code
    if result and result.get('feasible'):
        sys.exit(0)  # Feasible
    else:
        sys.exit(1)  # Infeasible or error
