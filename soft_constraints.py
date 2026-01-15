"""
Soft Constraints Module
Checks for soft constraint violations that are penalized but not strictly forbidden.
These are reported with magnitude AND weighted penalty scores.
"""

from collections import defaultdict
from data_loader import minutes_to_time_str, format_duration


# =============================================================================
# FACULTY LOAD (OVERLOAD/UNDERFILL)
# =============================================================================

def check_faculty_overload(schedule_rows, reference_data, config):
    """
    Check if faculty teaching hours exceed max_hours.
    Penalty: per minute over.
    """
    violations = []
    
    # Calculate total teaching minutes per faculty
    faculty_minutes = defaultdict(int)
    
    for row in schedule_rows:
        if row['faculty_id'] is not None:
            duration = row['end_minutes'] - row['start_minutes']
            faculty_minutes[row['faculty_id']] += duration
    
    for faculty_id, total_minutes in faculty_minutes.items():
        faculty_data = reference_data.faculty_by_id.get(faculty_id, {})
        faculty_name = faculty_data.get('faculty_name', str(faculty_id))
        max_minutes = faculty_data.get('max_hours_per_week', 0) * 60
        
        if max_minutes > 0 and total_minutes > max_minutes:
            over_by = total_minutes - max_minutes
            penalty = config.apply_penalty(over_by, config.FACULTY_OVERLOAD_PER_MINUTE)
            
            violations.append({
                'type': 'Faculty Overload',
                'entity_type': 'Faculty',
                'entity_name': faculty_name,
                'total_minutes': total_minutes,
                'max_minutes': max_minutes,
                'magnitude': over_by,
                'penalty': penalty,
                'details': f"{faculty_name}: {format_duration(total_minutes)} assigned, max {format_duration(max_minutes)}, over by {format_duration(over_by)}"
            })
    
    return violations


def check_faculty_underfill(schedule_rows, reference_data, config):
    """
    Check if faculty teaching hours below min_hours.
    Penalty: per minute under.
    """
    violations = []
    
    # Calculate total teaching minutes per faculty
    faculty_minutes = defaultdict(int)
    
    for row in schedule_rows:
        if row['faculty_id'] is not None:
            duration = row['end_minutes'] - row['start_minutes']
            faculty_minutes[row['faculty_id']] += duration
    
    # Check all faculty (even those with 0 classes)
    for faculty_id, faculty_data in reference_data.faculty_by_id.items():
        faculty_name = faculty_data.get('faculty_name', str(faculty_id))
        min_minutes = faculty_data.get('min_hours_per_week', 0) * 60
        total_minutes = faculty_minutes.get(faculty_id, 0)
        
        if min_minutes > 0 and total_minutes < min_minutes:
            under_by = min_minutes - total_minutes
            penalty = config.apply_penalty(under_by, config.FACULTY_UNDERFILL_PER_MINUTE)
            
            violations.append({
                'type': 'Faculty Underfill',
                'entity_type': 'Faculty',
                'entity_name': faculty_name,
                'total_minutes': total_minutes,
                'min_minutes': min_minutes,
                'magnitude': under_by,
                'penalty': penalty,
                'details': f"{faculty_name}: {format_duration(total_minutes)} assigned, min {format_duration(min_minutes)}, under by {format_duration(under_by)}"
            })
    
    return violations


# =============================================================================
# SECTION FILL (OVERFILL/UNDERFILL)
# =============================================================================

def check_section_overfill(sections, reference_data, config):
    """
    Check if section students exceed OPTIMAL room capacity (soft penalty).
    Different from hard constraint which uses ACTUAL capacity.
    """
    violations = []
    
    for section in sections:
        if section.room_id is None:
            continue
        
        room_data = reference_data.rooms_by_id.get(section.room_id, {})
        optimal_capacity = room_data.get('optimal_capacity', room_data.get('capacity', 0))
        
        if optimal_capacity and section.total_students > optimal_capacity:
            over_by = section.total_students - optimal_capacity
            penalty = config.apply_penalty(over_by, config.SECTION_OVERFILL_PER_STUDENT)
            
            violations.append({
                'type': 'Section Overfill',
                'entity_type': 'Section',
                'entity_name': section.section_id,
                'subject': section.subject_name,
                'room': section.room_name,
                'total_students': section.total_students,
                'optimal_capacity': optimal_capacity,
                'magnitude': over_by,
                'penalty': penalty,
                'details': f"{section.section_id}: {section.total_students} students in {section.room_name} (optimal {optimal_capacity}), over by {over_by}"
            })
    
    return violations


