"""
Hard Constraints Module
Checks for hard constraint violations that MUST be zero for a valid schedule.
These are reported with magnitude only (no penalty weights).
"""

from collections import defaultdict
from data_loader import minutes_to_time_str, format_duration


def check_overlap(start1, end1, start2, end2):
    """Check if two time ranges overlap."""
    return start1 < end2 and start2 < end1


def calculate_overlap_duration(start1, end1, start2, end2):
    """Calculate the overlap duration in minutes."""
    overlap_start = max(start1, start2)
    overlap_end = min(end1, end2)
    return max(0, overlap_end - overlap_start)


# =============================================================================
# FACULTY TIME CONFLICTS
# =============================================================================

def check_faculty_time_conflicts(schedule_rows, reference_data):
    """
    Check for faculty time conflicts.
    Violation: Same faculty assigned to overlapping time slots on same day.
    """
    violations = []
    
    # Group by faculty_id
    by_faculty = defaultdict(list)
    for row in schedule_rows:
        # Handle merged meetings - add to all faculty involved
        if row.get('all_faculty_ids'):
            for faculty_id in row['all_faculty_ids']:
                by_faculty[faculty_id].append(row)
        elif row.get('faculty_id') is not None:
            by_faculty[row['faculty_id']].append(row)
    
    for faculty_id, meetings in by_faculty.items():
        faculty_data = reference_data.faculty_by_id.get(faculty_id, {})
        faculty_name = faculty_data.get('faculty_name', str(faculty_id))
        
        # Group by day
        by_day = defaultdict(list)
        for m in meetings:
            by_day[m['day']].append(m)
        
        for day, day_meetings in by_day.items():
            # Sort by start time
            day_meetings.sort(key=lambda x: x['start_minutes'])
            
            # Check each pair
            for i in range(len(day_meetings)):
                for j in range(i + 1, len(day_meetings)):
                    m1 = day_meetings[i]
                    m2 = day_meetings[j]
                    
                    if check_overlap(m1['start_minutes'], m1['end_minutes'],
                                     m2['start_minutes'], m2['end_minutes']):
                        overlap = calculate_overlap_duration(
                            m1['start_minutes'], m1['end_minutes'],
                            m2['start_minutes'], m2['end_minutes']
                        )
                        
                        violations.append({
                            'type': 'Faculty Time Conflict',
                            'entity_type': 'Faculty',
                            'entity_name': faculty_name,
                            'day': day,
                            'meeting1_id': m1.get('meeting_id'),
                            'meeting2_id': m2.get('meeting_id'),
                            'meeting1': f"{m1['subject_name']} @ {m1['start_time']}-{m1['end_time']}",
                            'meeting2': f"{m2['subject_name']} @ {m2['start_time']}-{m2['end_time']}",
                            'magnitude': overlap,
                            'details': f"{faculty_name} on {day}: Row {m1.get('meeting_id')} ({m1['start_time']}-{m1['end_time']}) overlaps Row {m2.get('meeting_id')} ({m2['start_time']}-{m2['end_time']}) - {format_duration(overlap)} overlap"
                        })
    
    return violations


# =============================================================================
# BATCH TIME CONFLICTS
# =============================================================================

def check_batch_time_conflicts(schedule_rows, reference_data):
    """
    Check for batch time conflicts.
    Violation: Same batch assigned to overlapping time slots on same day.
    """
    violations = []
    
    # Group by batch_id
    by_batch = defaultdict(list)
    for row in schedule_rows:
        # Handle merged meetings - add to all batches involved
        if row.get('all_batch_ids'):
            for batch_id in row['all_batch_ids']:
                by_batch[batch_id].append(row)
        elif row.get('batch_id') is not None:
            by_batch[row['batch_id']].append(row)
    
    for batch_id, meetings in by_batch.items():
        batch_data = reference_data.batches_by_id.get(batch_id, {})
        batch_name = batch_data.get('batch_name', str(batch_id))
        
        # Group by day
        by_day = defaultdict(list)
        for m in meetings:
            by_day[m['day']].append(m)
        
        for day, day_meetings in by_day.items():
            day_meetings.sort(key=lambda x: x['start_minutes'])
            
            for i in range(len(day_meetings)):
                for j in range(i + 1, len(day_meetings)):
                    m1 = day_meetings[i]
                    m2 = day_meetings[j]
                    
                    if check_overlap(m1['start_minutes'], m1['end_minutes'],
                                     m2['start_minutes'], m2['end_minutes']):
                        overlap = calculate_overlap_duration(
                            m1['start_minutes'], m1['end_minutes'],
                            m2['start_minutes'], m2['end_minutes']
                        )
                        
                        violations.append({
                            'type': 'Batch Time Conflict',
                            'entity_type': 'Batch',
                            'entity_name': batch_name,
                            'day': day,
                            'meeting1_id': m1.get('meeting_id'),
                            'meeting2_id': m2.get('meeting_id'),
                            'meeting1': f"{m1['subject_name']} @ {m1['start_time']}-{m1['end_time']}",
                            'meeting2': f"{m2['subject_name']} @ {m2['start_time']}-{m2['end_time']}",
                            'magnitude': overlap,
                            'details': f"Batch {batch_name} on {day}: Row {m1.get('meeting_id')} ({m1['start_time']}-{m1['end_time']}) overlaps Row {m2.get('meeting_id')} ({m2['start_time']}-{m2['end_time']}) - {format_duration(overlap)} overlap"
                        })
    
    return violations


