import threading, wx, time, sys, logging, Queue
import numpy as np
import matplotlib.pyplot as pl
from session import Session
from views import View
from subjects import Subject, list_subjects
from settings.param_handlers import ParamHandler
from hardware import dummy_light,dummy_puff
from util import setup_logging
from util import TCPIP
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
        if False:#not config.TESTING_MODE:
            sys.stdout=self.view.redir_out
            sys.stderr=self.view.redir_err
        setup_logging(outwin=self.view.redir_out,errwin=self.view.redir_err)

        self.tcpip = TCPIP(config.scanimage_tcpip_address)

        # Button bindings
        self.view.start_button.Bind(wx.EVT_BUTTON, self.evt_onoff)
        self.view.prepare_button.Bind(wx.EVT_BUTTON, self.evt_prepare)
        self.view.pause_button.Bind(wx.EVT_BUTTON, self.evt_pause)
        self.view.tcpip_button.Bind(wx.EVT_BUTTON, self.evt_tcpip)
        self.view.Bind(wx.EVT_CLOSE, self.evt_close)
        self.view.lighton_but.Bind(wx.EVT_BUTTON, lambda evt, temp=1: self.set_light(evt, temp))
        self.view.lightoff_but.Bind(wx.EVT_BUTTON, lambda evt, temp=0: self.set_light(evt, temp))
        self.view.puff_but.Bind(wx.EVT_BUTTON, self.evt_puff)
        self.view.deliver_but.Bind(wx.EVT_BUTTON, self.evt_deliver)
        self.view.roi_but.Bind(wx.EVT_BUTTON, self.evt_roi)
        self.view.add_sub_button.Bind(wx.EVT_BUTTON, self.evt_addsub)
        self.view.resetcam_button.Bind(wx.EVT_BUTTON, self.evt_resetcam)
        self.view.usrinput_box.Bind(wx.EVT_TEXT_ENTER, self.update_usrinput)
        self.view.slider.Bind(wx.EVT_COMMAND_SCROLL_THUMBTRACK, self.on_slide)
        self.view.ax_interactive.figure.canvas.mpl_connect('button_press_event', self.evt_interactive_click)

        # Runtime
        self.selection_pts = []
        self.selecting = False
        self.update_state(self.STATE_NULL)
        self.n_updates = 0

        # Run
        #self.view.Show()
        self.app.MainLoop()

    def update_state(self, st=None):
        if st is not None:
            self.state = st

        if self.state == self.STATE_NULL:
            self.view.prepare_button.Enable()
            self.view.prepare_button.SetLabel('Prepare Session')
            self.view.add_sub_button.Enable()
            self.view.start_button.Disable()
            self.view.pause_button.Disable()
            self.view.update_sub_choices()
        elif self.state == self.STATE_PREPARED:
            self.view.usrinput_box.SetValue('(notes)')
            self.view.prepare_button.SetLabel('Cancel Session')
            self.view.prepare_button.Enable()
            self.view.add_sub_button.Disable()
            self.view.start_button.SetLabel("Run Session")
            self.view.start_button.SetBackgroundColour((0,255,0))
            self.view.start_button.Enable()
            self.view.pause_button.Disable()
        elif self.state == self.STATE_RUNNING:
            self.view.prepare_button.Disable()
            self.view.prepare_button.SetLabel('Prepare Session')
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
            self.view.prepare_button.SetLabel('Prepare Session')
            self.view.add_sub_button.Enable()
            self.view.start_button.Disable()
            self.view.pause_button.Disable()
            self.view.update_sub_choices()
    
    def update(self):
        if (not self.session.session_on) and self.state == self.STATE_RUNNING:
            self.update_state(self.STATE_RUN_COMPLETE)
            return

        # checks
        if self.view.trial_n_widg.GetValue() == str(self.session.trial_idx):
            new_trial_flag = False
        else:
            new_trial_flag = True

        # clocks
        self.view.session_runtime_widg.SetValue(pretty_time(self.session.session_runtime))
        self.view.trial_runtime_widg.SetValue(pretty_time(self.session.trial_runtime))

        # plots
        try:
            aq = self.session.ar.get_accum()
            self.view.set_live_data((None,aq), (None,self.session.eyelid_buffer))
        except Queue.Empty:
            pass

        # movie
        cam_frame = self.session.im
        #self.view.panel_mov.set_frame(cam_frame)
        self.mov_im.set_data(cam_frame)
        self.view.ax_interactive.figure.canvas.draw()
        
        # trial
        if new_trial_flag:
            self.update_trial()
            
        # past
        if self.session.past_flag != False:
            cs,us = self.session.past_flag
            self.session.past_flag = False
            self.view.set_past_data(self.session.eyelid_buffer_ts,self.session.eyelid_buffer,cs,us)

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
        
        self.n_updates += 1
        self.update_timer = wx.CallLater(self.REFRESH_INTERVAL, self.update)

    def update_trial(self):
        if self.session.trial_idx < 0:
            return
        self.view.trial_n_widg.SetValue("%s"%(str(self.session.trial_idx)))
        self.view.trial_type_widg.SetValue(self.session.current_stim_state)

    ####### EVENTS ########
    def evt_prepare(self, evt):
        if self.state == self.STATE_PREPARED:
            self.session.end()
            self.update_state(self.STATE_NULL)

        else:
            sel_sub = self.view.sub_box.GetSelection()
            if wx.NOT_FOUND in [sel_sub]:
                dlg = wx.MessageDialog(self.view, message='Selections not made.', caption='Preparation not performed.', style=wx.OK)
                res = dlg.ShowModal()
                dlg.Destroy()
                return

            sub_name = self.view.sub_names[sel_sub]
            imaging = self.view.imaging_box.GetValue()

            sub = Subject(sub_name)
            ph = ParamHandler(sub, imaging=imaging)
            self.session = Session(ph.params, ax_interactive=self.view.ax_interactive)

            # tcpip communication
            if imaging:
                si_path = config.si_data_path+r'\\{}'.format(sub_name)
                seshname = self.session.name_as_str()
                dic = dict(path=si_path, name=seshname, idx=1)
                cont = True
                while cont:
                    suc = self.tcpip.send(dic)
                    if not suc:
                        dlg = wx.MessageDialog(self.view, caption='ScanImage preparation failed.', message='Try again?', style=wx.YES_NO)
                        res = dlg.ShowModal()
                        dlg.Destroy()
                        cont = res==wx.ID_YES
                        if cont:
                            self.evt_tcpip(None)
                    else:
                        cont = False

            #self.view.setup_axlive()
            self.view.SetTitle('Subject {}'.format(sub_name))
            
            _,im = self.session.cam.get()
            self.view.ax_interactive.clear()
            self.view.ax_interactive.axis('off')
            self.mov_im = self.view.ax_interactive.imshow(im, cmap=pl.cm.Greys_r)

            self.update_state(self.STATE_PREPARED)
            self.update()
        
    def evt_tcpip(self, evt):
        bi = wx.BusyInfo('Connecting TCPIP; click connect on remote machine...', self.view)
        suc = self.tcpip.reconnect()
        bi.Destroy()
        if not suc:
            dlg = wx.MessageDialog(self.view, caption='TCPIP reconnection failed.', message='TCPIP not active.', style=wx.OK)
            res = dlg.ShowModal()
            dlg.Destroy()
        else:
            logging.info('TCPIP connected.')

    def evt_onoff(self, evt):
        if self.state != self.STATE_RUNNING:
            self.update_state(self.STATE_RUNNING)
            self.run_th = threading.Thread(target=self.session.run)
            self.run_th.start()
        elif self.state == self.STATE_RUNNING:
            self.session.session_kill = True
            self.update_state(self.STATE_KILLED_SESSION)

    def evt_pause(self, evt):
        if not self.session.paused:
            self.session.pause(True)
            self.view.pause_button.SetLabel('Unpause')
            self.view.pause_button.SetBackgroundColour((0,255,0))
            self.view.start_button.Disable()
        elif self.session.paused:
            self.session.pause(False)
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
                self.tcpip.end()
                self.view.Destroy()
            else:
                evt.Veto()

    def evt_addsub(self, evt):
        dlg = wx.TextEntryDialog(self.view, message='Enter new subject name:')
        ret = dlg.ShowModal()
        if ret == wx.ID_OK:
            self.view.add_sub(dlg.GetValue().strip().lower())
        else:
            pass

    def set_light(self, evt, state):
        if self.state in [self.STATE_PREPARED,self.STATE_RUNNING,self.STATE_KILLED_SESSION]:
            self.session.dummy_light(state)
        else:
            dummy_light(state)
    def evt_puff(self, evt):
        if self.state in [self.STATE_PREPARED,self.STATE_RUNNING,self.STATE_KILLED_SESSION]:
            self.session.dummy_puff()
        else:
            dummy_puff()
    def evt_deliver(self, evt):
        if self.state in [self.STATE_RUNNING]:
            self.session.deliver_override = True
            logging.info('Manual trial delivering.')
        else:
            logging.info('No session running to deliver trial.')
    def update_usrinput(self, evt):
        self.session.notes = self.view.usrinput_box.GetValue()
        logging.info('Metadata updated.')
    def evt_roi(self, evt):
        if self.state not in [self.STATE_PREPARED, self.STATE_RUNNING]:
            logging.info('No session for ROI selection.')
            return
            
        if not self.selecting:
            self.view.roi_but.SetLabel('DONE')
            im = self.session.im
            self.mov_im.set_data(im)
            self.view.ax_interactive.axis([0,im.shape[1],0,im.shape[0]])
            self.view.ax_interactive.figure.canvas.draw()
            logging.info('Select ROI now, and press DONE to stop.')
            self.selecting = True
        elif self.selecting:
            self.session.roi_pts = np.copy(self.selection_pts)
            self.session.acquire_mask()
            self.view.roi_but.SetLabel('ROI')
            self.selection_pts = []
            self.selecting = False
    def evt_resetcam(self, evt):
        if self.state in [self.STATE_PREPARED, self.STATE_RUNNING]:
            self.session.cam.reset_cams()
    def evt_interactive_click(self, event):
        if self.selecting:
            self.selection_pts.append((event.xdata, event.ydata))
            lims = self.view.ax_interactive.axis()
            self.view.ax_interactive.plot(event.xdata,event.ydata,'rx')
            self.view.ax_interactive.axis(lims)
            self.view.ax_interactive.figure.canvas.draw()
    def on_slide(self, evt):
        if self.state in [self.STATE_PREPARED, self.STATE_RUNNING]:
            self.session.eyelid_thresh = self.view.slider.GetValue()
        self.view.update_thresh()
