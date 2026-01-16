"""Debug script to check gap detection for BSIT 1-B"""
import sys
sys.path.insert(0, r'c:\Users\John Ramos\Desktop\Schedule Evaluator')

from data_loader import ReferenceData, ScheduleLoader
from collections import defaultdict

# Load data
ref = ReferenceData('REFERENCE')
loader = ScheduleLoader(ref)
schedule_rows = loader.load('INPUT/schedule.csv')

# Get BSIT 1-B (batch_id = 3)
batch_id = 3
batch_meetings = []

print("Collecting meetings for BSIT 1-B (batch_id=3)...")
print("-" * 80)

for row in schedule_rows:
    # Check if this meeting involves BSIT 1-B
    if row.get('all_batch_ids'):
        if batch_id in row['all_batch_ids']:
            batch_meetings.append(row)
            print(f"Added (merged): Row {row.get('meeting_id')} | {row['day']} {row['start_time']}-{row['end_time']} | {row['subject_name']} | all_batch_ids={row['all_batch_ids']}")
    elif row.get('batch_id') == batch_id:
        batch_meetings.append(row)
        print(f"Added (singular): Row {row.get('meeting_id')} | {row['day']} {row['start_time']}-{row['end_time']} | {row['subject_name']} | batch_id={row['batch_id']}")

print(f"\nTotal meetings for BSIT 1-B: {len(batch_meetings)}")

# Group by day
by_day = defaultdict(list)
for m in batch_meetings:
    by_day[m['day']].append(m)

print("\n" + "=" * 80)
print("TUESDAY SCHEDULE (sorted by time):")
print("=" * 80)

if 'TUESDAY' in by_day:
    tuesday = sorted(by_day['TUESDAY'], key=lambda x: x['start_minutes'])
    for i, m in enumerate(tuesday):
        print(f"{i}. Row {m.get('meeting_id'):4} | {m['start_time']}-{m['end_time']} | {m['subject_name']:20} | start_min={m['start_minutes']}, end_min={m['end_minutes']}")
    
    print("\n" + "=" * 80)
    print("GAPS:")
    print("=" * 80)
    
    for i in range(len(tuesday) - 1):
        current_end = tuesday[i]['end_minutes']
        next_start = tuesday[i + 1]['start_minutes']
        gap = next_start - current_end
        
        print(f"Between meetings {i} and {i+1}:")
        print(f"  Meeting {i} ends at: {tuesday[i]['end_time']} ({current_end} min)")
        print(f"  Meeting {i+1} starts at: {tuesday[i+1]['start_time']} ({next_start} min)")
        print(f"  Gap: {gap} minutes")
        print(f"  Exceeds 30 min threshold? {gap > 30}")
        print()