# =============================================================================
# ROOM TIME CONFLICTS
# =============================================================================

def check_room_time_conflicts(schedule_rows, reference_data):
    """
    Check for room time conflicts.
    Violation: Same room assigned to overlapping time slots on same day.
    """
    violations = []
    
    # Group by room_id
    by_room = defaultdict(list)
    for row in schedule_rows:
        # Handle merged meetings - add to all rooms involved
        if row.get('all_room_ids'):
            for room_id in row['all_room_ids']:
                by_room[room_id].append(row)
        elif row.get('room_id') is not None:
            by_room[row['room_id']].append(row)
    
    for room_id, meetings in by_room.items():
        room_data = reference_data.rooms_by_id.get(room_id, {})
        room_name = room_data.get('room_name', str(room_id))
        
        # Group by day
        by_day = defaultdict(list)
        for m in meetings:
            by_day[m['day']].append(m)
        
        for day, day_meetings in by_day.items():
            day_meetings.sort(key=lambda x: x['start_minutes'])
            
            for i in range(len(day_meetings)):
                for j in range(i + 1, len(day_meetings)):
                    m1 = day_meetings[i]
                    m2 = day_meetings[j]
                    
                    if check_overlap(m1['start_minutes'], m1['end_minutes'],
                                     m2['start_minutes'], m2['end_minutes']):
                        overlap = calculate_overlap_duration(
                            m1['start_minutes'], m1['end_minutes'],
                            m2['start_minutes'], m2['end_minutes']
                        )
                        
                        violations.append({
                            'type': 'Room Time Conflict',
                            'entity_type': 'Room',
                            'entity_name': room_name,
                            'day': day,
                            'meeting1_id': m1.get('meeting_id'),
                            'meeting2_id': m2.get('meeting_id'),
                            'meeting1': f"{m1['subject_name']} @ {m1['start_time']}-{m1['end_time']}",
                            'meeting2': f"{m2['subject_name']} @ {m2['start_time']}-{m2['end_time']}",
                            'magnitude': overlap,
                            'details': f"Room {room_name} on {day}: Row {m1.get('meeting_id')} ({m1['start_time']}-{m1['end_time']}) overlaps Row {m2.get('meeting_id')} ({m2['start_time']}-{m2['end_time']}) - {format_duration(overlap)} overlap"
                        })
    
    return violations


# =============================================================================
# ROOM CAPACITY (HARD)
# =============================================================================

def check_room_capacity(sections, reference_data):
    """
    Check if section students exceed room capacity.
    Violation: total_students > room_capacity
    """
    violations = []
    
    for section in sections:
        if section.room_id is None or section.room_capacity is None:
            continue
        
        if section.total_students > section.room_capacity:
            over_by = section.total_students - section.room_capacity
            
            violations.append({
                'type': 'Room Capacity Exceeded',
                'entity_type': 'Section',
                'entity_name': section.section_id,
                'subject': section.subject_name,
                'room': section.room_name,
                'total_students': section.total_students,
                'room_capacity': section.room_capacity,
                'magnitude': over_by,
                'details': f"{section.section_id}: {section.total_students} students in {section.room_name} (capacity {section.room_capacity}), exceeds by {over_by}"
            })
    
    return violations


# =============================================================================
# MAX CONTINUOUS CLASS (HARD)
# =============================================================================

