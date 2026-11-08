"""Report only measured trials; never substitute synthetic accuracy."""
import csv
import json
from pathlib import Path
from statistics import mean

def summarize(rows):
    positive = [r for r in rows if r['expected']]
    negative = [r for r in rows if not r['expected']]
    times = [float(r['seconds']) for r in positive if r['seconds'] and r['actual'] == r['expected']]
    return {
        'trials': len(rows),
        'character_accuracy': sum(r['actual'] == r['expected'] for r in positive)/len(positive) if positive else None,
        'contact_detection_accuracy': sum(r['contact_expected'] == r['contact_actual'] for r in rows)/len(rows) if rows else None,
        'false_activation_rate_per_negative_trial': sum(bool(r['actual']) for r in negative)/len(negative) if negative else None,
        'mean_start_to_correct_output_seconds': mean(times) if times else None,
    }

def report(source):
    source = Path(source)
    with source.open(encoding='utf-8', newline='') as stream:
        reader = csv.DictReader(stream)
        required = {'expected','actual','seconds','contact_expected','contact_actual','mode','condition'}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError('Invalid trials CSV headers')
        rows = list(reader)
    result = summarize(rows)
    result['timing_note'] = 'Measured from Start trial button, includes user movement; not algorithm-only latency.'
    result['by_mode_and_condition'] = {
        f'{mode} / {condition}': summarize([r for r in rows if r['mode']==mode and r['condition']==condition])
        for mode, condition in sorted({(r['mode'],r['condition']) for r in rows})}
    labels = ['<NONE>'] + list('ABCDEFGHIJKLMNOPQRSTUVWXYZ') + ['<OTHER>']
    matrix = {a:{b:0 for b in labels} for a in labels}
    def label(s):
        return s if s in labels else ('<NONE>' if not s else '<OTHER>')
    for row in rows:
        matrix[label(row['expected'])][label(row['actual'])] += 1
    target = source.with_name('confusion_matrix.csv')
    with target.open('w', encoding='utf-8', newline='') as stream:
        writer = csv.writer(stream)
        writer.writerow(['expected / actual']+labels)
        for a in labels:
            writer.writerow([a]+[matrix[a][b] for b in labels])
    summary = source.with_name('evaluation.json')
    summary.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    return f'{summary}\n{target}'