def check_section_underfill(sections, reference_data, config):
    """
    Check if section students are significantly below room capacity.
    Penalty: per student under a threshold.
    """
    violations = []
    
    for section in sections:
        if section.room_id is None:
            continue
        
        room_data = reference_data.rooms_by_id.get(section.room_id, {})
        min_capacity = room_data.get('min_capacity', 0)
        
        if min_capacity and section.total_students < min_capacity:
            under_by = min_capacity - section.total_students
            penalty = config.apply_penalty(under_by, config.SECTION_UNDERFILL_PER_STUDENT)
            
            violations.append({
                'type': 'Section Underfill',
                'entity_type': 'Section',
                'entity_name': section.section_id,
                'subject': section.subject_name,
                'room': section.room_name,
                'total_students': section.total_students,
                'min_capacity': min_capacity,
                'magnitude': under_by,
                'penalty': penalty,
                'details': f"{section.section_id}: {section.total_students} students in {section.room_name} (min {min_capacity}), under by {under_by}"
            })
    
    return violations


# =============================================================================
# MIN CONTINUOUS CLASS (SOFT)
# =============================================================================

def check_min_continuous_class(schedule_rows, reference_data, config):
    """
    Check if continuous blocks are below MIN_CONTINUOUS_CLASS_HOURS.
    This is a SOFT penalty (unlike max continuous which is HARD).
    """
    violations = []
    min_minutes = config.MIN_CONTINUOUS_CLASS_MINUTES
    
    # Check faculty
    violations.extend(_check_min_continuous_for_entity(
        schedule_rows, reference_data, config, 'faculty', min_minutes
    ))
    
    # Check batches
    violations.extend(_check_min_continuous_for_entity(
        schedule_rows, reference_data, config, 'batch', min_minutes
    ))
    
    return violations


def _check_min_continuous_for_entity(schedule_rows, reference_data, config, entity_type, min_minutes):
    """Helper to check minimum continuous blocks for an entity type."""
    violations = []
    
    id_field = f'{entity_type}_id'
    
    by_entity = defaultdict(list)
    for row in schedule_rows:
        if row.get(id_field) is not None:
            by_entity[row[id_field]].append(row)
    
    for entity_id, meetings in by_entity.items():
        if entity_type == 'faculty':
            entity_data = reference_data.faculty_by_id.get(entity_id, {})
            entity_name = entity_data.get('faculty_name', str(entity_id))
        else:
            entity_data = reference_data.batches_by_id.get(entity_id, {})
            entity_name = entity_data.get('batch_name', str(entity_id))
        
        by_day = defaultdict(list)
        for m in meetings:
            by_day[m['day']].append(m)
        
        for day, day_meetings in by_day.items():
            day_meetings.sort(key=lambda x: x['start_minutes'])
            
            if not day_meetings:
                continue
            
            # Find continuous blocks
            blocks = []
            block_start = day_meetings[0]['start_minutes']
            block_end = day_meetings[0]['end_minutes']
            
            for i in range(1, len(day_meetings)):
                current = day_meetings[i]
                
                if current['start_minutes'] == block_end:  # Continuous
                    block_end = current['end_minutes']
                else:
                    blocks.append((block_start, block_end))
                    block_start = current['start_minutes']
                    block_end = current['end_minutes']
            
            blocks.append((block_start, block_end))  # Last block
            
            # Check each block
            for block_start, block_end in blocks:
                block_duration = block_end - block_start
                
                if block_duration > 0 and block_duration < min_minutes:
                    under_by = min_minutes - block_duration
                    penalty = config.apply_penalty(under_by, config.MIN_CONTINUOUS_PENALTY_PER_MINUTE)
                    
                    violations.append({
                        'type': 'Min Continuous Class',
                        'entity_type': entity_type.capitalize(),
                        'entity_name': entity_name,
                        'day': day,
                        'block_start': minutes_to_time_str(block_start),
                        'block_end': minutes_to_time_str(block_end),
                        'block_duration': block_duration,
                        'min_required': min_minutes,
                        'magnitude': under_by,
                        'penalty': penalty,
                        'details': f"{entity_name} on {day}: {format_duration(block_duration)} block ({minutes_to_time_str(block_start)}-{minutes_to_time_str(block_end)}), below min {format_duration(min_minutes)} by {format_duration(under_by)}"
                    })
    
    return violations


