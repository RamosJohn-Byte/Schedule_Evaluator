"""
Reporter Module
Generates output reports: violations_analyzed.csv, violations_summary.txt, unmapped_subjects.txt, entity_groupings.txt
"""

import os
import csv
from collections import defaultdict
from datetime import datetime


def generate_reports(hard_violations, soft_violations, unmapped_subjects, output_folder, config, schedule_rows=None, reference_data=None, schedule_loader=None, sections=None, valid_lecture_lab_pairs=None, error_lecture_lab_pairs=None):
    """
    Generate all output reports.
    """
    os.makedirs(output_folder, exist_ok=True)
    
    # Generate violations CSV
    csv_path = os.path.join(output_folder, 'violations_analyzed.csv')
    generate_violations_csv(hard_violations, soft_violations, csv_path)
    
    # Generate violations summary
    summary_path = os.path.join(output_folder, 'violations_summary.txt')
    generate_violations_summary(hard_violations, soft_violations, summary_path, config)
    
    # Generate unmapped subjects report if any
    if unmapped_subjects:
        unmapped_path = os.path.join(output_folder, 'unmapped_subjects.txt')
        generate_unmapped_report(unmapped_subjects, unmapped_path)
    
    # Generate data conflicts report if any
    all_conflicts = []
    if schedule_loader and schedule_loader.get_data_conflicts():
        all_conflicts.extend(schedule_loader.get_data_conflicts())
    
    # Add lecture-lab faculty mismatch errors to conflicts
    if error_lecture_lab_pairs:
        for pair in error_lecture_lab_pairs:
            all_conflicts.append({
                'type': 'Lecture-Lab Faculty Mismatch',
                'details': pair.error,
                'lecture_section': pair.lecture_section.section_id,
                'lab_section': pair.lab_section.section_id
            })
    
    if all_conflicts:
        conflicts_path = os.path.join(output_folder, 'data_conflicts.txt')
        generate_data_conflicts_report(all_conflicts, conflicts_path)
        print(f"  - data_conflicts.txt ({len(all_conflicts)} conflicts)")
    
    # Generate structural violations CSV
    if schedule_rows and sections:
        struct_path = os.path.join(output_folder, 'structural_violations.csv')
        violation_count = generate_structural_violations_csv(schedule_rows, sections, struct_path)
        if violation_count > 0:
            print(f"  - structural_violations.csv ({violation_count} violations)")
    
    # Generate meeting unification summary
    if schedule_rows and schedule_loader:
        unification_path = os.path.join(output_folder, 'meeting_unification.txt')
        merged_count = generate_meeting_unification_summary(
            schedule_rows, schedule_loader.get_unmerged_rows(), unification_path
        )
        print(f"  - meeting_unification.txt ({len(schedule_rows)} meetings, {merged_count} merged)")
    
    # Generate sections summary
    if sections:
        sections_path = os.path.join(output_folder, 'sections_summary.txt')
        section_count = generate_sections_summary(
            sections, valid_lecture_lab_pairs or [], error_lecture_lab_pairs or [], sections_path
        )
        print(f"  - sections_summary.txt ({section_count} sections)")
    
    # Generate entity groupings debug file (comprehensive debug file)
    if schedule_rows and reference_data and schedule_loader:
        groupings_path = os.path.join(output_folder, 'entity_groupings.txt')
        generate_entity_groupings(
            schedule_rows, reference_data, groupings_path, 
            schedule_loader.get_unmerged_rows(), sections,
            valid_lecture_lab_pairs, error_lecture_lab_pairs
        )
        print(f"  - entity_groupings.txt (schedule views)")
    
    print(f"\nReports generated in: {output_folder}")
    print(f"  - violations_analyzed.csv")
    print(f"  - violations_summary.txt")
    if unmapped_subjects:
        print(f"  - unmapped_subjects.txt ({len(unmapped_subjects)} subjects)")


