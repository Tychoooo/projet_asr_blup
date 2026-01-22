from bokeh import events
from bokeh.io import curdoc
from bokeh.layouts import layout, column
from bokeh.models import Div, RangeSlider, Spinner, CustomJS, DatetimeTickFormatter, RangeTool, TapTool
from bokeh.models import Legend, HoverTool, LabelSet, ColumnDataSource, MultiSelect, CDSView, CustomJSFilter, AllIndices, Button
from bokeh.models.widgets import FileInput
from bokeh.plotting import figure, show, output_file, save
from bokeh.events import Tap
from tkinter import Tk
from tkinter.filedialog import askopenfilename
import sys
import datetime
import numpy as np
import pandas as pd
import blup_core as bp



if len(sys.argv)>1:
    trace=bp.BlupTrace(sys.argv[1])
else:
    trace=bp.BlupTrace()

    ########################## Top of the screen
# At the top of the screen, we have a button for choosing a trace, and
# a div that displays the trace name
div = Div(text="<p>Load Trace:</p>")
file_input = Button(label="Select trace")
trace_title = Div(width_policy="max", styles={'font-size': '150%'}, text="")

# Add a button for loading a trace. The files are located on the server system
def select_file():
    global trace, gantt_chart
    root = Tk()
    root.attributes('-topmost', True)
    root.withdraw()
    filename = askopenfilename(filetypes=[("Pallas trace","*.pallas"), ("OTF2 trace","*.otf2"),("CSV file","*.csv")])
    if filename:
        trace.open_trace(filename)
        trace_title.text=filename    
        update_display()

file_input.on_click(lambda x: select_file())

# update display of the current dataframe
def update_display():
    global trace, gantt_chart
    gantt_chart.y_range.factors=list(reversed(trace.active_threads))
    gantt_chart.xaxis[0].formatter = DatetimeTickFormatter()
    multiselect.options = trace.threads
    multiselect.value = trace.active_threads
    new_data_source=ColumnDataSource(trace.df)
    trace.data_source.data=dict(new_data_source.data)

############################ Details view
# On the right part of the screen, we display details on the selected function
# This view is composed of two divs
# - selected_indices_div: prints the selected indices  (eg. "1, 2, 13"). This is mostly for debugging
# - details_div: prints the callstack and other information
# 

# This function is called when selected_indices_div changes
def update_details(attr, old, new):
    global trace
    # new contains an array of indices represented as a string (eg. "1, 2, 13")
    indices=new.split(',')

    depth=0
    frame=trace.df.loc[int(indices[depth])]
    text="<b>Thread</b>: "+frame["Thread"]+"<br/>" \
        "<ol>"
    for depth in range(len(indices)):
        frame=trace.df.loc[int(indices[depth])]
        duration=frame["Duration"]
        upper_duration=pd.Timedelta(0)
        if(depth<len(indices)-1):
            upper_frame=trace.df.loc[int(indices[depth+1])]
            upper_duration=upper_frame["Duration"]

        text=text+"<li>"
        text=text+"<b>Function</b>: "+frame["Function"]+"<br/>" 
        text=text+"<b>Start</b>: "+bp.pretty_duration_pandas(frame["Start"])+"<br/>"
        text=text+"<b>Finish</b>: "+bp.pretty_duration_pandas(frame["Finish"])+"<br/>"
        if upper_duration > pd.Timedelta(0):
            percentage= '%.2f' % (100*duration/upper_duration)
            text=text+"<b>Duration</b>: "+bp.pretty_duration_pandas(duration)+" ("+percentage+"%)<br/></div>"
        else:
            text=text+"<b>Duration</b>: "+bp.pretty_duration_pandas(duration)+"<br/></div>"
        text=text+"<b>Depth</b>: "+str(frame["Depth"])+"<br/>"
        text=text+"</li>"

    text=text+"</ol>"
    details_div.text=text;

details_div = Div(width_policy="max", text="")
selected_indices_div = Div(width_policy="max", text="")
selected_indices_div.on_change("text", update_details)

details_layout = column(children=[selected_indices_div, details_div],sizing_mode="stretch_height" )

############################ Central panel
# At the center of the screen, we display a gantt chart
#


gantt_width=1500
gantt_height=800
gantt_chart=trace.create_chart(gantt_width, gantt_height)
trace.add_gantt(gantt_chart)

# Display the whole trace, and the current position being displayed
rangetool_height=50
select = figure(height=rangetool_height, width=gantt_width, y_range=gantt_chart.y_range,
                x_axis_type="datetime", y_axis_type=None,
                tools="", toolbar_location=None, background_fill_color="#efefef")

range_tool = RangeTool(x_range=gantt_chart.x_range)
range_tool.overlay.fill_color = "navy"
range_tool.overlay.fill_alpha = 0.2
select.add_tools(range_tool)


## Tap tool
# When user clicks a glyph, show the detail in the detail div
on_tap_callback = CustomJS(args=dict(source=trace.data_source,
                                     selected_indices=selected_indices_div), code="""
// Changing selecting_indices will trigger the update_details callback
selected_indices.text=source.selected.indices.toString();
""")
tap = TapTool(callback=on_tap_callback)
gantt_chart.tools.append(tap)


# When data change (eg, loading a new trace), reset xrange and yrange
js_reset = CustomJS(args=dict(figure=gantt_chart), code="figure.reset.emit()")
trace.data_source.js_on_change('data', js_reset)

# Add a toolkit for selecting the threads to be displayed
def update_threads():
    global trace
    trace.active_threads=multiselect.value
    update_display()
multiselect = MultiSelect(value=trace.active_threads, options=trace.threads, height_policy="max")
button = Button(label="update")
button.on_click(update_threads)

# switch visualization from gantt chart to flamgraph
def gantt_flame_callback():
    global trace, gantt_chart

    if (gantt_flame_button.label=="FlameGraph"):
        # Currently, we display a Gantt chart. We need to display a
        # flamegraph instead

        # Hide the current display
        g=gantt_chart.select_one({'name': 'gantt'})
        g.visible=False
        # Display a Flamegraph
        f=gantt_chart.select_one({'name': 'flamegraph'})
        if f is None:
            trace.add_flame(gantt_chart)
        else:
            f.visible=True
        gantt_flame_button.label="Gantt"
    else:
        # Currently, we display a FlameGraph. We need to display a
        # Gantt chart instead
        f=gantt_chart.select_one({'name': 'flamegraph'})
        f.visible=False

        g=gantt_chart.select_one({'name': 'gantt'})
        if g is None:
            gantt_chart=trace.add_gantt(gantt_chart)
        else:
            g.visible=True
        gantt_flame_button.label="FlameGraph"
    update_display()

gantt_flame_button = Button(label="FlameGraph")
gantt_flame_button.on_click(gantt_flame_callback)

multiselect_layout = column(children=[multiselect, button, gantt_flame_button],sizing_mode="stretch_height" )

column_plots=column(gantt_chart, select)


############################ General layout
layout = layout(
    [
        [div, file_input, trace_title],
        [multiselect_layout, column_plots, details_layout],
    ],
)

# display result
curdoc().add_root(layout)
curdoc().title = "Blup"
