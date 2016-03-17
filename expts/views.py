import numpy as np
from matplotlib.figure import Figure
from matplotlib.backends.backend_wxagg import FigureCanvasWxAgg
import cv2, logging, wx

class RedirectText(object):
    def __init__(self, text_ctrl):
        self.text_ctrl = text_ctrl
    def write(self, s):
        wx.CallAfter(self.text_ctrl.WriteText, s)

### Wx ###
class View(wx.Frame):
    def __init__(self, parent, subs=[], conditions=[], manipulations=[], size=(1200,720)):
        wx.Frame.__init__(self, parent, title="Puffs Experiment Control", size=size)
        self.Center()
        
        self.n_perf_show = 50
        self.n_lick_show = 1200
        
        # Leftmost panel
        self.panel_left_sizer = wx.BoxSizer(wx.VERTICAL)
        self.add_sub_button = wx.Button(self, label='Add Subject')
        self.sub_box = wx.ListBox(self)
        self.sub_names,self.sub_strs = subs,[]
        self.update_sub_choices()
        self.cond_box = wx.ListBox(self, choices=conditions)
        self.manip_box = wx.ListBox(self, choices=manipulations)
        self.panel_left_sizer.Add(self.add_sub_button)
        self.panel_left_sizer.Add(self.sub_box, flag=wx.EXPAND|wx.ALL, proportion=1)
        self.panel_left_sizer.Add(self.cond_box, flag=wx.EXPAND|wx.ALL, proportion=1)
        self.panel_left_sizer.Add(self.manip_box, flag=wx.EXPAND|wx.ALL, proportion=1)

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
        self.rewarded_widg = wx.TextCtrl(self.panel_top)
        self.rewarded_widg.SetEditable(False)
        self.rewarded_lab = wx.StaticText(self.panel_top, label='Rewards: ', style=wx.ALIGN_RIGHT)
        self.bias_widg = wx.TextCtrl(self.panel_top)
        self.bias_widg.SetEditable(False)
        self.bias_lab = wx.StaticText(self.panel_top, label='RL Bias: ', style=wx.ALIGN_RIGHT)
        self.panel_top_sizer.Add(self.trial_n_lab, flag=wx.ALIGN_RIGHT, proportion=1)
        self.panel_top_sizer.Add(self.trial_n_widg, flag=wx.EXPAND|wx.ALL, proportion=1)
        self.panel_top_sizer.Add(self.session_runtime_lab, flag=wx.ALIGN_RIGHT, proportion=1)
        self.panel_top_sizer.Add(self.session_runtime_widg, flag=wx.EXPAND|wx.ALL, proportion=1)
        self.panel_top_sizer.Add(self.trial_runtime_lab, flag=wx.ALIGN_RIGHT, proportion=1)
        self.panel_top_sizer.Add(self.trial_runtime_widg,flag=wx.EXPAND|wx.ALL, proportion=1)
        self.panel_top_sizer.Add(self.rewarded_lab, flag=wx.ALIGN_RIGHT, proportion=1)
        self.panel_top_sizer.Add(self.rewarded_widg,flag=wx.EXPAND|wx.ALL, proportion=1)
        self.panel_top_sizer.Add(self.bias_lab, flag=wx.ALIGN_RIGHT, proportion=1)
        self.panel_top_sizer.Add(self.bias_widg,flag=wx.EXPAND|wx.ALL, proportion=1)
        self.panel_top.SetSizerAndFit(self.panel_top_sizer)
        
        # 2nd from top panel
        self.panel_top2 = wx.Panel(self)
        self.panel_top2_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.cal_lab = wx.StaticText(self.panel_top2, label='Flush spouts: ', style=wx.ALIGN_RIGHT)
        self.cal_but = wx.Button(self.panel_top2, label='Flush (1s)')
        self.locklev_lab = wx.StaticText(self.panel_top2, label='Lock level: ', style=wx.ALIGN_RIGHT)
        self.locklev_but = wx.Button(self.panel_top2, label='Lock')
        self.lev_lab = wx.StaticText(self.panel_top2, label='Change level: ', style=wx.ALIGN_RIGHT)
        self.levu_but = wx.Button(self.panel_top2, label='UP')
        self.levd_but = wx.Button(self.panel_top2, label='DOWN')
        self.reward_lab = wx.StaticText(self.panel_top2, label='Give reward: ', style=wx.ALIGN_RIGHT)
        self.rewardl_but = wx.Button(self.panel_top2, label='L')
        self.rewardr_but = wx.Button(self.panel_top2, label='R')
        self.puff_lab = wx.StaticText(self.panel_top2, label='Give puff: ', style=wx.ALIGN_RIGHT)
        self.puffl_but = wx.Button(self.panel_top2, label='L')
        self.puffr_but = wx.Button(self.panel_top2, label='R')
        self.panel_top2_sizer.Add(self.cal_lab, flag=wx.ALIGN_RIGHT, proportion=1)
        self.panel_top2_sizer.Add(self.cal_but, proportion=1)
        self.panel_top2_sizer.Add(self.locklev_lab, flag=wx.ALIGN_RIGHT, proportion=1)
        self.panel_top2_sizer.Add(self.locklev_but, proportion=1)
        self.panel_top2_sizer.Add(self.lev_lab, flag=wx.ALIGN_RIGHT, proportion=1)
        self.panel_top2_sizer.Add(self.levu_but, proportion=1)
        self.panel_top2_sizer.Add(self.levd_but, proportion=1)
        self.panel_top2_sizer.Add(self.reward_lab, flag=wx.ALIGN_RIGHT, proportion=1)
        self.panel_top2_sizer.Add(self.rewardr_but, proportion=1)
        self.panel_top2_sizer.Add(self.rewardl_but, proportion=1)
        self.panel_top2_sizer.Add(self.puff_lab, flag=wx.ALIGN_RIGHT, proportion=1)
        self.panel_top2_sizer.Add(self.puffr_but, proportion=1)
        self.panel_top2_sizer.Add(self.puffl_but, proportion=1)
        self.panel_top2.SetSizerAndFit(self.panel_top2_sizer)

        # bottom panel
        self.panel_bottom = wx.Panel(self,2)
        self.panel_bottom_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.start_button = wx.Button(self.panel_bottom, label="Run Session")
        self.start_button.SetBackgroundColour((0,255,0))
        self.pause_button = wx.Button(self.panel_bottom, label="Pause")
        self.pause_button.SetBackgroundColour((0,150,150))
        self.prepare_button = wx.Button(self.panel_bottom, label="Prepare Session")
        self.panel_bottom_sizer.AddStretchSpacer()
        self.panel_bottom_sizer.Add(self.prepare_button, flag=wx.EXPAND|wx.ALL, proportion=1)
        self.panel_bottom_sizer.AddStretchSpacer()
        self.panel_bottom_sizer.Add(self.start_button, flag=wx.EXPAND|wx.ALL, proportion=1)
        self.panel_bottom_sizer.AddStretchSpacer()
        self.panel_bottom_sizer.Add(self.pause_button, flag=wx.EXPAND|wx.ALL, proportion=1)
        self.panel_bottom_sizer.AddStretchSpacer()
        self.panel_bottom.SetSizerAndFit(self.panel_bottom_sizer)

        # performance plot panel
        self.panel_performance = wx.Panel(self,3)
        self.panel_performance_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.fig = Figure( figsize=(7.5, 4), dpi=80 )
        self.ax0 = self.fig.add_subplot(111)
        self.perfl,self.perfr,self.perfv,self.perfv_l,self.perfv_r,self.perf_data,self.w_perf_data,self.w_perfl,self.w_perfr,self.w_perfv,self.w_perfvl,self.w_perfvr = self.ax0.plot(np.zeros([self.n_perf_show,12])-1, color='gray')
        self.perfl.set_color('blue')
        self.perfr.set_color('green')
        self.w_perfl.set_color('blue')
        self.w_perfr.set_color('green')
        self.w_perfl.set_linewidth(3)
        self.w_perfr.set_linewidth(3)
        self.w_perf_data.set_linewidth(3)
        self.perfv.set_color('black')
        self.perfv.set_linestyle('dotted')
        self.perfv_l.set_color('blue')
        self.perfv_l.set_linestyle('dotted')
        self.perfv_r.set_color('green')
        self.perfv_r.set_linestyle('dotted')
        self.w_perfv.set_color('black')
        self.w_perfv.set_linestyle('dotted')
        self.w_perfv.set_linewidth(4)
        self.w_perfvl.set_color('blue')
        self.w_perfvl.set_linestyle('dotted')
        self.w_perfvl.set_linewidth(4)
        self.w_perfvr.set_color('green')
        self.w_perfvr.set_linestyle('dotted')
        self.w_perfvr.set_linewidth(4)
        self.perfl.set_alpha(0.4)
        self.perfr.set_alpha(0.4)
        self.perfv.set_alpha(0.4)
        self.w_perfl.set_alpha(0.4)
        self.w_perfr.set_alpha(0.4)
        self.w_perfv.set_alpha(0.4)
        self.perf_marks = [self.ax0.plot(m, -1)[0] for m in xrange(self.n_perf_show)]
        self.ax0.set_ylim([-0.02,1.08])
        self.ax0.set_xlim([-0.2,self.n_perf_show-0.8])
        self.canvas = FigureCanvasWxAgg(self.panel_performance, -1, self.fig)
        self.panel_performance_sizer.Add(self.canvas, flag=wx.EXPAND|wx.ALL, proportion=1)
        self.panel_performance.SetSizerAndFit(self.panel_performance_sizer)
        
        # lick meter panel
        self.panel_lick = wx.Panel(self,4)
        self.panel_lick_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.fig_lick = Figure( figsize=(7.5, 4), dpi=80 )
        self.ax_lick = self.fig_lick.add_subplot(111)
        self.canvas_lick = FigureCanvasWxAgg(self.panel_lick, -1, self.fig_lick)
        self.panel_lick_sizer.Add(self.canvas_lick, flag=wx.EXPAND|wx.ALL, proportion=1)
        self.panel_lick.SetSizerAndFit(self.panel_lick_sizer)
        
        # movie panel
        self.panel_mov = MoviePanel(self)
        
        # trial display panel
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
        self.sizer_l.Add(self.panel_lick, flag=wx.EXPAND, proportion=1)
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
    def update_sub_choices(self, rewards={}):
        self.sub_names = sorted(self.sub_names)
        self.sub_box.Clear()
        self.sub_strs = ['{} ({:0.0f}uL due)'.format(s,1000.-4.*rewards.get(s,0)) for s in self.sub_names]
        if self.sub_strs:
            self.sub_box.InsertItems(items=self.sub_strs, pos=0)
    def add_sub(self, s, rewards={}):
        if not isinstance(s, list):
            s = [s]
        s = [str(i) for i in s]
        self.sub_names += s
        self.sub_names = sorted(self.sub_names)
        self.update_sub_choices(rewards=rewards)
    def setup_axlick(self):
        self.ax_lick.clear()
        self.lick_data1,self.lick_data2 = self.ax_lick.plot(np.zeros((self.n_lick_show,2)), alpha=0.5)
        self.ax_lick.set_ylim([-.9,10.1])
    def set_bias(self, b):
        self.bias_widg.SetValue('{:0.2f} : {:0.2f}'.format(*b[::-1]))
    def set_history(self, th):
        history,winhist = th.history_glob,th.history_win
        
        data = history['perc']
        windata = winhist['perc']
        markers = history['outcome']
        cors = history['side']
        perfl = history['perc_l']
        perfr = history['perc_r']
        winpl = winhist['perc_l']
        winpr = winhist['perc_r']
        perfv = history['valid']
        vall = history['valid_l']
        valr = history['valid_r']
        winval = winhist['valid']
        winvall = winhist['valid_l']
        winvalr = winhist['valid_r']

        shapes = np.array(['v','^','s','o','x',None])
        sizes = np.array([7,7,4,4,4,4])
        cor_cols = ['blue','green']
        i0 = 0
        if len(data) < self.n_perf_show:
            def pad(d):
                d = np.pad(d, (0,self.n_perf_show-len(d)), mode='constant', constant_values=-1)
                d[d==-1] = np.nan
                return d
            data,perfl,perfr,perfv,winpl,winpr,vall,valr,winval,windata,winvall,winvalr = map(pad,[data,perfl,perfr,perfv,winpl,winpr,vall,valr,winval,windata,winvall,winvalr])
            markers = np.pad(markers, (0,self.n_perf_show-len(markers)), mode='constant', constant_values=-1)
            cors = (np.pad(cors, (0,self.n_perf_show-len(cors)), mode='constant', constant_values=-1)).astype(int)
        elif len(data) >= self.n_perf_show:
            i0 = len(data) - self.n_perf_show
            def cut(d):
                d = d.iloc[-self.n_perf_show:]
                return d
            data,perfl,perfr,perfv,winpl,winpr,vall,valr,winval,windata,winvall,winvalr = map(cut,[data,perfl,perfr,perfv,winpl,winpr,vall,valr,winval,windata,winvall,winvalr])
            markers = markers.iloc[-self.n_perf_show:].astype(int)
            cors = cors.iloc[-self.n_perf_show:].astype(int)
        
        self.perf_data.set_ydata(data)
        self.perfl.set_ydata(perfl)
        self.perfr.set_ydata(perfr)
        self.perfv.set_ydata(perfv)
        self.perfv_l.set_ydata(vall)
        self.perfv_r.set_ydata(valr)
        
        self.w_perf_data.set_ydata(windata)
        self.w_perfl.set_ydata(winpl)
        self.w_perfr.set_ydata(winpr)
        self.w_perfv.set_ydata(winval)
        self.w_perfvl.set_ydata(winvall)
        self.w_perfvr.set_ydata(winvalr)
        for i,d,new_m,mline,cor in zip(range(len(data)), data, markers, self.perf_marks, cors):
            mline.set_marker(shapes[new_m])
            mline.set_markersize(sizes[new_m])
            mline.set_markeredgewidth(1)
            mline.set_markeredgecolor(cor_cols[cor])
            mline.set_markerfacecolor(cor_cols[cor])
            mline.set_ydata(d)
        self.ax0.set_xticklabels([str(int(i0+float(i))) for i in self.ax0.get_xticks()])
        self.fig.canvas.draw()
    def set_lick_data(self, data):
        self.lick_data1.set_ydata(data[0][-self.n_lick_show:])
        self.lick_data2.set_ydata(data[1][-self.n_lick_show:])
        self.fig_lick.canvas.draw()
    def set_trial_data(self, th, sesh):
        times = th.trt['time']
        sides = th.trt['side']
        times_l,times_r = times[sides==0],times[sides==1]
        corside = th.trial.side

        self.ax_trial.cla()
        corcols = {0:'blue',1:'green'}

        self.ax_trial.plot(np.zeros(times_r.shape), times_r, marker='o', markeredgecolor='none', markerfacecolor='green', linestyle='None')
        self.ax_trial.plot(np.ones(times_l.shape), times_l, marker='o', markeredgecolor='none', markerfacecolor='blue', linestyle='None')
        
        self.ax_trial.hlines(0, -1., 2.,colors='k',linestyles='dashed')
        self.ax_trial.hlines(th.stim_phase_pad[0], -1., 2.,colors='k',linestyles='dashed')
        self.ax_trial.hlines(th.stim_phase_pad[0]+th.trial.dur, -1., 2.,colors=corcols[corside],linestyles='dashed')
        self.ax_trial.hlines(sum(th.stim_phase_pad)+th.trial.dur, -1., 2.,colors='gray',linestyles='dashed')
        self.ax_trial.hlines(sum(th.stim_phase_pad)+th.trial.dur+th.trial.delay, -1., 2.,colors='k',linestyles='dashed')
        
        ylim = th.phase_dur+th.trial.delay+0.4
        
        self.ax_trial.set_ylim([-0.2,ylim])
        self.ax_trial.set_xlim([-1.,2.])
        self.ax_trial.set_xticks([],[])
        self.fig_trial.canvas.draw()

class MoviePanel(wx.Panel):
    def __init__(self, parent, size=(320,240)):
        wx.Panel.__init__(self, parent, wx.ID_ANY, (0,0), size)
        self.size = size
        height, width = size[::-1] 
        dummy = np.zeros((height,width))
        self.SetSize((width, height))

        self.bmp = wx.BitmapFromBuffer(width, height, dummy)

        self.Bind(wx.EVT_PAINT, self.on_paint)

    def on_paint(self, evt):
        dc = wx.BufferedPaintDC(self)
        dc.DrawBitmap(self.bmp, 0, 0)

    def set_frame(self, fr):
        fr = cv2.cvtColor(fr.astype(np.uint8), cv2.COLOR_GRAY2RGB)
        self.bmp.CopyFromBuffer(fr)
        self.Refresh()

