import sys, os, ctypes
from app.database import SessionLocal
from sqlalchemy import text

# PLATFORM HARD LIMITS (Free Tier / Budget Optimization per Rule #4 & Rule #8)
SUPABASE_MAX_STORAGE_MB = 500.0          # 500 MB max storage
SUPABASE_MAX_EGRESS_MB = 5120.0          # 5 GB (5,120 MB) monthly bandwidth
GEMINI_MAX_RPM = 15.0                    # 15 requests per minute per key
GEMINI_MAX_RPD = 1000.0                  # 1,000 requests per day per key
SERVER_MAX_RAM_MB = 512.0                # 512 MB memory limit (Render/Free VM)

# 70% ALARM THRESHOLD MARKERS (Rule #8)
THRESHOLD_STORAGE_MB = SUPABASE_MAX_STORAGE_MB * 0.70    # 350.0 MB (Note: Rule #7 hard cap is 400 MB)
THRESHOLD_EGRESS_MB = SUPABASE_MAX_EGRESS_MB * 0.70      # 3,584.0 MB (3.5 GB)
THRESHOLD_RPM = GEMINI_MAX_RPM * 0.70                    # 10.5 RPM
THRESHOLD_RPD = GEMINI_MAX_RPD * 0.70                    # 700.0 RPD
THRESHOLD_RAM_MB = SERVER_MAX_RAM_MB * 0.70              # 358.4 MB

def get_process_memory_mb():
    try:
        if os.name == 'nt':
            class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
                _fields_ = [
                    ("cb", ctypes.c_ulong),
                    ("PageFaultCount", ctypes.c_ulong),
                    ("PeakWorkingSetSize", ctypes.c_size_t),
                    ("WorkingSetSize", ctypes.c_size_t),
                    ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                    ("PagefileUsage", ctypes.c_size_t),
                    ("PeakPagefileUsage", ctypes.c_size_t),
                ]
            counters = PROCESS_MEMORY_COUNTERS()
            counters.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS)
            handle = ctypes.windll.kernel32.GetCurrentProcess()
            if ctypes.windll.psapi.GetProcessMemoryInfo(handle, ctypes.byref(counters), counters.cb):
                return counters.WorkingSetSize / (1024.0 * 1024.0)
        return 0.0
    except Exception:
        return 0.0

class PlatformSafetyAlarm:
    @staticmethod
    def check_and_alert_all():
        """
        Audits current resource consumption against the 70% platform thresholds.
        If any limit hits >= 70%, triggers an urgent alarm and returns alert details.
        """
        alarms_triggered = []
        status_report = {}

        # 1. Check Database Storage Size
        try:
            db = SessionLocal()
            db_size_mb = float(db.execute(text("SELECT pg_database_size(current_database()) / 1048576.0")).scalar() or 0.0)
            db.close()
            status_report['database_size_mb'] = round(db_size_mb, 2)
            status_report['database_size_pct'] = round((db_size_mb / float(SUPABASE_MAX_STORAGE_MB)) * 100, 1)

            if db_size_mb >= THRESHOLD_STORAGE_MB:
                alarm_msg = f"🚨 [ALARM - DB STORAGE] Database size is {db_size_mb:.2f} MB ({status_report['database_size_pct']}% of 500 MB cap)! Has crossed the 70% threshold ({THRESHOLD_STORAGE_MB:.1f} MB)."
                alarms_triggered.append(alarm_msg)
                print(f"\n{alarm_msg}\n")
        except Exception as e:
            status_report['database_error'] = str(e)

        # 2. Check Local Server Memory Consumption
        try:
            mem_mb = get_process_memory_mb()
            status_report['server_ram_mb'] = round(mem_mb, 2)
            status_report['server_ram_pct'] = round((mem_mb / SERVER_MAX_RAM_MB) * 100, 1)

            if mem_mb >= THRESHOLD_RAM_MB:
                alarm_msg = f"🚨 [ALARM - SERVER RAM] Process memory is {mem_mb:.2f} MB ({status_report['server_ram_pct']}% of 512 MB cap)! Has crossed the 70% threshold ({THRESHOLD_RAM_MB:.1f} MB)."
                alarms_triggered.append(alarm_msg)
                print(f"\n{alarm_msg}\n")
        except Exception as e:
            status_report['memory_error'] = str(e)

        status_report['alarms_triggered'] = alarms_triggered
        status_report['is_alarm_active'] = len(alarms_triggered) > 0
        return status_report

if __name__ == '__main__':
    report = PlatformSafetyAlarm.check_and_alert_all()
    print("=== PLATFORM RESOURCE 70% THRESHOLD AUDIT ===")
    for k, v in report.items():
        print(f"  {k}: {v}")