def generate_violations_csv(hard_violations, soft_violations, filepath):
    """
    Generate detailed CSV with all violations.
    """
    all_violations = []
    
    # Process hard violations
    for v in hard_violations:
        all_violations.append({
            'constraint_category': 'HARD',
            'violation_type': v['type'],
            'entity_type': v.get('entity_type', ''),
            'entity_name': v.get('entity_name', ''),
            'magnitude': v.get('magnitude', 0),
            'penalty': '',  # Hard constraints have no penalty
            'details': v.get('details', '')
        })
    
    # Process soft violations
    for v in soft_violations:
        all_violations.append({
            'constraint_category': 'SOFT',
            'violation_type': v['type'],
            'entity_type': v.get('entity_type', ''),
            'entity_name': v.get('entity_name', ''),
            'magnitude': v.get('magnitude', 0),
            'penalty': v.get('penalty', 0),
            'details': v.get('details', '')
        })
    
    # Write CSV
    fieldnames = ['constraint_category', 'violation_type', 'entity_type', 
                  'entity_name', 'magnitude', 'penalty', 'details']
    
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_violations)
    
    return filepath


def generate_violations_summary(hard_violations, soft_violations, filepath, config):
    """
    Generate human-readable summary of violations.
    """
    lines = []
    lines.append("=" * 80)
    lines.append("SCHEDULE EVALUATION REPORT")
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("=" * 80)
    lines.append("")
    
    # Calculate totals
    hard_total = len(hard_violations)
    soft_total = len(soft_violations)
    total_penalty = sum(v.get('penalty', 0) for v in soft_violations)
    
    # Summary statistics
    lines.append("SUMMARY")
    lines.append("-" * 40)
    lines.append(f"Total Hard Violations: {hard_total}")
    lines.append(f"Total Soft Violations: {soft_total}")
    lines.append(f"Total Penalty Score: {total_penalty:.2f}")
    lines.append("")
    
    # Schedule feasibility
    if hard_total == 0:
        lines.append("✓ SCHEDULE IS FEASIBLE (no hard constraint violations)")
    else:
        lines.append("✗ SCHEDULE IS INFEASIBLE (has hard constraint violations)")
    lines.append("")
    
    # ==========================================================================
    # HARD CONSTRAINTS BREAKDOWN
    # ==========================================================================
    lines.append("=" * 80)
    lines.append("HARD CONSTRAINTS (must be zero for valid schedule)")
    lines.append("=" * 80)
    
    # Group by type
    hard_by_type = defaultdict(list)
    for v in hard_violations:
        hard_by_type[v['type']].append(v)
    
    hard_types = [
        'Faculty Time Conflict',
        'Batch Time Conflict',
        'Room Time Conflict',
        'Room Capacity Exceeded',
        'Max Continuous Class Exceeded',
        'Min Gap Violation',
        'Banned Time Violation',
        'Lecture-Lab Separation'
    ]
    
    for vtype in hard_types:
        violations = hard_by_type.get(vtype, [])
        lines.append("")
        lines.append(f"{vtype}: {len(violations)} violations")
        lines.append("-" * 40)
        
        if not violations:
            lines.append("  (none)")
        else:
            # Show first 10 violations
            for v in violations[:10]:
                lines.append(f"  • {v.get('details', '')}")
            if len(violations) > 10:
                lines.append(f"  ... and {len(violations) - 10} more")
    
    # ==========================================================================
    # SOFT CONSTRAINTS BREAKDOWN
    # ==========================================================================
    lines.append("")
    lines.append("=" * 80)
    lines.append("SOFT CONSTRAINTS (penalized but allowed)")
    lines.append("=" * 80)
    
    # Group by type
    soft_by_type = defaultdict(list)
    for v in soft_violations:
        soft_by_type[v['type']].append(v)
    
    soft_types = [
        'Faculty Overload',
        'Faculty Underfill',
        'Section Overfill',
        'Section Underfill',
        'Min Continuous Class',
        'Excess Gap',
        'Non-Preferred Subject',
        'Friday Late Class',
        'Excess Subjects',
        'External Meeting Conflict'
    ]
    
    for vtype in soft_types:
        violations = soft_by_type.get(vtype, [])
        type_penalty = sum(v.get('penalty', 0) for v in violations)
        
        lines.append("")
        lines.append(f"{vtype}: {len(violations)} violations (penalty: {type_penalty:.2f})")
        lines.append("-" * 40)
        
        if not violations:
            lines.append("  (none)")
        else:
            for v in violations[:10]:
                lines.append(f"  • {v.get('details', '')} [penalty: {v.get('penalty', 0):.2f}]")
            if len(violations) > 10:
                lines.append(f"  ... and {len(violations) - 10} more")
    
    # ==========================================================================
    # PENALTY BREAKDOWN
    # ==========================================================================
    lines.append("")
    lines.append("=" * 80)
    lines.append("PENALTY SCORE BREAKDOWN")
    lines.append("=" * 80)
    lines.append("")
    lines.append(f"Formula: (magnitude ^ {config.PENALTY_EXPONENT}) × weight")
    lines.append("")
    
    for vtype in soft_types:
        violations = soft_by_type.get(vtype, [])
        if violations:
            type_penalty = sum(v.get('penalty', 0) for v in violations)
            type_magnitude = sum(v.get('magnitude', 0) for v in violations)
            lines.append(f"{vtype:35} {len(violations):4} violations | magnitude: {type_magnitude:6} | penalty: {type_penalty:10.2f}")
    
    lines.append("-" * 80)
    lines.append(f"{'TOTAL':35} {soft_total:4} violations | {'':15} | penalty: {total_penalty:10.2f}")
    
    # Write file
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    
    return filepath


