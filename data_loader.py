"""
Data Loader Module
Loads reference data and schedule, handles name-to-ID mapping.
"""

import pandas as pd
import os
from datetime import datetime


def time_to_minutes(time_str):
    """Convert HH:MM time string to minutes from midnight."""
    try:
        if pd.isna(time_str):
            return 0
        t = datetime.strptime(str(time_str).strip(), "%H:%M")
        return t.hour * 60 + t.minute
    except:
        return 0


def minutes_to_time_str(minutes):
    """Convert minutes from midnight to HH:MM format."""
    hours = int(minutes) // 60
    mins = int(minutes) % 60
    return f"{hours:02d}:{mins:02d}"


def format_duration(minutes):
    """Format minutes as readable duration."""
    if minutes <= 0:
        return "0 mins"
    hours, mins = divmod(int(minutes), 60)
    parts = []
    if hours > 0:
        parts.append(f"{hours} hr{'s' if hours != 1 else ''}")
    if mins > 0:
        parts.append(f"{mins} min{'s' if mins != 1 else ''}")
    return " ".join(parts)


def normalize_subject_name(name):
    """
    Normalize subject name for matching.
    Remove all spaces and convert to uppercase.
    Example: "ICS 103" -> "ICS103", "CS SIP" -> "CSSIP"
    """
    if pd.isna(name) or not name:
        return ""
    return str(name).replace(" ", "").replace(".", "").upper()


class ReferenceData:
    """Container for all reference data with lookup dictionaries."""
    
    def __init__(self, reference_folder="REFERENCE"):
        self.reference_folder = reference_folder
        
        # Primary dictionaries (keyed by name for mapping from schedule)
        self.faculty_by_name = {}      # faculty_name -> {faculty_id, min_load, max_load, ...}
        self.subjects_by_name = {}     # normalized_subject_name -> {subject_id, ...}
        self.rooms_by_name = {}        # room_name -> {room_id, capacity}
        self.batches_by_name = {}      # batch_name -> {batch_id, population}
        
        # Secondary dictionaries (keyed by ID for reverse lookup)
        self.faculty_by_id = {}
        self.subjects_by_id = {}
        self.rooms_by_id = {}
        self.batches_by_id = {}
        
        # Banned times list
        self.banned_times = []
        
        # Load all data
        self._load_all()
    
    def _load_all(self):
        """Load all reference CSV files."""
        self._load_faculty()
        self._load_subjects()
        self._load_rooms()
        self._load_batches()
        self._load_banned_times()
        
        print(f"  ✓ Loaded {len(self.faculty_by_name)} faculty")
        print(f"  ✓ Loaded {len(self.subjects_by_name)} subjects")
        print(f"  ✓ Loaded {len(self.rooms_by_name)} rooms")
        print(f"  ✓ Loaded {len(self.batches_by_name)} batches")
        print(f"  ✓ Loaded {len(self.banned_times)} banned time slots")
    
    def _load_faculty(self):
        """Load faculty.csv"""
        path = os.path.join(self.reference_folder, "faculty.csv")
        if not os.path.exists(path):
            print(f"  ⚠ Warning: {path} not found")
            return
        
        df = pd.read_csv(path)
        for _, row in df.iterrows():
            faculty_id = row['faculty_id']
            faculty_name = str(row['faculty_name']).strip()
            
            # Parse preferred subjects (semicolon-separated, convert to int)
            preferred = []
            if pd.notna(row.get('preferred_subjects')):
                preferred = [int(s.strip()) for s in str(row['preferred_subjects']).split(';') if s.strip()]
            
            # Parse qualified subjects (semicolon-separated, convert to int)
            qualified = []
            if pd.notna(row.get('qualified_subjects')):
                qualified = [int(s.strip()) for s in str(row['qualified_subjects']).split(';') if s.strip()]
            
            data = {
                'faculty_id': faculty_id,
                'faculty_name': faculty_name,
                'min_load': float(row.get('min_load', 0)),
                'max_load': float(row.get('max_load', 99)),
                'max_subjects': int(row.get('max_subjects', 99)),
                'preferred_subjects': preferred,
                'qualified_subjects': qualified
            }
            
            self.faculty_by_name[faculty_name] = data
            self.faculty_by_id[faculty_id] = data
    
    def _load_subjects(self):
        """Load subjects.csv"""
        path = os.path.join(self.reference_folder, "subjects.csv")
        if not os.path.exists(path):
            print(f"  ⚠ Warning: {path} not found")
            return
        
        df = pd.read_csv(path)
        for _, row in df.iterrows():
            subject_id = row['subject_id']
            subject_name = str(row['subject_name']).strip()
            normalized_name = normalize_subject_name(subject_name)
            
            linked_id = None
            if pd.notna(row.get('linked_subject_id')):
                linked_id = int(row['linked_subject_id'])
            
            data = {
                'subject_id': subject_id,
                'subject_name': subject_name,
                'normalized_name': normalized_name,
                'lecture_units': float(row.get('lecture_units', 0)),
                'lab_units': float(row.get('lab_units', 0)),
                'linked_subject_id': linked_id,
                'max_enrollment': int(row.get('max_enrollment', 60)),
                'room_type_id': row.get('room_type_id', None)
            }
            
            self.subjects_by_name[normalized_name] = data
            self.subjects_by_id[subject_id] = data
    
    def _load_rooms(self):
        """Load rooms.csv"""
        path = os.path.join(self.reference_folder, "rooms.csv")
        if not os.path.exists(path):
            print(f"  ⚠ Warning: {path} not found")
            return
        
        df = pd.read_csv(path)
        for _, row in df.iterrows():
            room_id = row['room_id']
            room_name = str(row['room_name']).strip()
            
            data = {
                'room_id': room_id,
                'room_name': room_name,
                'capacity': int(row.get('capacity', 40))
            }
            
            self.rooms_by_name[room_name] = data
            self.rooms_by_id[room_id] = data
    
    def _load_batches(self):
        """Load student_batches.csv"""
        path = os.path.join(self.reference_folder, "student_batches.csv")
        if not os.path.exists(path):
            print(f"  ⚠ Warning: {path} not found")
            return
        
        df = pd.read_csv(path)
        for _, row in df.iterrows():
            batch_id = row['batch_id']
            batch_name = str(row['batch_name']).strip()
            
            data = {
                'batch_id': batch_id,
                'batch_name': batch_name,
                'population': int(row.get('population', 0))
            }
            
            self.batches_by_name[batch_name] = data
            self.batches_by_id[batch_id] = data
    
    def _load_banned_times(self):
        """Load banned_times.csv if it exists."""
        path = os.path.join(self.reference_folder, "banned_times.csv")
        if not os.path.exists(path):
            return
        
        df = pd.read_csv(path)
        for _, row in df.iterrows():
            # Handle different column name possibilities
            faculty_name = row.get('faculty_name', '')
            if pd.isna(faculty_name):
                faculty_name = ''
            
            self.banned_times.append({
                'faculty_name': str(faculty_name).strip(),
                'day': str(row.get('day', '')).strip().upper(),
                'start_time': str(row.get('start_time', '00:00')),
                'end_time': str(row.get('end_time', '00:00')),
                'start_minutes': time_to_minutes(row.get('start_time')),
                'end_minutes': time_to_minutes(row.get('end_time'))
            })


