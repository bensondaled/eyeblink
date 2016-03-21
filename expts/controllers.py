import threading, wx, time, sys, logging, Queue
import numpy as np
from session import Session
from views import View
from subjects import Subject, list_subjects
from settings.param_handlers import ParamHandler
from util import setup_logging
import config

def pretty_time(t):
    if t<60:
        return '%0.0f s'%t
    else:
        return '%0.0f m, %0.0f s'%(np.floor(t/60.),t%60.)

class Controller:

    REFRESH_INTERVAL = 500 #ms
    STATE_NULL = 0
    STATE_PREPARED = 1
    STATE_RUNNING = 2
    STATE_KILLED_SESSION = 3
    STATE_RUN_COMPLETE = 4

    def __init__(self):
        # Make app
        self.app = wx.App(False) 

        # Generate view    
        subs_list = list_subjects()
        self.view = View(None, subs=subs_list)
        setup_logging()

        # Button bindings
        self.view.start_button.Bind(wx.EVT_BUTTON, self.evt_onoff)
        self.view.prepare_button.Bind(wx.EVT_BUTTON, self.evt_prepare)
        self.view.pause_button.Bind(wx.EVT_BUTTON, self.evt_pause)
        self.view.Bind(wx.EVT_CLOSE, self.evt_close)
        self.view.add_sub_button.Bind(wx.EVT_BUTTON, self.evt_addsub)
        self.view.usrinput_box.Bind(wx.EVT_TEXT_ENTER, self.update_usrinput)

        # Runtime
        self.update_state(self.STATE_NULL)

        # Run
        #self.view.Show()
        self.app.MainLoop()

    def update_state(self, st=None):
        if st is not None:
            self.state = st

        if self.state == self.STATE_NULL:
            self.view.prepare_button.Enable()
            self.view.add_sub_button.Enable()
            self.view.start_button.Disable()
            self.view.pause_button.Disable()
            self.view.update_sub_choices(list_rewards())
        elif self.state == self.STATE_PREPARED:
            self.view.prepare_button.Disable()
            self.view.add_sub_button.Disable()
            self.view.start_button.SetLabel("Run Session")
            self.view.start_button.SetBackgroundColour((0,255,0))
            self.view.start_button.Enable()
            self.view.pause_button.Disable()
        elif self.state == self.STATE_RUNNING:
            self.view.prepare_button.Disable()
            self.view.add_sub_button.Disable()
            self.view.start_button.Disable()
            self.view.start_button.SetLabel('End Session')
            self.view.start_button.SetBackgroundColour((255,0,0))
            self.view.pause_button.Enable()
        elif self.state == self.STATE_KILLED_SESSION:
            self.view.start_button.SetLabel('Ending...')
            self.view.start_button.Disable()
            self.view.pause_button.Disable()
            if self.session.session_on:
                self.update_timer = wx.CallLater(self.REFRESH_INTERVAL, self.update_state)
            else:
                self.update_state(self.STATE_RUN_COMPLETE)
        elif self.state == self.STATE_RUN_COMPLETE:
            self.view.SetTitle('Puffs Experiment Control')
            self.update_timer.Stop()
            self.view.start_button.SetLabel("Run Session")
            self.view.start_button.SetBackgroundColour((0,255,0))
            self.view.prepare_button.Enable()
            self.view.add_sub_button.Enable()
            self.view.start_button.Disable()
            self.view.pause_button.Disable()
            self.view.update_sub_choices(list_rewards())
    
    def update(self):
        if (not self.session.session_on) and self.state == self.STATE_RUNNING:
            self.update_state(self.STATE_RUN_COMPLETE)
            return

        # checks
        if self.view.trial_n_widg.GetValue() == str(self.session.th.idx):
            new_trial_flag = False
        else:
            new_trial_flag = True

        # clocks
        self.view.session_runtime_widg.SetValue(pretty_time(self.session.session_runtime))

        # plots
        try:
            self.view.set_lick_data(self.session.ar.accum_q.get(block=False))
        except Queue.Empty:
            pass

        # movie
        self.view.panel_mov1.set_frame(self.session.cam1.get_current_frame(self.session.cam1.cS))
        self.view.panel_mov2.set_frame(self.session.cam2.get_current_frame(self.session.cam2.cS))
        
        # trial
        if new_trial_flag:
            self.update_trial()

        # pauses
        if self.session.paused:
            self.view.pause_button.SetLabel('Unpause')
            self.view.pause_button.SetBackgroundColour((0,255,0))
            self.view.start_button.Disable()
        elif not self.session.paused:
            self.view.pause_button.SetLabel('Pause')
            self.view.pause_button.SetBackgroundColour((0,150,150))
            if self.session.session_on and not self.session.session_kill:
                self.view.start_button.Enable()
            
        self.update_timer = wx.CallLater(self.REFRESH_INTERVAL, self.update)

    def update_trial(self):
        if self.session.th.idx < 0:
            return
        self.view.trial_n_widg.SetValue("%s (%s)"%(str(self.session.th.idx),str(self.session.th.valid_idx)))
        if self.session.th.idx > 0:
            self.view.set_history(self.session.th)

    ####### EVENTS ########
    def evt_prepare(self, evt):
        sel_sub = self.view.sub_box.GetSelection()
        if wx.NOT_FOUND in [sel_sub]:
            dlg = wx.MessageDialog(self.view, message='Selections not made.', caption='Preparation not performed.', style=wx.OK)
            res = dlg.ShowModal()
            dlg.Destroy()
            return

        sub_name = self.view.sub_names[sel_sub]

        sub = Subject(sub_name)
        ph = ParamHandler(sub)
        self.session = Session(ph.params)

        self.view.setup_axlick()
        self.view.SetTitle('{}'.format(sub_name))

        self.update_state(self.STATE_PREPARED)
        self.update()

    def evt_onoff(self, evt):
        if not self.STATE_PREPARED:
            dlg = wx.MessageDialog(self.view, message='', caption='No session prepared.', style=wx.OK)
            res = dlg.ShowModal()
            dlg.Destroy()
            return
        elif self.state != self.STATE_RUNNING:
            self.update_state(self.STATE_RUNNING)
            self.run_th = threading.Thread(target=self.session.run)
            self.run_th.start()
        elif self.state == self.STATE_RUNNING:
            self.session.session_kill = True
            self.update_state(self.STATE_KILLED_SESSION)

    def evt_pause(self, evt):
        if not self.session.paused:
            self.session.paused += 1
            self.view.pause_button.SetLabel('Unpause')
            self.view.pause_button.SetBackgroundColour((0,255,0))
            self.view.start_button.Disable()
        elif self.session.paused:
            self.session.paused = max(self.session.paused-1,0)
            self.view.pause_button.SetLabel('Pause')
            self.view.pause_button.SetBackgroundColour((0,100,200))
            self.view.start_button.Enable()

    def evt_close(self, evt):
        if self.state in [self.STATE_RUNNING]:
            dlg = wx.MessageDialog(self.view, message='End session before closing interface.', caption='Session is active.', style=wx.OK)
            res = dlg.ShowModal()
            dlg.Destroy()
            evt.Veto()
        elif self.state in [self.STATE_NULL, self.STATE_RUN_COMPLETE, self.STATE_PREPARED]:
            dlg = wx.MessageDialog(self.view, message="", caption="Exit Experiment?", style=wx.OK|wx.CANCEL)
            result = dlg.ShowModal()
            dlg.Destroy()
            if result == wx.ID_OK:
                if self.state == self.STATE_PREPARED:
                    self.session.end()
                    self.update_state(self.STATE_KILLED_SESSION)
                    while self.state != self.STATE_RUN_COMPLETE:
                        pass
                self.view.Destroy()
            else:
                evt.Veto()

    def evt_addsub(self, evt):
        dlg = wx.TextEntryDialog(self.view, message='Enter new subject name:')
        ret = dlg.ShowModal()
        if ret == wx.ID_OK:
            self.view.add_sub(dlg.GetValue().strip().lower(), rewards=list_rewards())
        else:
            pass

    def update_usrinput(self, evt):
        self.session.notes = self.view.usrinput_box.GetValue()
        logging.info('Metadata updated.')