def generate_unmapped_report(unmapped_subjects, filepath):
    """
    Generate report of subjects that couldn't be mapped to reference data.
    """
    lines = []
    lines.append("UNMAPPED SUBJECTS REPORT")
    lines.append("=" * 60)
    lines.append("")
    lines.append("The following subjects in the schedule could not be mapped to reference data.")
    lines.append("These rows were processed but may be missing subject-specific information.")
    lines.append("")
    lines.append("-" * 60)
    
    for subject in sorted(unmapped_subjects):
        lines.append(f"  • {subject}")
    
    lines.append("")
    lines.append(f"Total unmapped: {len(unmapped_subjects)}")
    lines.append("")
    lines.append("Possible causes:")
    lines.append("  1. Typo in schedule subject name")
    lines.append("  2. Subject missing from reference subjects.csv")
    lines.append("  3. Different naming convention (spaces, case)")
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    
    return filepath


def generate_data_conflicts_report(conflicts, filepath):
    """
    Generate report of data conflicts detected during meeting merge and lecture-lab pairing.
    """
    lines = []
    lines.append("DATA CONFLICTS REPORT")
    lines.append("=" * 80)
    lines.append("")
    lines.append("These conflicts were detected during data processing.")
    lines.append("")
    lines.append("-" * 80)
    
    for conflict in conflicts:
        lines.append("")
        lines.append(f"TYPE: {conflict['type']}")
        
        # Handle different conflict formats
        if 'meeting' in conflict:
            lines.append(f"MEETING: {conflict['meeting']}")
        if 'row_ids' in conflict:
            lines.append(f"ROW IDs: {', '.join(str(r) for r in conflict['row_ids'])}")
        if 'lecture_section' in conflict:
            lines.append(f"LECTURE SECTION: {conflict['lecture_section']}")
        if 'lab_section' in conflict:
            lines.append(f"LAB SECTION: {conflict['lab_section']}")
        if 'faculty' in conflict:
            lines.append(f"FACULTY ASSIGNED: {', '.join(conflict['faculty'])}")
        if 'rooms' in conflict:
            lines.append(f"ROOMS ASSIGNED: {', '.join(conflict['rooms'])}")
        
        lines.append(f"DETAILS: {conflict['details']}")
        lines.append("-" * 80)
    
    lines.append("")
    lines.append(f"Total conflicts: {len(conflicts)}")
    lines.append("")
    lines.append("ACTION REQUIRED:")
    lines.append("  - Review the INPUT schedule CSV file")
    lines.append("  - For meeting conflicts: ensure only ONE row per meeting has faculty/room data")
    lines.append("  - For lecture-lab conflicts: ensure lecture and lab have SAME faculty assigned")
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    
    return filepath