class ScheduleLoader:
    """Loads and normalizes schedule data, mapping names to IDs."""
    
    def __init__(self, reference_data: ReferenceData):
        self.ref = reference_data
        self.schedule_rows = []
        self.schedule_rows_unmerged = []  # Keep original unmerged data
        self.unmapped_subjects = set()
        self.data_conflicts = []  # Track conflicts during merge
    
    def load(self, schedule_path="INPUT/schedule.csv"):
        """Load schedule and map to reference data."""
        if not os.path.exists(schedule_path):
            print(f"  ✗ Error: {schedule_path} not found")
            return []
        
        # Read CSV
        df = pd.read_csv(schedule_path)
        
        print(f"  ✓ Read {len(df)} rows from {schedule_path}")
        
        # Process each row
        unmerged_rows = []
        for idx, row in df.iterrows():
            mapped_row = self._map_row(row, idx)
            if mapped_row:
                unmerged_rows.append(mapped_row)
        
        self.schedule_rows_unmerged = unmerged_rows
        
        print(f"  ✓ Mapped {len(unmerged_rows)} valid meetings (before merge)")
        
        # Unify meetings that share same subject, day, and time
        self.schedule_rows = self._unify_meetings(unmerged_rows)
        
        print(f"  ✓ Unified into {len(self.schedule_rows)} unique meetings")
        if self.data_conflicts:
            print(f"  ⚠ {len(self.data_conflicts)} data conflicts detected during merge")
        print(f"  ⚠ {len(self.unmapped_subjects)} unmapped subject types")
        
        return self.schedule_rows
    
    def _map_row(self, row, idx):
        """Map a single schedule row to reference IDs."""
        
        # Get and normalize subject_name -> subject
        event_name = row.get('subject_name', '')
        if pd.isna(event_name) or not str(event_name).strip():
            return None
        
        normalized_event = normalize_subject_name(event_name)
        
        # Map to subject
        subject_data = self.ref.subjects_by_name.get(normalized_event)
        if not subject_data:
            self.unmapped_subjects.add(str(event_name).strip())
            subject_id = None
            subject_name = str(event_name).strip()
        else:
            subject_id = subject_data['subject_id']
            subject_name = subject_data['subject_name']
        
        # Map faculty_name -> faculty_id (skip if empty)
        faculty_name = row.get('faculty_name', '')
        faculty_id = None
        if pd.notna(faculty_name) and str(faculty_name).strip():
            faculty_name = str(faculty_name).strip()
            faculty_data = self.ref.faculty_by_name.get(faculty_name)
            if faculty_data:
                faculty_id = faculty_data['faculty_id']
        else:
            faculty_name = None
        
        # Map room_name -> room_id (skip if empty)
        room_name = row.get('room_name', '')
        room_id = None
        room_capacity = None
        if pd.notna(room_name) and str(room_name).strip():
            room_name = str(room_name).strip()
            room_data = self.ref.rooms_by_name.get(room_name)
            if room_data:
                room_id = room_data['room_id']
                room_capacity = room_data['capacity']
        else:
            room_name = None
        
        # Map batch_name/batch_names -> batch_id (skip if empty)
        # Support both 'batch_name' (single) and 'batch_names' (potentially multiple, semicolon-separated)
        # e.g., "BSCS 4 (14);BSIT 4-B (11)" -> ["BSCS 4", "BSIT 4-B"]
        batch_name = row.get('batch_names', row.get('batch_name', ''))
        batch_ids = []
        batch_names = []
        batch_population = 0
        
        if pd.notna(batch_name) and str(batch_name).strip():
            batch_name_str = str(batch_name).strip()
            # Split by semicolon to handle multiple batches
            batch_parts = [b.strip() for b in batch_name_str.split(';') if b.strip()]
            
            for batch_part in batch_parts:
                # Extract just the batch name (remove student count in parentheses)
                # e.g., "BSIT 1-A (35)" -> "BSIT 1-A"
                if '(' in batch_part:
                    batch_name_clean = batch_part.split('(')[0].strip()
                else:
                    batch_name_clean = batch_part
                
                batch_data = self.ref.batches_by_name.get(batch_name_clean)
                if batch_data:
                    batch_ids.append(batch_data['batch_id'])
                    batch_names.append(batch_name_clean)
                    batch_population += batch_data['population']
        
        # For backwards compatibility, use first batch as primary
        batch_id = batch_ids[0] if batch_ids else None
        batch_name = batch_names[0] if batch_names else None
        
        # Parse times
        start_time = str(row.get('start_time', '00:00'))
        end_time = str(row.get('end_time', '00:00'))
        start_minutes = time_to_minutes(start_time)
        end_minutes = time_to_minutes(end_time)
        duration_minutes = end_minutes - start_minutes
        
        # Normalize day - support both 'day' and 'day_of_week' columns
        day = str(row.get('day_of_week', row.get('day', ''))).strip().upper()
        
        # Get meeting_id from CSV (if present)
        meeting_id = row.get('meeting_id', idx + 1)  # Default to 1-based row index
        if pd.isna(meeting_id):
            meeting_id = idx + 1
        
        return {
            'row_index': idx,
            'meeting_id': meeting_id,
            
            # Subject info
            'subject_id': subject_id,
            'subject_name': subject_name,
            'original_event_name': str(event_name).strip(),
            
            # Faculty info
            'faculty_id': faculty_id,
            'faculty_name': faculty_name,
            
            # Room info
            'room_id': room_id,
            'room_name': room_name,
            'room_capacity': room_capacity,
            
            # Batch info
            'batch_id': batch_id,
            'batch_name': batch_name,
            'batch_population': batch_population,
            'all_batch_ids': batch_ids if len(batch_ids) > 1 else None,
            'all_batch_names': batch_names if len(batch_names) > 1 else None,
            
            # Time info
            'day': day,
            'start_time': start_time,
            'end_time': end_time,
            'start_minutes': start_minutes,
            'end_minutes': end_minutes,
            'duration_minutes': duration_minutes
        }
    
    def _unify_meetings(self, unmerged_rows):
        """
        Unify meetings that share the same (subject, day, time).
        Multiple rows representing the same physical meeting are merged.
        """
        from collections import defaultdict
        
        # Group by meeting key: (subject_name, day, start_time, end_time)
        meeting_groups = defaultdict(list)
        
        for row in unmerged_rows:
            key = (
                row['subject_name'],
                row['day'],
                row['start_time'],
                row['end_time']
            )
            meeting_groups[key].append(row)
        
        unified_meetings = []
        
        for meeting_key, rows in meeting_groups.items():
            if len(rows) == 1:
                # Single row, no merging needed
                unified_meetings.append(rows[0])
            else:
                # Multiple rows - merge them
                unified = self._merge_meeting_rows(rows, meeting_key)
                unified_meetings.append(unified)
        
        return unified_meetings
    
    def _merge_meeting_rows(self, rows, meeting_key):
        """
        Merge multiple rows representing the same meeting.
        Detects conflicts when multiple different faculty or rooms are assigned.
        """
        subject_name, day, start_time, end_time = meeting_key
        
        # Collect all non-null values
        meeting_ids = []
        faculty_ids = set()
        faculty_names = set()
        batch_ids = set()
        batch_names = set()
        room_ids = set()
        room_names = set()
        room_capacities = set()
        
        subject_id = None
        original_event_name = None
        
        for row in rows:
            meeting_ids.append(row.get('meeting_id'))
            
            if row['subject_id'] is not None:
                subject_id = row['subject_id']
            if row['original_event_name']:
                original_event_name = row['original_event_name']
            
            if row['faculty_id'] is not None:
                faculty_ids.add(row['faculty_id'])
                faculty_names.add(row['faculty_name'])
            
            if row['batch_id'] is not None:
                batch_ids.add(row['batch_id'])
                batch_names.add(row['batch_name'])
            
            if row['room_id'] is not None:
                room_ids.add(row['room_id'])
                room_names.add(row['room_name'])
                if row['room_capacity'] is not None:
                    room_capacities.add(row['room_capacity'])
        
        # Check for conflicts
        if len(faculty_ids) > 1:
            self.data_conflicts.append({
                'type': 'Multiple Faculty Conflict',
                'meeting': f"{subject_name} on {day} {start_time}-{end_time}",
                'row_ids': meeting_ids,
                'faculty': list(faculty_names),
                'details': f"Same meeting assigned to {len(faculty_ids)} different faculty: {', '.join(faculty_names)}"
            })
        
        if len(room_ids) > 1:
            self.data_conflicts.append({
                'type': 'Multiple Room Conflict',
                'meeting': f"{subject_name} on {day} {start_time}-{end_time}",
                'row_ids': meeting_ids,
                'rooms': list(room_names),
                'details': f"Same meeting assigned to {len(room_ids)} different rooms: {', '.join(room_names)}"
            })
        
        # Create unified meeting (use first non-null value for single-valued fields)
        # For multi-valued fields (batches), keep all
        return {
            'row_index': rows[0]['row_index'],
            'meeting_id': '/'.join(str(mid) for mid in sorted(meeting_ids)),  # Combined ID
            'merged_from_rows': meeting_ids,
            
            # Subject info
            'subject_id': subject_id,
            'subject_name': subject_name,
            'original_event_name': original_event_name or subject_name,
            
            # Faculty info (take first, log if conflict)
            'faculty_id': list(faculty_ids)[0] if faculty_ids else None,
            'faculty_name': list(faculty_names)[0] if faculty_names else None,
            'all_faculty_ids': list(faculty_ids),
            'all_faculty_names': list(faculty_names),
            
            # Room info (take first, log if conflict)
            'room_id': list(room_ids)[0] if room_ids else None,
            'room_name': list(room_names)[0] if room_names else None,
            'room_capacity': list(room_capacities)[0] if room_capacities else None,
            'all_room_ids': list(room_ids),
            'all_room_names': list(room_names),
            
            # Batch info (keep all - this is normal)
            'batch_id': list(batch_ids)[0] if batch_ids else None,  # For compatibility
            'batch_name': list(batch_names)[0] if batch_names else None,  # For compatibility
            'batch_population': sum(self.ref.batches_by_id.get(bid, {}).get('population', 0) for bid in batch_ids),
            'all_batch_ids': list(batch_ids),
            'all_batch_names': list(batch_names),
            
            # Time info
            'day': day,
            'start_time': start_time,
            'end_time': end_time,
            'start_minutes': rows[0]['start_minutes'],
            'end_minutes': rows[0]['end_minutes'],
            'duration_minutes': rows[0]['duration_minutes']
        }
    
    def get_unmapped_subjects(self):
        """Return set of event names that couldn't be mapped."""
        return self.unmapped_subjects
    
    def get_data_conflicts(self):
        """Return list of data conflicts detected during merge."""
        return self.data_conflicts
    
    def get_unmerged_rows(self):
        """Return original unmerged schedule rows."""
        return self.schedule_rows_unmerged
