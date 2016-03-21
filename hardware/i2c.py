
class I2C(pydaq.Task):
    def __init__(self, device='Dev1', port=0, clk_line=2, dat_line=3, output_rate=1e6, buf_size=2048):
        
        pydaq.Task.__init__(self)
        self.buf_size = 2048
        port_address = '/'.join([device, 'port{}'.format(port)])
        clk_address = '/'.join([port_address, 'line{}'.format(clk_line)])
        dat_address = '/'.join([port_address, 'line{}'.format(dat_line)])

        self.CreateDOChan(clk_address, 'clk', pydaq.DAQmx_Val_ChanPerLine)
        self.CreateDOChan(dat_address, 'dat', pydaq.DAQmx_Val_ChanPerLine)
        self.CfgSampClkTiming('', output_rate, pydaq.DAQmx_Val_Rising, pydaq.DAQmx_Val_FiniteSamps, 1)

        #sue ann:
      DAQmxErrChk( "nidaqI2C:sendclock"    , DAQmxCreateTask("counter", &sendClock) );
      sprintf(channel, "Dev%d/ctr%d", device, sendCounter);
      DAQmxErrChk( "nidaqI2C:counter"      ,  DAQmxCreateCOPulseChanTicks ( sendClock
                                                                          , channel, "", timebase
                                                                          , DAQmx_Val_Low, 0, halfPeriod, halfPeriod
                                                                          ) );
      DAQmxErrChk( "nidaqI2C:countercfg"   , DAQmxCfgImplicitTiming(sendClock, DAQmx_Val_ContSamps, 1) );


      // TASK :  Digital communications task
      DAQmxErrChk( "nidaqI2C:sendtask"     , DAQmxCreateTask("send", &sendTask) );

      //         Use CLK and DTA lines for output
      sprintf(channel                       , "Dev%d/port%d/line%d", device, port, sCLKline);
      DAQmxErrChk( "nidaqI2C:sendCLK"      , DAQmxCreateDOChan(sendTask, channel, "CLK", DAQmx_Val_ChanPerLine));
      sprintf(channel                       , "Dev%d/port%d/line%d", device, port, sDTAline);
      DAQmxErrChk( "nidaqI2C:sendDTA"      , DAQmxCreateDOChan(sendTask, channel, "DTA", DAQmx_Val_ChanPerLine));

      //         Use sample clock to time digital output
      sprintf(channel                       , "/Dev%d/Ctr%dInternalOutput", device, sendCounter);
      DAQmxErrChk( "nidaqI2C:sendsampling" , DAQmxCfgSampClkTiming(sendTask, channel, dataRate, DAQmx_Val_Rising, DAQmx_Val_FiniteSamps, BUFFER_SEND) );

      //         Use onboard circular buffer and transfer data when half empty
      //DAQmxErrChk( "nidaqI2C:sendregen"    , DAQmxSetWriteRegenMode(sendTask, DAQmx_Val_AllowRegen) );
      DAQmxErrChk( "nidaqI2C:sendregen"    , DAQmxSetWriteRegenMode(sendTask, DAQmx_Val_DoNotAllowRegen) );
      DAQmxErrChk( "nidaqI2C:sendxfer"     , DAQmxSetDODataXferReqCond(sendTask, "", DAQmx_Val_OnBrdMemHalfFullOrLess) ); 

      //         Configure length of RAM buffer
      DAQmxErrChk( "nidaqI2C:outbuffer"    , DAQmxCfgOutputBuffer(sendTask, BUFFER_SEND) );

      //         This task should be committed to improve performance in software restart
      DAQmxErrChk( "nidaqI2C:sendcommit"   , DAQmxTaskControl(sendTask, DAQmx_Val_Task_Commit) );

    def send(self, msg):
        n = len(msg)

        self.abort()
        self.set('sampQuantSampPerChan', n)
        hI2CTask.set('bufOutputBufSize', n)
        self.WriteDigitalLines( self.buf_size, True, 0, pydaq.DAQmx_Val_GroupByChannel, msg, None, None )
        hI2CTask.start();
        self.WaitUntilTaskDone(1)
        self.StopTask()
        hI2CTask.control('DAQmx_Val_Task_Unreserve');

    def release(self):
        try:
            self.StopTask()
            self.ClearTask()
        except:
            pass