def generate_structural_violations_csv(schedule_rows, sections, filepath):
    """
    Generate CSV file listing meetings/sections with missing faculty, batches, or rooms.
    """
    violations = []
    
    # Check meetings for missing data
    for meeting in schedule_rows:
        issues = []
        if meeting.get('faculty_id') is None:
            issues.append('Missing Faculty')
        if not meeting.get('all_batch_ids'):
            issues.append('Missing Batches')
        if meeting.get('room_id') is None:
            issues.append('Missing Room')
        
        if issues:
            violations.append({
                'Type': 'Meeting',
                'ID': meeting['meeting_id'],
                'Subject': meeting.get('subject_name', 'N/A'),
                'Day': meeting.get('day', 'N/A'),
                'Time': f"{meeting.get('start_time', '')}-{meeting.get('end_time', '')}",
                'Faculty': ', '.join(meeting.get('all_faculty_names', [])) or 'MISSING',
                'Batches': ', '.join(meeting.get('all_batch_names', [])) or 'MISSING',
                'Room': ', '.join(meeting.get('all_room_names', [])) or 'MISSING',
                'Issues': '; '.join(issues)
            })
    
    # Check sections for missing data
    if sections:
        for section in sections:
            issues = []
            if section.faculty_id is None:
                issues.append('Missing Faculty')
            if not section.batch_ids:
                issues.append('Missing Batches')
            if not section.room_ids:
                issues.append('Missing Rooms')
            
            if issues:
                batches_str = ', '.join(section.batch_names) if section.batch_names else 'MISSING'
                rooms_str = ', '.join(section.room_names) if section.room_names else 'MISSING'
                
                violations.append({
                    'Type': 'Section',
                    'ID': section.section_id,
                    'Subject': section.subject_name,
                    'Day': 'N/A',
                    'Time': 'N/A',
                    'Faculty': section.faculty_name or 'MISSING',
                    'Batches': batches_str,
                    'Room': rooms_str,
                    'Issues': '; '.join(issues)
                })
    
    # Write CSV
    if violations:
        fieldnames = ['Type', 'ID', 'Subject', 'Day', 'Time', 'Faculty', 'Batches', 'Room', 'Issues']
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(violations)
    
    return len(violations)


def generate_meeting_unification_summary(schedule_rows, unmerged_rows, filepath):
    """
    Generate separate file showing meeting unification/merge summary.
    """
    lines = []
    lines.append("=" * 100)
    lines.append("MEETING UNIFICATION SUMMARY")
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("=" * 100)
    lines.append("")
    lines.append(f"Original CSV rows: {len(unmerged_rows)}")
    lines.append(f"Unified meetings: {len(schedule_rows)}")
    lines.append(f"Rows merged: {len(unmerged_rows) - len(schedule_rows)}")
    lines.append("")
    lines.append("Format: [Subject] | [Day Time] | [Faculty [row]] | [Batch [row]] | [Room [row]]")
    lines.append("")
    
    # Show all meetings (both merged and singular)
    merged_count = 0
    singular_count = 0
    
    for meeting in schedule_rows:
        merged_from = meeting.get('merged_from_rows', [])
        if not merged_from:
            # If no merged_from_rows, use meeting_id as the single source
            merged_from = [meeting.get('meeting_id')]
        
        num_source_rows = len(merged_from)
        
        if num_source_rows > 1:
            merged_count += 1
        else:
            singular_count += 1
        
        # Build entity strings showing which row contributed each
        faculty_str = "NO_FACULTY"
        batch_strs = []
        room_str = "NO_ROOM"
        
        # Track which rows contributed which entities
        if unmerged_rows:
            row_map = {r['meeting_id']: r for r in unmerged_rows if r['meeting_id'] in merged_from}
            
            # Find faculty source
            for row_id in merged_from:
                row = row_map.get(row_id)
                if row and row.get('faculty_name'):
                    faculty_str = f"{row['faculty_name']} [{row_id}]"
                    break
            
            # Find batch sources
            batch_map = {}
            for row_id in merged_from:
                row = row_map.get(row_id)
                if row and row.get('batch_name'):
                    batch_map[row['batch_name']] = row_id
            
            if batch_map:
                batch_strs = [f"{batch} [{row_id}]" for batch, row_id in sorted(batch_map.items())]
            
            # Find room source
            for row_id in merged_from:
                row = row_map.get(row_id)
                if row and row.get('room_name'):
                    room_str = f"{row['room_name']} [{row_id}]"
                    break
        
        batches_display = ', '.join(batch_strs) if batch_strs else "NO_BATCH"
        
        lines.append(f"{meeting['subject_name']}")
        lines.append(f"  {meeting['day']} {meeting['start_time']}-{meeting['end_time']}")
        lines.append(f"  {faculty_str}")
        lines.append(f"  {batches_display}")
        lines.append(f"  {room_str}")
        
        # Show merge status
        if num_source_rows > 1:
            lines.append(f"  MERGED from rows: {merged_from}")
        else:
            lines.append(f"  SINGULAR (row {merged_from[0] if merged_from else '?'})")
        lines.append("")
    
    lines.append(f"Total merged meetings: {merged_count}")
    lines.append(f"Total singular meetings: {singular_count}")
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    
    return merged_count


