import numpy as np
import pandas as pd
import sys

df=pd.read_csv(sys.argv[1])
df.columns=["type", "Thread", "type", "Start", "Finish", "Duration", "Depth", "Function"]
df=df[["Thread", "Function", "Start", "Finish", "Duration", "Depth"]]
df.to_csv(sys.argv[2])
