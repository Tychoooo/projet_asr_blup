import pandas as pd
import io
import os
import base64
import sys
import re
import datetime
from functools import partial
import numpy as np
from bokeh.palettes import Set3 as palette
from bokeh.models import ColumnDataSource, HoverTool
from bokeh.plotting import figure
from bokeh import events

# For trace_fxt, to access the python library
sys.path.append("build")

# Converts a duration (int64) in nanoseconds to a dict. The dict contains
# sign: '' or '-'
# ns: nanoseconds [0-999]
# us: microseconds [0-999]
# ms: milliseconds [0-999]
# s:  seconds [0-59]
# m:  minutes [0-59]
# h:  hours [0-inf]
def split_duration(duration):
    d = {"sign": '', "ns":0, "us":0, "ms": 0, "s":0, "m":0, "h":0}
    if duration < 0 :
        d["sign"]='-'
    d["ns"] = abs(int(duration))
    d["us"], d["ns"] = divmod(d["ns"], 1000)
    d["ms"], d["us"] = divmod(d["us"], 1000)
    d["s"], d["ms"] = divmod(d["ms"], 1000)
    d["m"], d["s"] = divmod(d["s"], 60)
    d["h"], d["m"] = divmod(d["m"], 3600)
    return d

def pretty_duration(ns):
    d=split_duration(ns)
    if d["h"] > 0:
        return '%s%dh %dm %ds %dms %dus %dns' % (d["sign"], d["h"], d["m"], d["s"], d["ms"], d["us"], d["ns"])
    if d["m"] > 0:
        return '%s%dm %ds %dms %dus %dns' % (d["sign"], d["m"], d["s"], d["ms"], d["us"], d["ns"])
    if d["s"] > 0:
        return '%s%ds %dms %dus %dns' % (d["sign"], d["s"], d["ms"], d["us"], d["ns"])
    if d["ms"] > 0:
        return '%s%dms %dus %dns' % (d["sign"], d["ms"], d["us"], d["ns"])
    if d["us"] > 0:
        return '%s%dus %dns' % (d["sign"], d["us"], d["ns"])
    else:
        return '%s%dns' % (d["sign"], d["ns"])

def pandas_timedelta_to_ns(td):
    return td/np.timedelta64(1, 'ns')

# calls pretty_duration with a pandas timedelta64
def pretty_duration_pandas(duration):
    return pretty_duration(pandas_timedelta_to_ns(duration))

def atoi(text):
    return int(text) if text.isdigit() else text

# Sort text that contains integer
def natural_keys(text):
    # by default sorted(list) will generate:
    # P0T0
    # P1T0
    # P10T0
    # ...
    # P2T0

    # This function makes sure that P2 comes before P10:
    # P0T0
    # P1T0
    # P2T0
    # ...
    # P9T0
    # P10T0    
    
    return [ atoi(c) for c in re.split(r'(\d+)', text) ]


def compute_depth(df):
    if(max(df["Depth"])>0):
        return df
    t1=datetime.datetime.now()

    threads=sorted(df["Thread"].unique())

    sequences_depth=[float("nan")] * len(df)

    for thread in threads:
        filtered_df=df.loc[df["Thread"]==thread]
        stack = []

        df_indices, start_ts, finish_ts = (
            list(filtered_df.index),
            list(filtered_df["Start"]),
            list(filtered_df["Finish"]),
        )

        stack.append((df_indices[0], start_ts[0], finish_ts[0]))

        for i in range(1, len(filtered_df)):
            curr_df_index, curr_start_ts, curr_finish_ts = (
                df_indices[i],
                start_ts[i],
                finish_ts[i],
            )

            # Search for a sequence whose finish_timestamp ends after curr_start_ts
            # This sequence is the one that called the current sequence
            i = len(stack)-1
            stack_df_index, stack_start_ts, stack_finish_ts = stack[i]
            while(i > -1 and curr_start_ts >= stack_finish_ts):
                  i -= 1
                  stack_df_index, stack_start_ts, stack_finish_ts = stack[i]
                  del stack[i+1]

            stack.append((curr_df_index, curr_start_ts, curr_finish_ts))
            sequences_depth[curr_df_index] = len(stack)

    df["Depth"] = sequences_depth
    t2=datetime.datetime.now()
    d=t2-t1
    print("Compute depth took "+str(d))
    return df

def choose_palette(functions):
    max_id=len(palette)
    min_id=3
    id=max(min_id, min(len(functions), max_id))
    return palette[id]