def check_max_continuous_class(schedule_rows, reference_data, config):
    """
    Check if any entity has continuous class block > MAX_CONTINUOUS_CLASS_HOURS.
    Applies to both faculty and batches.
    """
    violations = []
    max_minutes = config.MAX_CONTINUOUS_CLASS_MINUTES
    
    # Check faculty
    violations.extend(_check_continuous_for_entity_type(
        schedule_rows, reference_data, config, 'faculty', max_minutes
    ))
    
    # Check batches
    violations.extend(_check_continuous_for_entity_type(
        schedule_rows, reference_data, config, 'batch', max_minutes
    ))
    
    return violations


def _check_continuous_for_entity_type(schedule_rows, reference_data, config, entity_type, max_minutes):
    """Helper to check continuous blocks for a specific entity type."""
    violations = []
    
    # Group by entity
    id_field = f'{entity_type}_id'
    name_field = f'{entity_type}_name'
    all_ids_field = f'all_{entity_type}_ids'
    
    by_entity = defaultdict(list)
    for row in schedule_rows:
        # Handle merged meetings - add to all entities involved
        if row.get(all_ids_field):
            for entity_id in row[all_ids_field]:
                by_entity[entity_id].append(row)
        elif row.get(id_field) is not None:
            by_entity[row[id_field]].append(row)
    
    for entity_id, meetings in by_entity.items():
        # Get entity name
        if entity_type == 'faculty':
            entity_data = reference_data.faculty_by_id.get(entity_id, {})
            entity_name = entity_data.get('faculty_name', str(entity_id))
        else:
            entity_data = reference_data.batches_by_id.get(entity_id, {})
            entity_name = entity_data.get('batch_name', str(entity_id))
        
        # Group by day
        by_day = defaultdict(list)
        for m in meetings:
            by_day[m['day']].append(m)
        
        for day, day_meetings in by_day.items():
            day_meetings.sort(key=lambda x: x['start_minutes'])
            
            if not day_meetings:
                continue
            
            # Track continuous blocks
            block_start = day_meetings[0]['start_minutes']
            block_end = day_meetings[0]['end_minutes']
            
            for i in range(len(day_meetings)):
                current_start = day_meetings[i]['start_minutes']
                current_end = day_meetings[i]['end_minutes']
                
                if i < len(day_meetings) - 1:
                    next_start = day_meetings[i + 1]['start_minutes']
                    
                    if current_end == next_start:  # Continuous
                        block_end = day_meetings[i + 1]['end_minutes']
                    else:  # Gap found - check block
                        block_duration = block_end - block_start
                        
                        if block_duration > max_minutes:
                            over_by = block_duration - max_minutes
                            violations.append({
                                'type': 'Max Continuous Class Exceeded',
                                'entity_type': entity_type.capitalize(),
                                'entity_name': entity_name,
                                'day': day,
                                'block_start': minutes_to_time_str(block_start),
                                'block_end': minutes_to_time_str(block_end),
                                'block_duration': block_duration,
                                'max_allowed': max_minutes,
                                'magnitude': over_by,
                                'details': f"{entity_name} on {day}: {format_duration(block_duration)} continuous ({minutes_to_time_str(block_start)}-{minutes_to_time_str(block_end)}), exceeds max {format_duration(max_minutes)} by {format_duration(over_by)}"
                            })
                        
                        # Start new block
                        block_start = next_start
                        block_end = day_meetings[i + 1]['end_minutes']
                else:
                    # Final block check
                    block_duration = current_end - block_start
                    
                    if block_duration > max_minutes:
                        over_by = block_duration - max_minutes
                        violations.append({
                            'type': 'Max Continuous Class Exceeded',
                            'entity_type': entity_type.capitalize(),
                            'entity_name': entity_name,
                            'day': day,
                            'block_start': minutes_to_time_str(block_start),
                            'block_end': minutes_to_time_str(current_end),
                            'block_duration': block_duration,
                            'max_allowed': max_minutes,
                            'magnitude': over_by,
                            'details': f"{entity_name} on {day}: {format_duration(block_duration)} continuous ({minutes_to_time_str(block_start)}-{minutes_to_time_str(current_end)}), exceeds max {format_duration(max_minutes)} by {format_duration(over_by)}"
                        })
    
    return violations


# =============================================================================
# MIN GAP (HARD ONLY)
# =============================================================================

