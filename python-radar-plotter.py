# Python + Arduino-based Radar Plotter
#
# ** Works with any motor that outputs angular rotation
# ** and with any distance sensor (HC-SR04, VL53L0x,LIDAR)
#
import numpy as np
import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
from matplotlib.widgets import Button
import serial,sys,glob
import serial.tools.list_ports as COMs
#
#
############################################
# Find Arudino ports, select one, then start communication with it
############################################
#
def port_search():
    if sys.platform.startswith('win'): # Windows
        ports = ['COM{0:1.0f}'.format(ii) for ii in range(1,256)]
    elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
        ports = glob.glob('/dev/tty[A-Za-z]*')
    elif sys.platform.startswith('darwin'): # MAC
        ports = glob.glob('/dev/tty.*')
    else:
        raise EnvironmentError('Machine Not pyserial Compatible')

    arduinos = []
    for port in ports: # loop through to determine if accessible
        if len(port.split('Bluetooth'))>1:
            continue
        try:
            ser = serial.Serial(port)
            ser.close()
            arduinos.append(port) # if we can open it, consider it an arduino
        except (OSError, serial.SerialException):
            pass
    return arduinos

arduino_ports = port_search()
ser = serial.Serial(arduino_ports[0],baudrate=115200) # match baud on Arduino
ser.flush() # clear the port
#
############################################
# Start the interactive plotting tool and
# plot 180 degrees with dummy data to start
############################################
#
fig = plt.figure(facecolor='k')
win = fig.canvas.manager.window # figure window
screen_res = win.wm_maxsize() # used for window formatting later
dpi = 150.0 # figure resolution
fig.set_dpi(dpi) # set figure resolution

# polar plot attributes and initial conditions
ax = fig.add_subplot(111,polar=True,facecolor='#006d70')
ax.set_position([-0.05,-0.05,1.1,1.05])
r_max = 100.0 # can change this based on range of sensor
ax.set_ylim([0.0,r_max]) # range of distances to show
ax.set_xlim([0.0,np.pi]) # limited by the servo span (0-180 deg)
ax.tick_params(axis='both',colors='w')
ax.grid(color='w',alpha=0.5) # grid color
ax.set_rticks(np.linspace(0.0,r_max,5)) # show 5 different distances
ax.set_thetagrids(np.linspace(0.0,180.0,10)) # show 10 angles
angles = np.arange(0,181,1) # 0 - 180 degrees
theta = angles*(np.pi/180.0) # to radians
dists = np.ones((len(angles),)) # dummy distances until real data comes in
pols, = ax.plot([],linestyle='',marker='o',markerfacecolor = 'w',
                 markeredgecolor='#EFEFEF',markeredgewidth=1.0,
                 markersize=10.0,alpha=0.9) # dots for radar points
line1, = ax.plot([],color='w',
                  linewidth=4.0) # sweeping arm plot

# figure presentation adjustments
fig.set_size_inches(0.96*(screen_res[0]/dpi),0.96*(screen_res[1]/dpi))
plot_res = fig.get_window_extent().bounds # window extent for centering
win.wm_geometry('+{0:1.0f}+{1:1.0f}'.\
                format((screen_res[0]/2.0)-(plot_res[2]/2.0),
                       (screen_res[1]/2.0)-(plot_res[3]/2.0))) # centering plot
fig.canvas.toolbar.pack_forget() # remove toolbar for clean presentation
fig.canvas.set_window_title('Arduino Radar')

fig.canvas.draw() # draw before loop
axbackground = fig.canvas.copy_from_bbox(ax.bbox) # background to keep during loop

############################################
# button event to stop program
############################################

def stop_event(event):
    global stop_bool
    stop_bool = 1
prog_stop_ax = fig.add_axes([0.85,0.025,0.125,0.05])
pstop = Button(prog_stop_ax,'Stop Program',color='#FCFCFC',hovercolor='w')
pstop.on_clicked(stop_event)
# button to close window
def close_event(event):
    global stop_bool,close_bool
    if stop_bool:
        plt.close('all')
    stop_bool = 1
    close_bool = 1
close_ax = fig.add_axes([0.025,0.025,0.125,0.05])
close_but = Button(close_ax,'Close Plot',color='#FCFCFC',hovercolor='w')
close_but.on_clicked(close_event)

fig.show()

############################################
# inifinite loop, constantly updating the
# 180deg radar with incoming Arduino data
############################################
#
start_word,stop_bool,close_bool = False,False,False
while True:
    try:
        if stop_bool: # stops program
            fig.canvas.toolbar.pack_configure() # show toolbar
            if close_bool: # closes radar window
                plt.close('all')
            break
        ser_bytes = ser.readline() # read Arduino serial data
        decoded_bytes = ser_bytes.decode('utf-8') # decode data to utf-8
        data = (decoded_bytes.replace('\r','')).replace('\n','')
        if start_word:
            vals = [float(ii) for ii in data.split(',')]
            if len(vals)<2:
                continue
            angle,dist = vals # separate into angle and distance
            if dist>r_max:
                dist = 0.0 # measuring more than r_max, it's likely inaccurate
            dists[int(angle)] = dist
            if angle % 5 ==0: # update every 5 degrees
                pols.set_data(theta,dists)
                fig.canvas.restore_region(axbackground)
                ax.draw_artist(pols)

                line1.set_data(np.repeat((angle*(np.pi/180.0)),2),
                   np.linspace(0.0,r_max,2))
                ax.draw_artist(line1)

                fig.canvas.blit(ax.bbox) # replot only data
                fig.canvas.flush_events() # flush for next plot
        else:
            if data=='Radar Start': # stard word on Arduno
                start_word = True # wait for Arduino to output start word
                print('Radar Starting...')
            else:
                continue
           
    except KeyboardInterrupt:
        plt.close('all')
        print('Keyboard Interrupt')
        break