def read_trace_csv(filename):
    df=pd.read_csv(filename)

    # if the timestamp is a float, it's probably milliseconds. Convert to nanoseconds int values
    if(isinstance(df["Start"][0], np.float64)):
        df["Start"] = np.int64(df["Start"]*1e6)
    if(isinstance(df["Finish"][0], np.float64)):
        df["Finish"] = np.int64(df["Finish"]*1e6)
    if(isinstance(df["Duration"][0], np.float64)):
        df["Duration"] = np.int64(df["Duration"]*1e6)
    if not "Depth" in df:
        df["Depth"] = 0
        
    return df

def read_trace_otf2(trace_name):
    import otf2
    sequences=[]
    ongoing_sequences={}
    
    with otf2.reader.open(trace_name) as trace:
        for location, event in trace.events:
            if isinstance(event, otf2.events.ThreadBegin):
                s = {}
                s["Start"]=event.time
                s["Duration"]=0
                s["Finish"]=0
                s["Thread"]=location.name
                s["Function"]="main"
                s["Depth"]=0
                ongoing_sequences[location.name]=[s]
            if isinstance(event, otf2.events.Enter):
                s = {}
                s["Start"]=event.time
                s["Duration"]=0
                s["Finish"]=0
                s["Thread"]=location.name
                s["Function"]=event.region.name

                if (not location.name in ongoing_sequences) or (len(ongoing_sequences[location.name])==0):
                    ongoing_sequences[location.name]=[s]
                    s["Depth"]=0
                else:
                    s["Depth"]=ongoing_sequences[location.name][-1]["Depth"]+1
                    ongoing_sequences[location.name].append(s)
            elif isinstance(event, otf2.events.Leave) or isinstance(event, otf2.events.ThreadEnd):
                s=ongoing_sequences[location.name][-1]
                del ongoing_sequences[location.name][-1]
                s["Finish"]=event.time
                s["Duration"]=s["Finish"]-s["Start"]
                sequences.append(s)

    df=pd.DataFrame(sequences)
    empty_df=create_empty_df()
    df=pd.concat([empty_df, df]).fillna(0)

    expected_dtypes=empty_df.dtypes
    df = df.astype(expected_dtypes)

    return df

def read_trace_pallas(filename):
    import pallas_trace as pallas

    trace=pallas.open_trace(filename)
    df = create_empty_df()
    dataframes_list=[]
    for archive in trace.archives:
        for thread in archive.threads:
            for seq in thread.sequences:
                dataset = create_empty_df()
                dataset["Start"]=np.array(seq.timestamps)
                dataset["Duration"]=np.array(seq.durations)
                dataset["Finish"]=dataset["Start"]+dataset["Duration"]
                dataset["Thread"]=trace.locations[thread.id].name
                dataset["Function"]=seq.guessName(thread)
                dataframes_list.append(dataset);

    df=pd.concat(dataframes_list, axis=0, ignore_index=True)
    return df

def create_empty_df():
    df = pd.DataFrame({"Thread":pd.Series(dtype='str'),
                       "Function":pd.Series(dtype='str'),
                       "Start":pd.Series(dtype='timedelta64[ns]'),
                       "Finish":pd.Series(dtype='timedelta64[ns]'),
                       "Duration":pd.Series(dtype='int64'),
                       "Depth":pd.Series(dtype='int'),
                       "top":pd.Series(dtype='int64'),
                       "bottom":pd.Series(dtype='float64'),
                       "color":pd.Series(dtype='str')})
    return df

def update_plot_generic(df):
    threads=sorted(df["Thread"].unique(), key=natural_keys)
    functions=sorted(df["Function"].unique(), key=natural_keys)
    active_threads=threads
    df["top"]=df["Thread"].apply(threads.index)
    df["top"]=len(threads)-0.75-df["top"]
    df["bottom"]=df["top"] + 0.9
    df["color"]=df["Function"].apply(functions.index)

    df['Start'] = df["Start"].astype('timedelta64[ns]')
    df['Finish'] = df["Finish"].astype('timedelta64[ns]')
    used_palette=choose_palette(functions)
    df["color"]=df["color"].apply(lambda x: used_palette[x%len(used_palette)])
    df["Duration"]=pd.to_timedelta(df["Duration"])
    df=df.sort_values(["Start", "Finish"], ascending=[True, False])
    df=df.reset_index(drop=True)
    df=compute_depth(df)    
    df["bottom"]=df["top"] + df["Depth"]*0.1
    df["top"]=df["top"] + ((df["Depth"]+1)*0.1)
    return df, threads, active_threads, functions