def generate_sections_summary(sections, valid_lecture_lab_pairs, error_lecture_lab_pairs, filepath):
    """
    Generate separate file showing identified sections and lecture-lab pairs.
    """
    lines = []
    lines.append("=" * 100)
    lines.append("SECTIONS SUMMARY")
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("=" * 100)
    lines.append("")
    
    # Day order for sorting
    day_order = {'MONDAY': 1, 'TUESDAY': 2, 'WEDNESDAY': 3, 'THURSDAY': 4, 'FRIDAY': 5, 'SATURDAY': 6, 'SUNDAY': 7}
    
    # =========================================================================
    # SHOW IDENTIFIED SECTIONS
    # =========================================================================
    lines.append("=" * 100)
    lines.append("IDENTIFIED SECTIONS")
    lines.append("=" * 100)
    lines.append(f"Total: {len(sections)}")
    lines.append("Format: [Subject-Section] | [Faculty] | [Students] | [Room(s)] | [Meetings]")
    lines.append("")
    
    for section in sorted(sections, key=lambda s: s.section_id):
        faculty = section.faculty_name or "NO_FACULTY"
        batches = ', '.join(sorted(section.batch_names)) if section.batch_names else "NO_BATCHES"
        rooms = ', '.join(sorted(section.room_names)) if section.room_names else "NO_ROOM"
        
        lines.append(section.section_id)
        lines.append(f"  {faculty}")
        lines.append(f"  {section.total_students} Students ({batches})")
        lines.append(f"  {rooms}")
        lines.append(f"  {len(section.meetings)} Meetings:")
        
        # Show meetings sorted by day
        sorted_meetings = sorted(section.meetings, key=lambda m: (day_order.get(m.get('day', ''), 8), m.get('start_time', '')))
        
        for meeting in sorted_meetings:
            room_name = meeting.get('room_name') or "NO_ROOM"
            lines.append(f"    {meeting['day']:10s} {meeting['start_time']}-{meeting['end_time']} @ {room_name}")
        
        lines.append("")
    
    # =========================================================================
    # SHOW LECTURE-LAB PAIRS
    # =========================================================================
    lines.append("")
    lines.append("=" * 100)
    lines.append("LECTURE-LAB PAIRS")
    lines.append("=" * 100)
    lines.append(f"Valid pairs: {len(valid_lecture_lab_pairs)} (will be checked)")
    lines.append(f"Error pairs: {len(error_lecture_lab_pairs)} (excluded - different faculty)")
    lines.append("")
    
    if valid_lecture_lab_pairs:
        lines.append("VALID PAIRS:")
        lines.append("")
        
        for pair in valid_lecture_lab_pairs:
            lec = pair.lecture_section
            lab = pair.lab_section
            
            faculty = lec.faculty_name or "NO_FACULTY"
            batches = ', '.join(sorted(lec.batch_names)) if lec.batch_names else "NO_BATCHES"
            
            lines.append(f"{lec.section_id} + {lab.section_id} | {faculty} | {batches}")
            
            # Show lecture meetings
            lec_meetings = sorted(lec.meetings, key=lambda m: (day_order.get(m.get('day', ''), 8), m.get('start_time', '')))
            for meeting in lec_meetings:
                room_name = meeting.get('room_name') or "NO_ROOM"
                lines.append(f"  LEC: {meeting['day']:10s} {meeting['start_time']}-{meeting['end_time']} @ {room_name}")
            
            # Show lab meetings
            lab_meetings = sorted(lab.meetings, key=lambda m: (day_order.get(m.get('day', ''), 8), m.get('start_time', '')))
            for meeting in lab_meetings:
                room_name = meeting.get('room_name') or "NO_ROOM"
                lines.append(f"  LAB: {meeting['day']:10s} {meeting['start_time']}-{meeting['end_time']} @ {room_name}")
            
            lines.append("")
    
    if error_lecture_lab_pairs:
        lines.append("")
        lines.append("ERROR PAIRS (excluded from constraint checking):")
        lines.append("")
        
        for pair in error_lecture_lab_pairs:
            lec = pair.lecture_section
            lab = pair.lab_section
            lines.append(f"{lec.section_id} + {lab.section_id}")
            lines.append(f"  ERROR: {pair.error}")
            lines.append("")
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    
    return len(sections)