def check_min_gap(schedule_rows, reference_data, config):
    """
    Check if gap between meetings < MIN_GAP_HOURS.
    This is a HARD constraint only - no soft penalty.
    """
    violations = []
    min_gap_minutes = config.MIN_GAP_MINUTES
    
    # Check faculty
    violations.extend(_check_gap_for_entity_type(
        schedule_rows, reference_data, config, 'faculty', min_gap_minutes
    ))
    
    # Check batches
    violations.extend(_check_gap_for_entity_type(
        schedule_rows, reference_data, config, 'batch', min_gap_minutes
    ))
    
    return violations


def _check_gap_for_entity_type(schedule_rows, reference_data, config, entity_type, min_gap_minutes):
    """Helper to check gaps for a specific entity type."""
    violations = []
    
    id_field = f'{entity_type}_id'
    all_ids_field = f'all_{entity_type}_ids'
    
    by_entity = defaultdict(list)
    for row in schedule_rows:
        # Handle merged meetings - add to all entities involved
        if row.get(all_ids_field):
            for entity_id in row[all_ids_field]:
                by_entity[entity_id].append(row)
        elif row.get(id_field) is not None:
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
                
                # Gap exists but is less than minimum
                if gap > 0 and gap < min_gap_minutes:
                    under_by = min_gap_minutes - gap
                    
                    violations.append({
                        'type': 'Min Gap Violation',
                        'entity_type': entity_type.capitalize(),
                        'entity_name': entity_name,
                        'day': day,
                        'gap_start': minutes_to_time_str(current_end),
                        'gap_end': minutes_to_time_str(next_start),
                        'gap_minutes': gap,
                        'min_required': min_gap_minutes,
                        'magnitude': under_by,
                        'details': f"{entity_name} on {day}: gap of {format_duration(gap)} ({minutes_to_time_str(current_end)}-{minutes_to_time_str(next_start)}), below min {format_duration(min_gap_minutes)} by {format_duration(under_by)}"
                    })
    
    return violations


# =============================================================================
# BANNED TIMES
# =============================================================================

def check_banned_times(schedule_rows, reference_data):
    """
    Check if meetings overlap with banned times.
    """
    violations = []
    
    for banned in reference_data.banned_times:
        banned_day = banned['day']
        banned_start = banned['start_minutes']
        banned_end = banned['end_minutes']
        banned_faculty = banned.get('faculty_name', '')
        
        for meeting in schedule_rows:
            # Check day match
            if meeting['day'] != banned_day:
                continue
            
            # If banned time is faculty-specific, check faculty match
            if banned_faculty:
                # Check all faculty in merged meetings
                faculty_names_to_check = []
                if meeting.get('all_faculty_names'):
                    faculty_names_to_check = meeting['all_faculty_names']
                elif meeting.get('faculty_name'):
                    faculty_names_to_check = [meeting['faculty_name']]
                
                if banned_faculty not in faculty_names_to_check:
                    continue
            
            # Check time overlap
            if check_overlap(meeting['start_minutes'], meeting['end_minutes'],
                             banned_start, banned_end):
                overlap = calculate_overlap_duration(
                    meeting['start_minutes'], meeting['end_minutes'],
                    banned_start, banned_end
                )
                
                entity_desc = banned_faculty if banned_faculty else "All"
                
                violations.append({
                    'type': 'Banned Time Violation',
                    'entity_type': 'Meeting',
                    'entity_name': meeting['subject_name'],
                    'day': banned_day,
                    'meeting_time': f"{meeting['start_time']}-{meeting['end_time']}",
                    'banned_time': f"{banned['start_time']}-{banned['end_time']}",
                    'applies_to': entity_desc,
                    'magnitude': overlap,
                    'details': f"{meeting['subject_name']} on {banned_day} {meeting['start_time']}-{meeting['end_time']} overlaps banned time {banned['start_time']}-{banned['end_time']} ({format_duration(overlap)} overlap)"
                })
    
    return violations


# =============================================================================
# LECTURE-LAB SEPARATION
# =============================================================================

