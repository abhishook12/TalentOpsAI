import sys
try:
    print('\n--- CHECK 3: Dashboard API Output ---')
    sys.path.append('C:/TalentOpsAI/backend')
    from app.olap_sidecar import MemoryOLAPSidecar
    sidecar = MemoryOLAPSidecar()
    sidecar.refresh(20)
    metrics = sidecar.get_data_quality()
    for m in metrics:
        if m.get('metric') == 'Unknown State Recruiters':
            print(f"Dashboard will display: {m}")
except Exception as e:
    print('Error:', e)