def generate_entity_groupings(schedule_rows, reference_data, filepath, unmerged_rows=None, sections=None, valid_lecture_lab_pairs=None, error_lecture_lab_pairs=None):
    """
    Generate entity groupings file showing schedule views from different perspectives.
    Provides analytical groupings by faculty, batch, room, and day.
    """
    lines = []
    lines.append("=" * 100)
    lines.append("SCHEDULE GROUPINGS - ANALYTICAL VIEWS")
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("=" * 100)
    lines.append("")
    lines.append("This file shows the schedule organized by different entities:")
    lines.append("  • Group by Faculty - Review individual faculty schedules")
    lines.append("  • Group by Batch - Review individual student batch schedules")
    lines.append("  • Group by Room - Review room utilization")
    lines.append("  • Summary Statistics - Faculty subject counts and overall metrics")
    lines.append("")
    lines.append("For other information, see:")
    lines.append("  • structural_violations.csv - Missing data issues")
    lines.append("  • meeting_unification.txt - How CSV rows were merged")
    lines.append("  • sections_summary.txt - Section identification and lecture-lab pairs")
    lines.append("")
    
    # =========================================================================
    # GROUP BY FACULTY
    # =========================================================================
    lines.append("=" * 100)
    lines.append("GROUPING BY FACULTY")
    lines.append("=" * 100)
    
    by_faculty = defaultdict(list)
    for row in schedule_rows:
        if row['faculty_id'] is not None:
            by_faculty[row['faculty_id']].append(row)
    
    for faculty_id in sorted(by_faculty.keys()):
        meetings = by_faculty[faculty_id]
        faculty_data = reference_data.faculty_by_id.get(faculty_id, {})
        faculty_name = faculty_data.get('faculty_name', str(faculty_id))
        
        lines.append("")
        lines.append(f"FACULTY: {faculty_name} (ID: {faculty_id})")
        lines.append("-" * 80)
        
        # Group by day
        by_day = defaultdict(list)
        for m in meetings:
            by_day[m['day']].append(m)
        
        for day in ['MONDAY', 'TUESDAY', 'WEDNESDAY', 'THURSDAY', 'FRIDAY', 'SATURDAY', 'SUNDAY']:
            if day in by_day:
                day_meetings = sorted(by_day[day], key=lambda x: x['start_minutes'])
                lines.append(f"  {day}:")
                for m in day_meetings:
                    lines.append(f"    Row {m.get('meeting_id', '?'):4} | {m['start_time']}-{m['end_time']} | {m['subject_name']:20} | Room: {m['room_name'] or 'N/A':10} | Batch: {m['batch_name'] or 'N/A'}")
    
    # =========================================================================
    # GROUP BY BATCH
    # =========================================================================
    lines.append("")
    lines.append("=" * 100)
    lines.append("GROUPING BY BATCH")
    lines.append("=" * 100)
    
    by_batch = defaultdict(list)
    for row in schedule_rows:
        if row['batch_id'] is not None:
            by_batch[row['batch_id']].append(row)
    
    for batch_id in sorted(by_batch.keys()):
        meetings = by_batch[batch_id]
        batch_data = reference_data.batches_by_id.get(batch_id, {})
        batch_name = batch_data.get('batch_name', str(batch_id))
        
        lines.append("")
        lines.append(f"BATCH: {batch_name} (ID: {batch_id})")
        lines.append("-" * 80)
        
        by_day = defaultdict(list)
        for m in meetings:
            by_day[m['day']].append(m)
        
        for day in ['MONDAY', 'TUESDAY', 'WEDNESDAY', 'THURSDAY', 'FRIDAY', 'SATURDAY', 'SUNDAY']:
            if day in by_day:
                day_meetings = sorted(by_day[day], key=lambda x: x['start_minutes'])
                lines.append(f"  {day}:")
                for m in day_meetings:
                    lines.append(f"    Row {m.get('meeting_id', '?'):4} | {m['start_time']}-{m['end_time']} | {m['subject_name']:20} | Room: {m['room_name'] or 'N/A':10} | Faculty: {m['faculty_name'] or 'N/A'}")
    
    # =========================================================================
    # GROUP BY ROOM
    # =========================================================================
    lines.append("")
    lines.append("=" * 100)
    lines.append("GROUPING BY ROOM")
    lines.append("=" * 100)
    
    by_room = defaultdict(list)
    for row in schedule_rows:
        if row['room_id'] is not None:
            by_room[row['room_id']].append(row)
    
    for room_id in sorted(by_room.keys()):
        meetings = by_room[room_id]
        room_data = reference_data.rooms_by_id.get(room_id, {})
        room_name = room_data.get('room_name', str(room_id))
        
        lines.append("")
        lines.append(f"ROOM: {room_name} (ID: {room_id})")
        lines.append("-" * 80)
        
        by_day = defaultdict(list)
        for m in meetings:
            by_day[m['day']].append(m)
        
        for day in ['MONDAY', 'TUESDAY', 'WEDNESDAY', 'THURSDAY', 'FRIDAY', 'SATURDAY', 'SUNDAY']:
            if day in by_day:
                day_meetings = sorted(by_day[day], key=lambda x: x['start_minutes'])
                lines.append(f"  {day}:")
                for m in day_meetings:
                    lines.append(f"    Row {m.get('meeting_id', '?'):4} | {m['start_time']}-{m['end_time']} | {m['subject_name']:20} | Faculty: {m['faculty_name'] or 'N/A':15} | Batch: {m['batch_name'] or 'N/A'}")
    
    # =========================================================================
    # SUMMARY STATISTICS
    # =========================================================================
    lines.append("")
    lines.append("=" * 100)
    lines.append("SUMMARY STATISTICS")
    lines.append("=" * 100)
    lines.append(f"Total meetings loaded: {len(schedule_rows)}")
    lines.append(f"Unique faculty with meetings: {len(by_faculty)}")
    lines.append(f"Unique batches with meetings: {len(by_batch)}")
    lines.append(f"Unique rooms with meetings: {len(by_room)}")
    lines.append("")
    
    # Faculty subject counts (for debugging excess subjects)
    lines.append("-" * 50)
    lines.append("FACULTY SUBJECT COUNTS (for excess subjects check):")
    lines.append("-" * 50)
    
    for faculty_id in sorted(by_faculty.keys()):
        meetings = by_faculty[faculty_id]
        faculty_data = reference_data.faculty_by_id.get(faculty_id, {})
        faculty_name = faculty_data.get('faculty_name', str(faculty_id))
        
        subjects = set()
        base_subjects = set()
        for m in meetings:
            subjects.add(m['subject_name'])
            # Get base subject (lecture version)
            subj_id = m.get('subject_id')
            if subj_id:
                subj_data = reference_data.subjects_by_id.get(subj_id, {})
                linked = subj_data.get('linked_subject_id')
                if linked:
                    lec_data = reference_data.subjects_by_id.get(linked, {})
                    base_subjects.add(lec_data.get('subject_name', m['subject_name']))
                else:
                    base_subjects.add(m['subject_name'])
            else:
                base_subjects.add(m['subject_name'])
        
        lines.append(f"  {faculty_name}: {len(base_subjects)} unique subjects (counting lec+lab as 1)")
        lines.append(f"    Raw subjects: {sorted(subjects)}")
        lines.append(f"    Base subjects: {sorted(base_subjects)}")
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    
    return filepath


def print_quick_summary(hard_violations, soft_violations):
    """
    Print a quick console summary.
    """
    hard_total = len(hard_violations)
    soft_total = len(soft_violations)
    total_penalty = sum(v.get('penalty', 0) for v in soft_violations)
    
    print("\n" + "=" * 60)
    print("EVALUATION COMPLETE")
    print("=" * 60)
    
    if hard_total == 0:
        print("✓ FEASIBLE SCHEDULE (no hard violations)")
    else:
        print(f"✗ INFEASIBLE SCHEDULE ({hard_total} hard violations)")
    
    print(f"\nHard Violations: {hard_total}")
    print(f"Soft Violations: {soft_total}")
    print(f"Total Penalty: {total_penalty:.2f}")
    
    # Breakdown by type
    if hard_total > 0:
        print("\nHard violations by type:")
        hard_by_type = defaultdict(int)
        for v in hard_violations:
            hard_by_type[v['type']] += 1
        for vtype, count in sorted(hard_by_type.items(), key=lambda x: -x[1]):
            print(f"  {vtype}: {count}")
    
    print("=" * 60)
