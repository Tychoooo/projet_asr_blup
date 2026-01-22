import sys
sys.path.append("build")
sys.path.append(".")

import mini

mini.load_trace("ezv_trace_current.evt")
# mini.load_trace("trace.fxt")
# mini.load_trace("one_cpu.evt")

a = mini.get_data()
print(a.shape, a.dtype)
print(a[-2])

# a[i] = [event_id, time_ns, code, nb_params, cpu, tid, raw, p0, ..., p15]

# Count the occurrences of each code
from collections import Counter
codes = [row[2] for row in a]
code_counts = Counter(codes)
for code, count in code_counts.most_common(10):
    print(f"Code {code}: {count} occurrences")

cpus = [row[4] for row in a]
cpu_counts = Counter(cpus)
for cpu, count in cpu_counts.most_common():
    print(f"CPU {cpu}: {count} occurrences")


import pandas as pd

rows = []
last_time_per_cpu = {}

for row in a:
    code = int(row[2])
    if code != 269:
        continue

    cpu = int(row[4])
    t_ns = int(row[1])

    # If not first
    if cpu in last_time_per_cpu:
        start_ns = last_time_per_cpu[cpu]
        finish_ns = t_ns
        duration_ns = finish_ns - start_ns

        rows.append({
            "Thread": str(cpu),
            "Function": "0",
            "Start": start_ns,
            "Finish": finish_ns,
            "Duration": int(duration_ns),
            "Depth": 0,
        })

    last_time_per_cpu[cpu] = t_ns

df = pd.DataFrame(rows, columns=["Thread", "Function", "Start", "Finish", "Duration", "Depth"])


df["Thread"] = df["Thread"].astype("str")
df["Function"] = df["Function"].astype("str")
df["Start"] = df["Start"].astype("int64")
df["Finish"] = df["Finish"].astype("int64")
df["Duration"] = df["Duration"].astype("int64")
df["Depth"] = df["Depth"].astype("int64")

print(df.head())
print(df.dtypes)