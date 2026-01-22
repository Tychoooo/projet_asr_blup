# Blup

**Blup** is a web-based trace visualization tool.

![](doc/screenshot.png)

[![BSD-3 License](https://img.shields.io/badge/License-BSD3-yellow.svg)](https://opensource.org/license/bsd-3-clause)

**Blup** is a web-based trace visualization tool. It allows users to navigate in execution traces generated with tracing tools such as [EZTrace](https://gitlab.com/eztrace/eztrace).

## Building Blup

When running Blup for the first time, it automatically install
dependencies. All you need is `python`.

You may need to install the `python3-tk` package that may not be installed by pip.

## Running Blup locally

You can visualize traces stored on your local machine by running:
```
blup trace.otf2
```

This starts a local Blup server (on `localhost:5006`), and opens a browser that connects to
the server.


## Running Blup remotely

You can visualize traces stored on a remote machine `REMOTE` (eg. the
frontend of you cluster) by running:

```
(REMOTE)$ blup -s
2025-03-28 14:02:58,088 Starting Bokeh server version 3.6.3 (running on Tornado 6.4.2)
2025-03-28 14:02:58,089 User authentication hooks NOT provided (default user enabled)
2025-03-28 14:02:58,091 Bokeh app running at: http://localhost:5006/blup_server
2025-03-28 14:02:58,091 Starting Bokeh server with process id: 636809
[...]
```

```
(LOCAL)$ blup -c REMOTE
Connecting to REMOTE:5006
[...]
```

The `REMOTE` host name can be an ssh alias (eg. `mylogin@machine`)


## Supported trace formats

Currently, Blup supports several trace formats:

- [Pallas](https://gitlab.inria.fr/pallas/pallas) - you may need to
  use the `dev` branch of Pallas
- [OTF2](https://www.vi-hps.org/projects/score-p)
- CSV

### Reading a csv file

Blup can display csv files too. The csv file should be formatted as follows:

```
Thread,Function,Start,Finish,Duration
P#0T#0,main,23603869,29084554,5480685
P#0T#0,MPI_Barrier,23839473,24420186,580713
P#0T#0,MPI_Barrier,25177264,25206631,29367
P#1T#0,Loop_0,28779030,29181404,402374
P#1T#0,main,7557043,29081588,21524545
P#1T#0,MPI_Barrier,7747561,24399149,16651588
P#1T#0,MPI_Barrier,24810285,25215879,405594
```

`Start`, `Finish`, and `Duration` should be integer values
corresponding to nanoseconds. If these field contain float values,
Blup assumes these are milliseconds, and Blup converts them to
nanoseconds int values.

The timestamps do not need to be sorted, and may overlap. This can be
usefull for describing function calls. For example, if Thread P#0T#0 calls `foo`, and `foo` calls `bar`, the csv file may look like this:

```
Thread,Function,Start,Finish,Duration
P#0T#0,foo,0,200,200
P#0T#0,bar,50,150,100
```

### Generating csv files with Pallas

`pallas_print -cb trace.pallas` generates a csv file that shows recursive function calls.

Alternatively, you can use `pallas_print -c trace.pallas` to generate
a csv file that do not show recursive function calls. The previous example will look like this:

```
Thread,Function,Start,Finish,Duration
P#0T#0,foo,0,50,50
P#0T#0,bar,50,150,100
P#0T#0,foo,150,200,50
```

### Generating csv files from StarPU traces

First, generate a StarPU trace:
```
STARPU_FXT_PREFIX=trace_dir STARPU_FXT_TRACE=1 STARPU_MAIN_THREAD_BIND=1  chameleon_dtesting -o potrf --n 16000 --trace 
```

This creates an FxT trace `trace_dir/prof_file_${USER}_0`. You need to convert it to the Pajé format:
```
starpu_fxt_tool -i prof_file_${USER}_0
```

Then, create a csv file for StarVZ:
```
starpu_paje_summary paje.trace 
```

The generated `paje.trace.csv` file needs to be converted again using `tools/convert_starpu.py` (in the blup repository):

```
python tools/convert_starpu.py paje.trace.csv paje.trace_blup.csv 
```
