import numpy as np
from matplotlib.figure import Figure
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg
import logging, wx

class RedirectText(object):
    def __init__(self, text_ctrl):
        self.text_ctrl = text_ctrl
    def write(self, s):
        wx.CallAfter(self.text_ctrl.WriteText, s)

### Wx ###
class View(wx.Frame):
    def __init__(self, parent, subs=[], size=(1200,730)):
        wx.Frame.__init__(self, parent, title="Eyeblink Experiment Control", size=size)
        self.Center()
        
        self.n_live_show = 1200
        
        # Leftmost panel
        self.panel_left_sizer = wx.BoxSizer(wx.VERTICAL)
        self.add_sub_button = wx.Button(self, label='Add Subject')
        self.sub_box = wx.ListBox(self)
        self.sub_names,self.sub_strs = subs,[]
        self.update_sub_choices()
        self.imaging_box = wx.CheckBox(self, label='Imaging')
        self.panel_left_sizer.Add(self.imaging_box)
        self.panel_left_sizer.Add(self.add_sub_button)
        self.panel_left_sizer.Add(self.sub_box, flag=wx.EXPAND|wx.ALL, proportion=1)

        # top panel
        self.panel_top = wx.Panel(self,1)
        self.panel_top_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.trial_n_widg = wx.TextCtrl(self.panel_top)
        self.trial_n_widg.SetEditable(False)
        self.trial_n_lab = wx.StaticText(self.panel_top, label='Trial #: ', style=wx.ALIGN_RIGHT)
        self.session_runtime_widg = wx.TextCtrl(self.panel_top)
        self.session_runtime_widg.SetEditable(False)
        self.session_runtime_lab = wx.StaticText(self.panel_top, label='Session time: ', style=wx.ALIGN_RIGHT)
        self.trial_runtime_widg = wx.TextCtrl(self.panel_top)
        self.trial_runtime_widg.SetEditable(False)
        self.trial_runtime_lab = wx.StaticText(self.panel_top, label='Trial time: ', style=wx.ALIGN_RIGHT)
        self.panel_top_sizer.Add(self.trial_n_lab, flag=wx.ALIGN_RIGHT, proportion=1)
        self.panel_top_sizer.Add(self.trial_n_widg, flag=wx.EXPAND|wx.ALL, proportion=1)
        self.panel_top_sizer.Add(self.session_runtime_lab, flag=wx.ALIGN_RIGHT, proportion=1)
        self.panel_top_sizer.Add(self.session_runtime_widg, flag=wx.EXPAND|wx.ALL, proportion=1)
        self.panel_top_sizer.Add(self.trial_runtime_lab, flag=wx.ALIGN_RIGHT, proportion=1)
        self.panel_top_sizer.Add(self.trial_runtime_widg,flag=wx.EXPAND|wx.ALL, proportion=1)
        self.panel_top.SetSizerAndFit(self.panel_top_sizer)
        
        # 2nd from top panel
        self.panel_top2 = wx.Panel(self)
        self.panel_top2_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.light_lab = wx.StaticText(self.panel_top2, label='Light: ', style=wx.ALIGN_RIGHT)
        self.lighton_but = wx.Button(self.panel_top2, label='ON')
        self.lightoff_but = wx.Button(self.panel_top2, label='OFF')
        self.puff_lab = wx.StaticText(self.panel_top2, label='Give puff: ', style=wx.ALIGN_RIGHT)
        self.puff_but = wx.Button(self.panel_top2, label='PUFF')
        self.panel_top2_sizer.Add(self.light_lab, flag=wx.ALIGN_RIGHT, proportion=1)
        self.panel_top2_sizer.Add(self.lighton_but, proportion=1)
        self.panel_top2_sizer.Add(self.lightoff_but, proportion=1)
        self.panel_top2_sizer.Add(self.puff_lab, flag=wx.ALIGN_RIGHT, proportion=1)
        self.panel_top2_sizer.Add(self.puff_but, proportion=1)
        self.panel_top2.SetSizerAndFit(self.panel_top2_sizer)

        # bottom panel
        self.panel_bottom = wx.Panel(self,2)
        self.panel_bottom_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.start_button = wx.Button(self.panel_bottom, label="Run Session")
        self.start_button.SetBackgroundColour((0,255,0))
        self.pause_button = wx.Button(self.panel_bottom, label="Pause")
        self.pause_button.SetBackgroundColour((0,150,150))
        self.prepare_button = wx.Button(self.panel_bottom, label="Prepare Session")
        self.tcpip_button = wx.Button(self.panel_bottom, label="TCPIP")
        self.panel_bottom_sizer.AddStretchSpacer()
        self.panel_bottom_sizer.Add(self.prepare_button, flag=wx.EXPAND|wx.ALL, proportion=1)
        self.panel_bottom_sizer.AddStretchSpacer()
        self.panel_bottom_sizer.Add(self.start_button, flag=wx.EXPAND|wx.ALL, proportion=1)
        self.panel_bottom_sizer.AddStretchSpacer()
        self.panel_bottom_sizer.Add(self.pause_button, flag=wx.EXPAND|wx.ALL, proportion=1)
        self.panel_bottom_sizer.AddStretchSpacer()
        self.panel_bottom_sizer.Add(self.tcpip_button, flag=wx.EXPAND|wx.ALL, proportion=1)
        self.panel_bottom_sizer.AddStretchSpacer()
        self.panel_bottom.SetSizerAndFit(self.panel_bottom_sizer)

        # performance plot panel (UNUSED)
        self.panel_performance = wx.Panel(self,3)
        self.panel_performance_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.fig = Figure( figsize=(7.5, 4), dpi=80 )
        self.ax0 = self.fig.add_subplot(111)
        self.canvas = FigureCanvasWxAgg(self.panel_performance, -1, self.fig)
        self.panel_performance_sizer.Add(self.canvas, flag=wx.EXPAND|wx.ALL, proportion=1)
        self.panel_performance.SetSizerAndFit(self.panel_performance_sizer)
        
        # live measurements panel
        self.panel_live = wx.Panel(self,4)
        self.panel_live_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.fig_live = Figure( figsize=(7.5, 4), dpi=80 )
        self.ax_live = self.fig_live.add_subplot(111)
        self.canvas_live = FigureCanvasWxAgg(self.panel_live, -1, self.fig_live)
        self.panel_live_sizer.Add(self.canvas_live, flag=wx.EXPAND|wx.ALL, proportion=1)
        self.panel_live.SetSizerAndFit(self.panel_live_sizer)
        
        # movie panel
        self.panel_mov = MoviePanel(self)
        
        # trial display panel (UNUSED)
        self.panel_trial = wx.Panel(self,5)
        self.panel_trial_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.fig_trial = Figure( figsize=(6.5, 3), dpi=80 )
        self.ax_trial = self.fig_trial.add_subplot(111)
        self.canvas_trial = FigureCanvasWxAgg(self.panel_trial, -1, self.fig_trial)
        self.panel_trial_sizer.Add(self.canvas_trial, flag=wx.EXPAND|wx.ALL, proportion=1)
        self.panel_trial.SetSizerAndFit(self.panel_trial_sizer)

        # live stream textbox
        self.std_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.stdout_box = wx.TextCtrl(self, wx.ID_ANY, style=wx.TE_MULTILINE|wx.TE_READONLY|wx.HSCROLL|wx.VSCROLL, size=(-1,100))
        self.stderr_box = wx.TextCtrl(self, wx.ID_ANY, style=wx.TE_MULTILINE|wx.TE_READONLY|wx.HSCROLL|wx.VSCROLL, size=(-1,100))
        self.usrinput_box = wx.TextCtrl(self, wx.ID_ANY, style=wx.TE_PROCESS_ENTER|wx.HSCROLL|wx.VSCROLL, size=(-1,100), value='(notes)')
        self.redir_out=RedirectText(self.stdout_box)
        self.redir_err=RedirectText(self.stderr_box)
        self.stderr_box.SetForegroundColour(wx.RED)
        self.std_sizer.Add(self.stdout_box, wx.ID_ANY, wx.ALL|wx.EXPAND)
        self.std_sizer.Add(self.stderr_box, wx.ID_ANY, wx.ALL|wx.EXPAND)
        self.std_sizer.Add(self.usrinput_box, wx.ID_ANY, wx.ALL|wx.EXPAND)

        # main view sizers
        self.sizer_global = wx.BoxSizer(wx.VERTICAL)
        self.sizer_main = wx.BoxSizer(wx.HORIZONTAL)
        self.sizer_v = wx.BoxSizer(wx.VERTICAL)
        self.sizer_h = wx.BoxSizer(wx.HORIZONTAL)
        self.sizer_l = wx.BoxSizer(wx.VERTICAL)
        self.sizer_r = wx.BoxSizer(wx.VERTICAL)

        self.sizer_l.Add(self.panel_performance, flag=wx.EXPAND, proportion=1)
        self.sizer_l.Add(self.panel_live, flag=wx.EXPAND, proportion=1)
        self.sizer_r.Add(self.panel_mov, flag=wx.ALIGN_CENTER_HORIZONTAL) #proportion=1)
        self.sizer_r.Add(self.panel_trial, flag=wx.EXPAND, proportion=1)

        self.sizer_h.Add(self.sizer_l, flag=wx.EXPAND, proportion=1)
        self.sizer_h.Add(self.sizer_r, flag=wx.EXPAND, proportion=1)

        self.sizer_v.Add(self.panel_top, flag=wx.EXPAND|wx.ALL, proportion=1)
        self.sizer_v.Add(self.panel_top2, flag=wx.EXPAND|wx.ALL, proportion=1)
        self.sizer_v.Add(self.panel_bottom, flag=wx.EXPAND|wx.ALL, proportion=1)
        self.sizer_v.Add(self.sizer_h, proportion=1)

        self.sizer_main.Add(self.panel_left_sizer, flag=wx.EXPAND|wx.ALL, proportion=1)
        self.sizer_main.Add(self.sizer_v, flag=wx.EXPAND|wx.ALL, proportion=1)

        self.sizer_global.Add(self.std_sizer, flag=wx.EXPAND, proportion=1)
        self.sizer_global.Add(self.sizer_main, flag=wx.EXPAND, proportion=1)

        self.SetSizer(self.sizer_global)

        self.Show()
        self.Layout()
    def update_sub_choices(self):
        self.sub_names = sorted(self.sub_names)
        self.sub_box.Clear()
        self.sub_strs = self.sub_names
        if self.sub_strs:
            self.sub_box.InsertItems(items=self.sub_strs, pos=0)
    def add_sub(self, s):
        if not isinstance(s, list):
            s = [s]
        s = [str(i) for i in s]
        self.sub_names += s
        self.sub_names = sorted(self.sub_names)
        self.update_sub_choices()
    def setup_axlive(self):
        self.ax_live.clear()
        self.live_data1,self.live_data2,self.live_data3 = self.ax_live.plot(np.zeros((self.n_live_show,3)), alpha=0.5)
        self.ax_live.set_ylim([-.9,10.1])
        self.ax_live.set_xlim([0,self.n_live_show])
    def set_live_data(self, data):
        self.live_data1.set_ydata(data[0][-self.n_live_show:])
        self.fig_live.canvas.draw()

class MoviePanel(wx.Panel):
    def __init__(self, parent, size=(320,240)):
        wx.Panel.__init__(self, parent, wx.ID_ANY, (0,0), size)
        self.size = size
        height, width = size[::-1] 
        self.dummy = np.empty((height,width,3), dtype=np.uint8)
        self.SetSize((width, height))

        self.bmp = wx.BitmapFromBuffer(width, height, self.dummy)

        self.Bind(wx.EVT_PAINT, self.on_paint)

    def on_paint(self, evt):
        dc = wx.BufferedPaintDC(self)
        dc.DrawBitmap(self.bmp, 0, 0)

    def set_frame(self, fr):
        if fr is None:
            return
        fr = np.array([fr,fr,fr]).transpose([1,2,0]).astype(np.uint8)
        self.dummy.flat[:] = fr.flat[:]
        self.bmp.CopyFromBuffer(self.dummy)
        self.Refresh()