# =============================================================================
# EXCESS GAP (SOFT)
# =============================================================================

def check_excess_gap(schedule_rows, reference_data, config):
    """
    Check for excessive gaps between meetings.
    Gap > EXCESS_GAP_HOURS incurs penalty.
    """
    violations = []
    excess_threshold = config.EXCESS_GAP_MINUTES
    
    # Check faculty
    violations.extend(_check_excess_gap_for_entity(
        schedule_rows, reference_data, config, 'faculty', excess_threshold
    ))
    
    # Check batches
    violations.extend(_check_excess_gap_for_entity(
        schedule_rows, reference_data, config, 'batch', excess_threshold
    ))
    
    return violations


def _check_excess_gap_for_entity(schedule_rows, reference_data, config, entity_type, excess_threshold):
    """Helper to check excess gaps for an entity type."""
    violations = []
    
    id_field = f'{entity_type}_id'
    
    by_entity = defaultdict(list)
    for row in schedule_rows:
        if row.get(id_field) is not None:
            by_entity[row[id_field]].append(row)
    
    for entity_id, meetings in by_entity.items():
        if entity_type == 'faculty':
            entity_data = reference_data.faculty_by_id.get(entity_id, {})
            entity_name = entity_data.get('faculty_name', str(entity_id))
        else:
            entity_data = reference_data.batches_by_id.get(entity_id, {})
            entity_name = entity_data.get('batch_name', str(entity_id))
        
        by_day = defaultdict(list)
        for m in meetings:
            by_day[m['day']].append(m)
        
        for day, day_meetings in by_day.items():
            day_meetings.sort(key=lambda x: x['start_minutes'])
            
            for i in range(len(day_meetings) - 1):
                current_end = day_meetings[i]['end_minutes']
                next_start = day_meetings[i + 1]['start_minutes']
                gap = next_start - current_end
                
                if gap > excess_threshold:
                    excess = gap - excess_threshold
                    penalty = config.apply_penalty(excess, config.EXCESS_GAP_PENALTY_PER_MINUTE)
                    
                    violations.append({
                        'type': 'Excess Gap',
                        'entity_type': entity_type.capitalize(),
                        'entity_name': entity_name,
                        'day': day,
                        'gap_start': minutes_to_time_str(current_end),
                        'gap_end': minutes_to_time_str(next_start),
                        'gap_minutes': gap,
                        'threshold': excess_threshold,
                        'magnitude': excess,
                        'penalty': penalty,
                        'details': f"{entity_name} on {day}: {format_duration(gap)} gap ({minutes_to_time_str(current_end)}-{minutes_to_time_str(next_start)}), exceeds threshold {format_duration(excess_threshold)} by {format_duration(excess)}"
                    })
    
    return violations


# =============================================================================
# NON-PREFERRED SUBJECT
# =============================================================================

