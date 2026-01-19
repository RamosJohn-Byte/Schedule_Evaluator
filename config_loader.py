"""
Configuration Loader Module
Loads config.json and provides constants for the evaluator.
"""

import json
import os


def load_config(config_path="REFERENCE/config.json"):
    """Load configuration from config.json file."""
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        print(f"  ✓ Loaded config from {config_path}")
        return config
    except FileNotFoundError:
        print(f"  ⚠ Warning: {config_path} not found. Using default values.")
        return get_default_config()


def get_default_config():
    """Return default configuration values."""
    return {
        "PENALTY_EXPONENT": 1.0,
        "MIN_SECTION_STUDENTS": 10,
        "MAX_CONTINUOUS_CLASS_HOURS": 3,
        "MIN_CONTINUOUS_CLASS_HOURS": 1.5,
        "MAX_GAP_HOURS": 0.5,
        "MIN_GAP_HOURS": 0.5,
        "FRIDAY_END_MINUTES": 750,
        "LECTURE_UNIT_TO_HOURS": 1,
        "LAB_UNIT_TO_HOURS": 3,
        "ConstraintPenalties": get_default_penalties()
    }


def get_default_penalties():
    """Return default penalty values."""
    return {
        "FACULTY_OVERLOAD_PER_LOAD": 1,
        "FACULTY_UNDERFILL_PER_LOAD": 1,
        "ROOM_OVERCAPACITY_PER_STUDENT": 1,
        "SECTION_OVERFILL_PER_STUDENT": 1,
        "SECTION_UNDERFILL_PER_STUDENT": 1,
        "EXCESS_CONTINUOUS_CLASS_PER_MINUTE": 0,
        "UNDER_MINIMUM_BLOCK_PER_MINUTE": 0,
        "EXCESS_GAP_PER_MINUTE": 0,
        "NON_PREFERRED_SUBJECT_PER_SECTION": 1,
        "FRIDAY_AFTER_1230_PER_MINUTE": 1,
        "EXCESS_SUBJECTS_PER_SUBJECT": 1
    }


class Config:
    """Configuration singleton with all settings."""
    
    _instance = None
    
    def __new__(cls, config_path="REFERENCE/config.json"):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize(config_path)
        return cls._instance
    
    def _initialize(self, config_path):
        """Initialize configuration values."""
        raw_config = load_config(config_path)
        
        # Penalty exponent
        self.PENALTY_EXPONENT = raw_config.get("PENALTY_EXPONENT", 1.0)
        
        # Thresholds
        self.MIN_SECTION_STUDENTS = raw_config.get("MIN_SECTION_STUDENTS", 10)
        self.MAX_SECTION_STUDENTS = raw_config.get("MAX_SECTION_STUDENTS", 35)
        self.MAX_CONTINUOUS_CLASS_HOURS = raw_config.get("MAX_CONTINUOUS_CLASS_HOURS", 3)
        self.MIN_CONTINUOUS_CLASS_HOURS = raw_config.get("MIN_CONTINUOUS_CLASS_HOURS", 1.5)
        self.MAX_GAP_HOURS = raw_config.get("MAX_GAP_HOURS", 0.5)
        self.MIN_GAP_HOURS = raw_config.get("MIN_GAP_HOURS", 0.5)
        self.FRIDAY_END_MINUTES = raw_config.get("FRIDAY_END_MINUTES", 750)
        
        # Convert to minutes
        self.MAX_CONTINUOUS_CLASS_MINUTES = int(self.MAX_CONTINUOUS_CLASS_HOURS * 60)
        self.MIN_CONTINUOUS_CLASS_MINUTES = int(self.MIN_CONTINUOUS_CLASS_HOURS * 60)
        self.MAX_GAP_MINUTES = int(self.MAX_GAP_HOURS * 60)
        self.MIN_GAP_MINUTES = int(self.MIN_GAP_HOURS * 60)
        
        # Unit conversions
        self.LECTURE_UNIT_TO_HOURS = raw_config.get("LECTURE_UNIT_TO_HOURS", 1)
        self.LAB_UNIT_TO_HOURS = raw_config.get("LAB_UNIT_TO_HOURS", 3)
        
        # Load to hours factor (1 load unit = 3 hours)
        self.LOAD_TO_MINUTES = 180  # 3 hours * 60 minutes
        
        # Excess gap threshold (use MAX_GAP_HOURS from config)
        self.EXCESS_GAP_HOURS = raw_config.get("MAX_GAP_HOURS", 0.5)
        self.EXCESS_GAP_MINUTES = int(self.EXCESS_GAP_HOURS * 60)
        
        # Friday late threshold
        self.FRIDAY_LATE_MINUTES = raw_config.get("FRIDAY_END_MINUTES", 750)  # 12:30 PM default
        
        # Max subjects per faculty
        self.MAX_SUBJECTS_PER_FACULTY = raw_config.get("MAX_SUBJECTS_PER_FACULTY", 5)
        
        # Penalty weights
        penalties = raw_config.get("ConstraintPenalties", get_default_penalties())
        # Faculty load penalties are per load unit (not per minute)
        self.FACULTY_OVERLOAD_PER_LOAD = penalties.get("FACULTY_OVERLOAD_PER_LOAD", penalties.get("FACULTY_OVERLOAD_PER_MINUTE", 1))
        self.FACULTY_UNDERFILL_PER_LOAD = penalties.get("FACULTY_UNDERFILL_PER_LOAD", penalties.get("FACULTY_UNDERFILL_PER_MINUTE", 1))
        self.SECTION_OVERFILL_PER_STUDENT = penalties.get("SECTION_OVERFILL_PER_STUDENT", 1)
        self.SECTION_UNDERFILL_PER_STUDENT = penalties.get("SECTION_UNDERFILL_PER_STUDENT", 1)
        self.MIN_CONTINUOUS_PENALTY_PER_MINUTE = penalties.get("UNDER_MINIMUM_BLOCK_PER_MINUTE", 0)
        self.EXCESS_GAP_PENALTY_PER_MINUTE = penalties.get("EXCESS_GAP_PER_MINUTE", 0)
        self.NON_PREFERRED_SUBJECT_PENALTY = penalties.get("NON_PREFERRED_SUBJECT_PER_SECTION", 1)
        self.FRIDAY_LATE_PENALTY_PER_MINUTE = penalties.get("FRIDAY_AFTER_1230_PER_MINUTE", 1)
        self.EXCESS_SUBJECTS_PENALTY_PER_SUBJECT = penalties.get("EXCESS_SUBJECTS_PER_SUBJECT", 1)
        self.EXTERNAL_MEETING_CONFLICT_PENALTY_PER_MINUTE = penalties.get("EXTERNAL_MEETING_CONFLICT_PER_MINUTE", 1)
        
        # Day order for sorting
        self.DAY_ORDER = {
            "MONDAY": 0, 
            "TUESDAY": 1, 
            "WEDNESDAY": 2, 
            "THURSDAY": 3, 
            "FRIDAY": 4,
            "SATURDAY": 5,
            "SUNDAY": 6
        }
    
    def apply_penalty(self, raw_count, penalty_weight):
        """
        Apply penalty exponent and weight.
        Formula: (raw_count ^ PENALTY_EXPONENT) * penalty_weight
        """
        if raw_count <= 0:
            return 0
        scaled = raw_count ** self.PENALTY_EXPONENT
        return scaled * penalty_weight
