try:
	import winsound
except:
	winsound = None
import threading

ERROR,POP,LASER,INTRO,BUZZ = 0,1,2,3,4
def sounds(s):
   return 'media/'+str(s)+'.wav'

class Speaker(object):
    def __init__(self, saver=None):
        self.playing = []
        self.saver = saver
        self.event = threading.Event()
    def _play(self, filename):
        if self.event.is_set():
            return
        else:
            self.event.set()

            if self.saver:
                self.saver.write('speaker', dict(filename=filename))

            if winsound != None:
                winsound.PlaySound(sounds(filename), winsound.SND_FILENAME)

            self.event.clear()
    def error(self):
        threading.Thread(target=self._play, args=(ERROR,)).start()
    def pop(self):
        threading.Thread(target=self._play, args=(POP,)).start()
    def laser(self):
        threading.Thread(target=self._play, args=(LASER,)).start()
    def intro(self):
        threading.Thread(target=self._play, args=(INTRO,)).start()
    def wrong(self):
        threading.Thread(target=self._play, args=(BUZZ,)).start()
