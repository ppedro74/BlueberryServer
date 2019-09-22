import sys
import threading
import logging
import os
import datetime
import time
import pyaudio
import wave
import json
import AudioPlayerController
import contextlib

class PyAudioPlayerController(AudioPlayerController.AudioPlayerController):
    AUDIO_SAMPLE_BITRATE = 14700

    def __init__(self, log_level, save_audio_streams=False):
        super().__init__("PyAudioPlayerController", log_level)
        self.audio_stream = None
        self.audio_data = bytearray()
        self.lock = threading.Lock()
        self.wave = None
        self.wave_file = None
        if save_audio_streams:
            self.wave_file_prefix = os.path.join(os.getcwd(), "test-")
            self.logger.debug("wave_file_prefix=%s", self.wave_file_prefix)
        else:
            self.wave_file_prefix = None

    def play_audio_callback(self, in_data, frame_count, time_info, status):
        #    data = bytes([0] * frame_count * 1 * 1)

        self.lock.acquire()
        try:
            if len(self.audio_data)>=frame_count:
                data = self.audio_data[:frame_count]
                self.audio_data = self.audio_data[frame_count:]
                missing = 0
            else:
                data = self.audio_data
                self.audio_data = bytearray()
                missing = frame_count - len(data)
                data += bytes([0] * missing)
        
            if missing>0:
                self.logger.warning("callback frame_count:%s missing:%s status:%s data_len:%s", frame_count, missing, status, len(data))
            else:
                self.logger.debug("callback frame_count:%s status:%s data_len:%s", frame_count, status, len(data))

        finally:
            self.lock.release()

        self.logger.debug("callback frame_count:%s status:%s audio_data_len:%s", frame_count, status, len(self.audio_data))

        return (bytes(data), pyaudio.paContinue)

    def stop(self):
        self.audio_stream.close()
        self.py_audio.terminate()

    @contextlib.contextmanager
    def start(self, hide_debug_output = True):
        if hide_debug_output:
            #devnull = os.open(os.devnull, os.O_WRONLY)
            #old_stdout = os.dup(1)
            #sys.stdout.flush()
            #os.dup2(devnull, 1)
            #os.close(devnull)
            devnull = os.open(os.devnull, os.O_WRONLY)
            old_stderr = os.dup(2)
            sys.stderr.flush()
            os.dup2(devnull, 2)
            os.close(devnull)

        try:
            self.py_audio = pyaudio.PyAudio()

            self.audio_stream = self.py_audio.open(format=pyaudio.paUInt8,
                            channels=1,
                            rate=self.AUDIO_SAMPLE_BITRATE,
                            output=True,
                            stream_callback=self.play_audio_callback,
                            start=False)
        finally:
            if hide_debug_output:
                #os.dup2(old_stdout, 1)
                #os.close(old_stdout)
                os.dup2(old_stderr, 2)
                os.close(old_stderr)

    def stream_init(self):
        self.lock.acquire()
        try:
            self.audio_data = bytearray()
        finally:
            self.lock.release()
        if self.wave_file_prefix is not None:
            self.wave_file = self.wave_file_prefix + str(int(datetime.datetime.now().timestamp())) + ".wav";
            self.logger.debug("init creating wav file=%s", self.wave_file)
            self.wave = wave.open(self.wave_file, "wb")
            self.wave.setnchannels(1)
            self.wave.setsampwidth(1)
            self.wave.setframerate(self.AUDIO_SAMPLE_BITRATE)

    def stream_stop(self):
        if self.wave_file is not None:
            self.logger.debug("stop closing wav file=%s", self.wave_file)
            self.wave.close()
            self.wave = None
            self.wave_file = None
        if self.audio_stream.is_active():
            self.logger.debug("stop stopping audio stream")
            self.audio_stream.stop_stream()

    def stream_load(self, data):
        if self.wave is not None:
            self.wave.writeframes(bytes(data))

        debug_len1 = 0
        debug_len2 = 0
        self.lock.acquire()
        try:
            self.audio_data += data
            debug_len1 = len(data)
            debug_len2 = len(self.audio_data)
        finally:
            self.lock.release()

        self.logger.debug("load len=%s total=%s", debug_len1, debug_len2)

    def stream_play(self):
        self.logger.debug("play starting audio stream")
        self.audio_stream.start_stream()


def list_output_devices():
    p = pyaudio.PyAudio()
    for i in range(p.get_device_count()):
        info = p.get_device_info_by_index(i)
        info_json = json.dumps(info, sort_keys=True, indent=4)
        logging.info(info_json)
    p.terminate()

def play_file(fname):
    wf = wave.open(fname, 'rb')
    p = pyaudio.PyAudio()
    chunk = 1024
    logging.info("play file:%s sampleWidth:%s #channels:%s framerate:%s", fname, wf.getsampwidth(), wf.getnchannels(), wf.getframerate())
    stream = p.open(format=p.get_format_from_width(wf.getsampwidth()),
                    channels=wf.getnchannels(),
                    rate=wf.getframerate(),
                    output=True)
    data = wf.readframes(chunk)
    while data != b'':
        stream.write(data)
        data = wf.readframes(chunk)
    stream.close()
    p.terminate() 

if __name__ == "__main__":
    logging.basicConfig(format="%(process)d-%(levelname)s-%(message)s", level=logging.DEBUG)
    logging.info("Starting... platform=%s", sys.platform)
    os.environ["PA_ALSA_PLUGHW"] = "1"
    list_output_devices()
    #play_file("/usr/share/sounds/alsa/Front_Left.wav")
    #play_file("/usr/share/sounds/alsa/Front_Right.wav")
    play_file("./assets/test-01.wav")

