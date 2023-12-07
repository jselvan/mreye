from pathlib import Path
import random

def generate_sequence(stimulus_list=None):
    BASELINE = {'name': 'baseline', 'n_triggers': 14}
    PRE_TRIGGERS = {'name': 'pre_triggers', 'n_triggers': 31}
    if stimulus_list is None:
        stimulus_list = list(Path('stimuli').glob('*.avi')) + [None]*3
        random.shuffle(stimulus_list)
    sequence = [PRE_TRIGGERS] 
    # sequence = []
    for stimulus in stimulus_list:
        sequence.append(BASELINE)
        TASK = {
            'name': 'task', 'n_triggers': 11, 
            'stimuli': [
                {"type": "circle", "x": 0, "y": 0, "c": (0,0,255), "r": 0.25, 'z':1}, 
            ], 
            'fixation': {'x': 0, 'y': 0, 'radius': 5, 'proportion': 0.8}
        }
        if stimulus is not None:
            TASK['stimuli'].append({"type":"video", 'path': str(stimulus), "x": 0, "y": 0, 'z':0, "loop": True})
        sequence.append(TASK)
    sequence.append(BASELINE)
    return sequence

if __name__ == "__main__":
    import sys
    import json

    output_path = Path(sys.argv[1])
    if len(sys.argv) > 2:
        with open(sys.argv[2], 'r') as f:
            stimulus_order = [stimulus if stimulus else None for stimulus in f.read().split('\n')]
    else:
        stimulus_order = None
    sequence = generate_sequence(stimulus_order)
    json.dump(sequence, open(output_path, 'w'), indent=4)