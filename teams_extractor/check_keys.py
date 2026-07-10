from google import genai

with open('api_keys.txt') as f:
    keys = [line.strip() for line in f if line.strip()]

print(f'=== DIAGNOSING ALL {len(keys)} KEYS ===')
working = []
minute_ratelimit = []
daily_ratelimit = []
other_errors = []

for idx, k in enumerate(keys):
    try:
        client = genai.Client(api_key=k)
        resp = client.models.generate_content(model='gemini-2.0-flash', contents=['hi'])
        print(f'Key {idx+1}: OK')
        working.append(idx + 1)
    except Exception as e:
        err = str(e)
        if 'PerDay' in err or 'GenerateRequestsPerDay' in err:
            daily_ratelimit.append(idx + 1)
            print(f'Key {idx+1}: DAILY QUOTA EXHAUSTED')
        elif 'PerMinute' in err or 'GenerateRequestsPerMinute' in err or 'retry in' in err:
            minute_ratelimit.append(idx + 1)
            print(f'Key {idx+1}: MINUTE RATE LIMIT')
        else:
            other_errors.append(idx + 1)
            print(f'Key {idx+1}: ERROR {type(e).__name__} - {err[:60]}...')

print(f'\n=== DIAGNOSTIC SUMMARY ===')
print(f'Total Keys Tested: {len(keys)}')
print(f'Working Immediately: {len(working)} keys ({working})')
print(f'Minute Rate Limit (Recovers in <60s): {len(minute_ratelimit)} keys ({minute_ratelimit})')
print(f'Daily Quota Exhausted: {len(daily_ratelimit)} keys ({daily_ratelimit})')
print(f'Other Errors: {len(other_errors)} keys ({other_errors})')
