"""
Section Builder Module
Identifies sections from schedule data by grouping meetings with same (subject, faculty, batches).
Also identifies lecture-lab pairs and validates them.
"""

from collections import defaultdict


class Section:
    """Represents a section of a subject with specific faculty, batches and schedule."""
    
    def __init__(self, subject_id, subject_name, section_index):
        self.subject_id = subject_id
        self.subject_name = subject_name
        self.section_index = section_index
        self.section_id = f"{subject_name}-{section_index}"
        
        # Faculty (should be exactly one)
        self.faculty_id = None
        self.faculty_name = None
        
        # Batches (can be multiple - shared class)
        self.batch_ids = set()
        self.batch_names = set()
        self.total_students = 0
        
        # Rooms used (collect all - may differ between meetings)
        self.room_ids = set()
        self.room_names = set()
        self.room_capacity = None  # From first room
        
        # For backwards compatibility
        self.room_id = None
        self.room_name = None
        
        self.meetings = []  # List of meeting rows
        self.has_conflict = False  # Track if section has data issues
    
    def set_faculty(self, faculty_id, faculty_name):
        """Set the faculty for this section."""
        self.faculty_id = faculty_id
        self.faculty_name = faculty_name
    
    def add_batch(self, batch_id, batch_name, population):
        """Add a batch to this section."""
        if batch_id not in self.batch_ids:
            self.batch_ids.add(batch_id)
            self.batch_names.add(batch_name)
            self.total_students += population
    
    def add_room(self, room_id, room_name, room_capacity):
        """Add a room to this section."""
        if room_id is not None:
            self.room_ids.add(room_id)
            self.room_names.add(room_name)
            # Set first room as primary (for backwards compatibility)
            if self.room_id is None:
                self.room_id = room_id
                self.room_name = room_name
                self.room_capacity = room_capacity
    
    def add_meeting(self, meeting):
        """Add a meeting row to this section."""
        self.meetings.append(meeting)
    
    def __repr__(self):
        return f"Section({self.section_id}, faculty={self.faculty_name}, batches={list(self.batch_names)}, students={self.total_students})"


class LectureLabPair:
    """Represents a pairing between a lecture section and its lab section."""
    
    def __init__(self, lecture_section, lab_section):
        self.lecture_section = lecture_section
        self.lab_section = lab_section
        self.is_valid = True
        self.error = None
    
    def __repr__(self):
        status = "✓" if self.is_valid else f"✗ {self.error}"
        return f"Pair({self.lecture_section.section_id} + {self.lab_section.section_id}) [{status}]"


def build_sections(schedule_rows, reference_data):
    """
    Build sections from schedule rows.
    
    Section identification logic:
    1. Group meetings by (subject_name, faculty_id, batch_ids_tuple)
    2. Each unique combination = one section
    3. Collect all rooms used by each section's meetings
    
    Returns: List of Section objects
    """
    
    sections = []
    
    # Group meetings by (subject_id, faculty_id, batches_key)
    # batches_key is a frozenset of batch_ids for the meeting
    meeting_groups = defaultdict(list)
    
    for meeting in schedule_rows:
        if meeting['subject_id'] is None:
            continue
        
        # Get batch ids - handle both merged (all_batch_ids) and single (batch_id)
        batch_ids = meeting.get('all_batch_ids')
        if batch_ids is None:
            batch_ids = []
        if not batch_ids and meeting.get('batch_id') is not None:
            batch_ids = [meeting['batch_id']]
        
        # Skip meetings with no faculty and no batch (can't group them meaningfully)
        if meeting.get('faculty_id') is None and not batch_ids:
            continue
        
        # Get faculty_id
        faculty_id = meeting.get('faculty_id')
        
        # Create grouping key
        key = (
            meeting['subject_id'],
            faculty_id,
            frozenset(batch_ids) if batch_ids else frozenset()
        )
        
        meeting_groups[key].append(meeting)
    
    # Create sections from groups
    section_index_by_subject = defaultdict(int)
    
    for (subject_id, faculty_id, batch_ids_frozenset), meetings in meeting_groups.items():
        subject_data = reference_data.subjects_by_id.get(subject_id, {})
        subject_name = subject_data.get('subject_name', str(subject_id))
        
        section_index = section_index_by_subject[subject_id]
        section_index_by_subject[subject_id] += 1
        
        section = Section(subject_id, subject_name, section_index)
        
        # Set faculty
        if faculty_id is not None:
            faculty_data = reference_data.faculty_by_id.get(faculty_id, {})
            section.set_faculty(faculty_id, faculty_data.get('faculty_name', str(faculty_id)))
        
        # Add batches
        for batch_id in batch_ids_frozenset:
            batch_data = reference_data.batches_by_id.get(batch_id, {})
            section.add_batch(
                batch_id,
                batch_data.get('batch_name', str(batch_id)),
                batch_data.get('population', 0)
            )
        
        # Add meetings and collect rooms
        for meeting in meetings:
            section.add_meeting(meeting)
            
            # Add room from meeting
            room_id = meeting.get('room_id')
            if room_id is not None:
                section.add_room(
                    room_id,
                    meeting.get('room_name'),
                    meeting.get('room_capacity')
                )
        
        sections.append(section)
    
    print(f"  ✓ Identified {len(sections)} sections across {len(section_index_by_subject)} subjects")
    
    return sections


def find_lecture_lab_pairs(sections, reference_data):
    """
    Find and validate lecture-lab pairs based on linked_subject_id.
    
    Matching criteria:
    - Lab's linked_subject_id = Lecture's subject_id
    - Same faculty (required - if different, it's an error)
    - Same batches (required - if different batches, different sections)
    
    Returns: 
        - valid_pairs: List of LectureLabPair objects that are valid
        - error_pairs: List of LectureLabPair objects with errors (different faculty)
    """
    valid_pairs = []
    error_pairs = []
    
    # Build map of lab subject_id -> lecture subject_id
    lab_to_lecture = {}
    for subject_id, subject_data in reference_data.subjects_by_id.items():
        linked_id = subject_data.get('linked_subject_id')
        if linked_id:
            lab_to_lecture[subject_id] = linked_id
    
    # Group sections by subject_id
    sections_by_subject = defaultdict(list)
    for section in sections:
        sections_by_subject[section.subject_id].append(section)
    
    # Find pairs
    for lab_section in sections:
        if lab_section.subject_id not in lab_to_lecture:
            continue
        
        lecture_subject_id = lab_to_lecture[lab_section.subject_id]
        lecture_sections = sections_by_subject.get(lecture_subject_id, [])
        
        for lecture_section in lecture_sections:
            # Check if they have the same batches
            if lab_section.batch_ids != lecture_section.batch_ids:
                continue
            
            pair = LectureLabPair(lecture_section, lab_section)
            
            # Validate: must have same faculty
            if lab_section.faculty_id != lecture_section.faculty_id:
                pair.is_valid = False
                pair.error = f"Different faculty: Lecture={lecture_section.faculty_name}, Lab={lab_section.faculty_name}"
                error_pairs.append(pair)
            else:
                valid_pairs.append(pair)
    
    return valid_pairs, error_pairs


def get_lecture_lab_pairs(sections, reference_data):
    """
    Legacy function for backwards compatibility.
    Returns list of (lab_section, lecture_section) tuples.
    """
    valid_pairs, _ = find_lecture_lab_pairs(sections, reference_data)
    return [(pair.lab_section, pair.lecture_section) for pair in valid_pairs]