def check_lecture_lab_separation(valid_pairs, reference_data):
    """
    Check lecture-lab separation constraint for valid pairs only.
    
    Rules:
    - Only 1 lecture meeting and 1 lab meeting per day (per section)
    - If lecture and lab are on the SAME day:
      - Must be back-to-back (lecture.end == lab.start OR lab.end == lecture.start)
      - Must be in the SAME room
    
    Violations:
    - Same day + NOT back-to-back → VIOLATION
    - Same day + back-to-back + different rooms → VIOLATION
    """
    violations = []
    
    for pair in valid_pairs:
        lecture_section = pair.lecture_section
        lab_section = pair.lab_section
        
        # Group meetings by day
        lecture_by_day = defaultdict(list)
        lab_by_day = defaultdict(list)
        
        for meeting in lecture_section.meetings:
            lecture_by_day[meeting['day']].append(meeting)
        
        for meeting in lab_section.meetings:
            lab_by_day[meeting['day']].append(meeting)
        
        # Find days where BOTH lecture and lab have meetings
        common_days = set(lecture_by_day.keys()) & set(lab_by_day.keys())
        
        for day in common_days:
            lec_meetings = lecture_by_day[day]
            lab_meetings = lab_by_day[day]
            
            # For each pair of lecture-lab meetings on same day
            for lec_m in lec_meetings:
                for lab_m in lab_meetings:
                    # Check if back-to-back
                    is_back_to_back = (
                        lec_m['end_minutes'] == lab_m['start_minutes'] or
                        lab_m['end_minutes'] == lec_m['start_minutes']
                    )
                    
                    # Get rooms
                    lec_room = lec_m.get('room_name') or lec_m.get('room_id')
                    lab_room = lab_m.get('room_name') or lab_m.get('room_id')
                    lec_room_id = lec_m.get('room_id')
                    lab_room_id = lab_m.get('room_id')
                    
                    same_room = (lec_room_id == lab_room_id) and lec_room_id is not None
                    
                    if not is_back_to_back:
                        # VIOLATION: Same day but not back-to-back
                        violations.append({
                            'type': 'Lecture-Lab Separation',
                            'entity_type': 'Section',
                            'entity_name': f"{lecture_section.section_id} + {lab_section.section_id}",
                            'day': day,
                            'lecture_time': f"{lec_m['start_time']}-{lec_m['end_time']}",
                            'lab_time': f"{lab_m['start_time']}-{lab_m['end_time']}",
                            'lecture_room': lec_room or 'N/A',
                            'lab_room': lab_room or 'N/A',
                            'magnitude': 1,
                            'details': f"{lecture_section.section_id}/{lab_section.section_id} on {day}: Lecture ({lec_m['start_time']}-{lec_m['end_time']}) and Lab ({lab_m['start_time']}-{lab_m['end_time']}) not back-to-back"
                        })
                    elif not same_room:
                        # VIOLATION: Back-to-back but different rooms
                        violations.append({
                            'type': 'Lecture-Lab Separation',
                            'entity_type': 'Section',
                            'entity_name': f"{lecture_section.section_id} + {lab_section.section_id}",
                            'day': day,
                            'lecture_time': f"{lec_m['start_time']}-{lec_m['end_time']}",
                            'lab_time': f"{lab_m['start_time']}-{lab_m['end_time']}",
                            'lecture_room': lec_room or 'N/A',
                            'lab_room': lab_room or 'N/A',
                            'magnitude': 1,
                            'details': f"{lecture_section.section_id}/{lab_section.section_id} on {day}: Back-to-back but different rooms (Lecture: {lec_room or 'N/A'}, Lab: {lab_room or 'N/A'})"
                        })
                    # else: back-to-back + same room = OK
    
    return violations


# =============================================================================
# MAIN FUNCTION
# =============================================================================

def check_all_hard_constraints(schedule_rows, sections, reference_data, config, valid_lecture_lab_pairs=None):
    """
    Run all hard constraint checks.
    Returns list of violations with magnitude (no penalty).
    """
    violations = []
    
    print("  Checking faculty time conflicts...")
    violations.extend(check_faculty_time_conflicts(schedule_rows, reference_data))
    
    print("  Checking batch time conflicts...")
    violations.extend(check_batch_time_conflicts(schedule_rows, reference_data))
    
    print("  Checking room time conflicts...")
    violations.extend(check_room_time_conflicts(schedule_rows, reference_data))
    
    print("  Checking room capacity...")
    violations.extend(check_room_capacity(sections, reference_data))
    
    print("  Checking max continuous class...")
    violations.extend(check_max_continuous_class(schedule_rows, reference_data, config))
    
    print("  Checking min gap...")
    violations.extend(check_min_gap(schedule_rows, reference_data, config))
    
    print("  Checking banned times...")
    violations.extend(check_banned_times(schedule_rows, reference_data))
    
    print("  Checking lecture-lab separation...")
    if valid_lecture_lab_pairs is not None:
        violations.extend(check_lecture_lab_separation(valid_lecture_lab_pairs, reference_data))
    
    return violations