def check_non_preferred_subject(schedule_rows, reference_data, config):
    """
    Check if faculty is assigned to a non-preferred subject.
    Based on faculty preference ratings.
    Counts each section separately (not just unique subject types).
    """
    violations = []
    
    # Group by faculty and subject to count sections
    from collections import defaultdict
    faculty_subject_sections = defaultdict(list)
    
    for row in schedule_rows:
        if row['faculty_id'] is None or row['subject_id'] is None:
            continue
        
        faculty_data = reference_data.faculty_by_id.get(row['faculty_id'], {})
        
        # Check preferred subjects
        preferred_subjects = faculty_data.get('preferred_subjects', [])
        if preferred_subjects and row['subject_id'] not in preferred_subjects:
            pair_key = (row['faculty_id'], row['subject_id'])
            faculty_subject_sections[pair_key].append(row)
    
    # Create a violation for each section of non-preferred subject
    for (faculty_id, subject_id), sections in faculty_subject_sections.items():
        faculty_data = reference_data.faculty_by_id.get(faculty_id, {})
        faculty_name = faculty_data.get('faculty_name', str(faculty_id))
        
        subject_data = reference_data.subjects_by_id.get(subject_id, {})
        subject_name = subject_data.get('subject_name', str(subject_id))
        
        penalty = config.NON_PREFERRED_SUBJECT_PENALTY
        num_sections = len(sections)
        
        violations.append({
            'type': 'Non-Preferred Subject',
            'entity_type': 'Faculty',
            'entity_name': faculty_name,
            'subject': subject_name,
            'magnitude': num_sections,
            'penalty': penalty * num_sections,
            'details': f"{faculty_name} assigned to {num_sections} section(s) of non-preferred subject {subject_name}"
        })
    
    return violations


# =============================================================================
# FRIDAY LATE CLASSES
# =============================================================================

def check_friday_late_classes(schedule_rows, reference_data, config):
    """
    Check for classes on Friday after FRIDAY_LATE_HOUR.
    """
    violations = []
    late_threshold = config.FRIDAY_LATE_MINUTES
    
    for row in schedule_rows:
        if row['day'].upper() == 'FRIDAY' or row['day'].upper() == 'FRI':
            if row['end_minutes'] > late_threshold:
                over_by = row['end_minutes'] - late_threshold
                penalty = config.apply_penalty(over_by, config.FRIDAY_LATE_PENALTY_PER_MINUTE)
                
                violations.append({
                    'type': 'Friday Late Class',
                    'entity_type': 'Meeting',
                    'entity_name': row['subject_name'],
                    'day': row['day'],
                    'time': f"{row['start_time']}-{row['end_time']}",
                    'end_minutes': row['end_minutes'],
                    'threshold': late_threshold,
                    'magnitude': over_by,
                    'penalty': penalty,
                    'details': f"{row['subject_name']} on {row['day']} ends at {row['end_time']}, {format_duration(over_by)} past {minutes_to_time_str(late_threshold)}"
                })
    
    return violations


# =============================================================================
# EXCESS SUBJECTS PER FACULTY
# =============================================================================

def get_base_subject_name(subject_name, reference_data, subject_id):
    """
    Get the base subject name (lecture version) for counting purposes.
    If this is a lab, return the linked lecture's name.
    E.g., ICS103L -> ICS103, ICS103_L -> ICS103
    """
    if subject_id is None:
        # Try to determine from name if it's a lab
        name = str(subject_name).upper().replace('_', '')
        if name.endswith('L') or name.endswith('LAB'):
            # Remove lab suffix
            base = name.rstrip('L').rstrip('AB')
            return base
        return subject_name
    
    subject_data = reference_data.subjects_by_id.get(subject_id, {})
    linked_id = subject_data.get('linked_subject_id')
    
    if linked_id:
        # This is a lab, get the lecture name
        lecture_data = reference_data.subjects_by_id.get(linked_id, {})
        return lecture_data.get('subject_name', subject_name)
    
    return subject_name


def check_excess_subjects(schedule_rows, reference_data, config):
    """
    Check if faculty is assigned too many unique subjects.
    Lecture and lab of same subject count as ONE subject.
    """
    violations = []
    max_subjects = config.MAX_SUBJECTS_PER_FACULTY
    
    # Count unique BASE subjects per faculty (lecture+lab = 1)
    faculty_subjects = defaultdict(set)
    faculty_subject_details = defaultdict(set)  # For display: actual subject names
    
    for row in schedule_rows:
        if row['faculty_id'] is not None and row['subject_name'] is not None:
            base_name = get_base_subject_name(row['subject_name'], reference_data, row.get('subject_id'))
            faculty_subjects[row['faculty_id']].add(base_name)
            faculty_subject_details[row['faculty_id']].add(row['subject_name'])
    
    for faculty_id, base_subjects in faculty_subjects.items():
        if len(base_subjects) > max_subjects:
            faculty_data = reference_data.faculty_by_id.get(faculty_id, {})
            faculty_name = faculty_data.get('faculty_name', str(faculty_id))
            
            excess = len(base_subjects) - max_subjects
            penalty = config.apply_penalty(excess, config.EXCESS_SUBJECTS_PENALTY_PER_SUBJECT)
            
            # Show all actual subject names for clarity
            actual_subjects = sorted(faculty_subject_details[faculty_id])
            
            violations.append({
                'type': 'Excess Subjects',
                'entity_type': 'Faculty',
                'entity_name': faculty_name,
                'subject_count': len(base_subjects),
                'max_allowed': max_subjects,
                'subjects': sorted(base_subjects),
                'magnitude': excess,
                'penalty': penalty,
                'details': f"{faculty_name} has {len(base_subjects)} unique subjects (max {max_subjects}), excess {excess}: {', '.join(sorted(base_subjects))} (including: {', '.join(actual_subjects)})"
            })
    
    return violations