def read_trace_fxt(filename):
    import mini
    mini.load_trace(filename)
    a = mini.get_data()
    # a[i] = [Thread, Function, Start_ns, Finish_ns, Duration_ns, Depth]
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
            start_ns = row[7] * 1000
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


    # df["Thread"] = df["Thread"].astype("str")
    # df["Function"] = df["Function"].astype("str")
    # df["Start"] = df["Start"].astype("int64")
    # df["Finish"] = df["Finish"].astype("int64")
    # df["Duration"] = df["Duration"].astype("int64")
    # df["Depth"] = df["Depth"].astype("int64")


    # df = create_empty_df()
    # df["Thread"]=a[:,0]
    # df["Function"]=a[:,1]
    # df["Start"]=a[:,2]
    # df["Finish"]=a[:,3]
    # df["Duration"]=a[:,4]
    # df["Depth"]=a[:,5]
    # df = df[["Thread", "Function", "Start", "Finish", "Duration", "Depth"]]
    
    return df

def read_trace(file_name):
    t1=datetime.datetime.now()
    filename, file_extension = os.path.splitext(file_name)
    if file_extension == ".csv":
        df=read_trace_csv(file_name)
        print("Header of loaded csv trace:")
        print(df.head())
    elif file_extension == ".pallas":
        df=read_trace_pallas(file_name)
    elif file_extension == ".otf2":
        df=read_trace_otf2(file_name)
    elif file_extension == ".evt":
        df=read_trace_fxt(file_name)
        print("Loaded fxt trace with "+str(len(df))+" entries")
        print("Header of loaded fxt trace:")
        print(df.head(20))
        print(type(df["Thread"][0]))
    t2=datetime.datetime.now()
    d=t2-t1 
    print("loading trace took "+str(d))
    df, threads, active_threads, functions = update_plot_generic(df)
    return df, threads, active_threads, functions

class BlupTrace:
    df=create_empty_df()
    filename=""
    threads=["P#0T#0"]
    functions=[]
    active_threads=threads
    data_source=ColumnDataSource()

    def filter_data(self):
        return self.df[self.df['Thread'].isin(self.active_threads)]

    def __init__(self, filename=None):
        if filename is not  None:
            self.df, self.threads, self.active_threads, self.functions = read_trace(filename)
        self.data_source=ColumnDataSource(self.filter_data())

    # replace the current trace with a new one
    def open_trace(self, filename):
        self.df, self.threads, self.active_threads, self.functions = read_trace(filename)
        new_data_source=ColumnDataSource(self.df)
        self.data_source.data=dict(new_data_source.data)

    def ranges_update_callback(self, event):
        print("range_update (x0="+str(event.x0)+", y0="+str(event.y0)+", x1="+str(event.x1)+", y1="+str(event.y1)+")")
        print(event)

    # Create a gantt chart
    def gantt_chart(self, gantt_width=1500, gantt_height=800):
        g = figure(width=gantt_width, height=gantt_height,
                   output_backend="webgl",
                   tools=["box_zoom",
                          "xwheel_pan",
                          "xbox_zoom",
                          "reset",
                          "undo",
                          "redo",
                          "ycrosshair"],
                   active_drag="box_zoom",
                   y_range=list(reversed(self.threads)),
                   x_axis_type="datetime")
        # When user hovers, display the callstack
        g.add_tools(HoverTool(tooltips=[("Function", "@Function"),
                                        ("Start", "@Start"),
                                        ("Stop", "@Finish"),
                                        ("Duration", "@Duration")]))
        g.hbar(y="Thread", left="Start", right="Finish",
               height=0.5, color="color", legend_field="Function", source=self.data_source)
        g.legend.click_policy="hide"

        g.on_event(events.RangesUpdate, self.ranges_update_callback)

        return g

    def create_chart(self, gantt_width=1500, gantt_height=800):
        g = figure(width=gantt_width, height=gantt_height,
                   output_backend="webgl",
                   tools=["box_zoom",
                          "xwheel_pan",
                          "xbox_zoom",
                          "reset",
                          "undo",
                          "redo",
                          "ycrosshair"],
                   active_drag="box_zoom",
                   y_range=list(reversed(self.threads)),
                   x_axis_type="datetime")
        # When user hovers, display the callstack
        g.add_tools(HoverTool(tooltips=[("Function", "@Function"),
                                        ("Start", "@Start"),
                                        ("Stop", "@Finish"),
                                        ("Duration", "@Duration")]))
        g.legend.click_policy="hide"

        g.on_event(events.RangesUpdate, self.ranges_update_callback)

        return g

    def add_gantt(self, g):
        g.hbar(y="Thread", left="Start", right="Finish",
               height=0.5, color="color", legend_field="Function", source=self.data_source, name="gantt")

    # Create a gantt chart
    def add_flame(self, g):
        g.quad(left="Start", right="Finish", top="top", bottom="bottom", color="color", legend_field="Function", source=self.data_source, name="flamegraph")


if __name__ == "__main__":

    filename = "sample_traces/mpi_ring_4_ranks.csv"

    blup_trace = BlupTrace(filename)
    print("Threads: "+str(blup_trace.threads))
    print("Functions: "+str(blup_trace.functions))