# =============================================================================
# EXTERNAL MEETING CONFLICTS
# =============================================================================

def check_external_meeting_conflicts(schedule_rows, reference_data, config):
    """
    Check for conflicts with faculty external meetings.
    """
    violations = []
    
    # Load external meetings if available
    if not hasattr(reference_data, 'external_meetings') or not reference_data.external_meetings:
        return violations
    
    for ext in reference_data.external_meetings:
        ext_faculty = ext.get('faculty_name', '')
        ext_day = ext['day']
        ext_start = ext['start_minutes']
        ext_end = ext['end_minutes']
        
        for meeting in schedule_rows:
            # Check faculty match
            if meeting['faculty_name'] != ext_faculty:
                continue
            
            # Check day
            if meeting['day'] != ext_day:
                continue
            
            # Check overlap
            if meeting['start_minutes'] < ext_end and ext_start < meeting['end_minutes']:
                overlap_start = max(meeting['start_minutes'], ext_start)
                overlap_end = min(meeting['end_minutes'], ext_end)
                overlap = overlap_end - overlap_start
                
                penalty = config.apply_penalty(overlap, config.EXTERNAL_MEETING_CONFLICT_PENALTY_PER_MINUTE)
                
                violations.append({
                    'type': 'External Meeting Conflict',
                    'entity_type': 'Faculty',
                    'entity_name': ext_faculty,
                    'day': ext_day,
                    'meeting': f"{meeting['subject_name']} @ {meeting['start_time']}-{meeting['end_time']}",
                    'external_meeting': f"{ext.get('description', 'External')} @ {ext['start_time']}-{ext['end_time']}",
                    'magnitude': overlap,
                    'penalty': penalty,
                    'details': f"{ext_faculty} on {ext_day}: {meeting['subject_name']} conflicts with external meeting ({format_duration(overlap)} overlap)"
                })
    
    return violations


# =============================================================================
# MAIN FUNCTION
# =============================================================================

def check_all_soft_constraints(schedule_rows, sections, reference_data, config):
    """
    Run all soft constraint checks.
    Returns list of violations with magnitude AND penalty.
    """
    violations = []
    
    print("  Checking faculty overload...")
    violations.extend(check_faculty_overload(schedule_rows, reference_data, config))
    
    print("  Checking faculty underfill...")
    violations.extend(check_faculty_underfill(schedule_rows, reference_data, config))
    
    print("  Checking section overfill...")
    violations.extend(check_section_overfill(sections, reference_data, config))
    
    print("  Checking section underfill...")
    violations.extend(check_section_underfill(sections, reference_data, config))
    
    print("  Checking min continuous class...")
    violations.extend(check_min_continuous_class(schedule_rows, reference_data, config))
    
    print("  Checking excess gap...")
    violations.extend(check_excess_gap(schedule_rows, reference_data, config))
    
    print("  Checking non-preferred subjects...")
    violations.extend(check_non_preferred_subject(schedule_rows, reference_data, config))
    
    print("  Checking Friday late classes...")
    violations.extend(check_friday_late_classes(schedule_rows, reference_data, config))
    
    print("  Checking excess subjects per faculty...")
    violations.extend(check_excess_subjects(schedule_rows, reference_data, config))
    
    print("  Checking external meeting conflicts...")
    violations.extend(check_external_meeting_conflicts(schedule_rows, reference_data, config))
    
    return violations
