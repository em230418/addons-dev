import cv2
import time
import threading
import logging
import threading

try:
    from greenlet import getcurrent as get_ident
except ImportError:
    try:
        from thread import get_ident
    except ImportError:
        from _thread import get_ident

_logger = logging.getLogger(__name__)

INACTIVITY_TIME_SECONDS = 10

class InvalidRecordingId(Exception):
    pass

class RecordingIdAlreadyExists(Exception):
    pass

class CameraEvent(object):
    """An Event-like class that signals all active clients when a new frame is
    available.
    """
    def __init__(self):
        self.events = {}

    def wait(self):
        """Invoked from each client's thread to wait for the next frame."""
        ident = get_ident()
        if ident not in self.events:
            # this is a new client
            # add an entry for it in the self.events dict
            # each entry has two elements, a threading.Event() and a timestamp
            self.events[ident] = [threading.Event(), time.time()]
        return self.events[ident][0].wait()

    def set(self):
        """Invoked by the camera thread when a new frame is available."""
        now = time.time()
        remove = None
        for ident, event in self.events.items():
            if not event[0].isSet():
                # if this client's event is not set, then set it
                # also update the last set timestamp to now
                event[0].set()
                event[1] = now
            else:
                # if the client's event is already set, it means the client
                # did not process a previous frame
                # if the event stays set for more than 5 seconds, then assume
                # the client is gone and remove it
                if now - event[1] > 5:
                    remove = ident
        if remove:
            del self.events[remove]

    def clear(self):
        """Invoked from each client's thread after a frame was processed."""
        self.events[get_ident()][0].clear()


class Camera(object):
    instances = {}

    def __new__(cls, uri):
        if uri not in cls.instances:
            _logger.debug("Creating new instance for {}".format(uri))
            cls.instances[uri] = object.__new__(cls)
        else:
            _logger.debug("Using created instance for {}".format(uri))
        return cls.instances[uri]
        
    def __init__(self, uri):
        self.last_access = time.time()

        if getattr(self, "uri", None):
            # No need to run __init__ for already existing instance
            # the only thing we need - make sure that thread exists
            self._start_thread()
            return

        self.uri = uri
        self.event = CameraEvent()
        self.frame = None
        self.thread = None

        self.video_width = None
        self.video_height = None
        self.video_fps = None

        # TODO: rename to frame_callbacks
        self.recording_callbacks = {}

        self.record_ids_requested_to_stop_lock = threading.Lock()
        self.record_ids_requested_to_stop = []

        # start background frame thread
        self._start_thread()

    def _start_thread(self):
        if not self.thread:
            self.thread = threading.Thread(target=self._thread)
            self.thread.start()

    def prepare(self):
        # wait until frames are available
        while self.get_frame() is None:
            time.sleep(0)

    def get_frame(self):
        """Return the current camera frame."""
        self.last_access = time.time()

        # wait for a signal from the camera thread
        self.event.wait()
        self.event.clear()

        return self.frame

    def _thread(self):
        """Camera background thread."""
        _logger.debug('Starting camera thread.')
        frames_iterator = self.frames()
        for frame, img in frames_iterator:
            self.frame = frame
            self.event.set()  # send signal to clients
            time.sleep(0)

            # if anything is recording
            if self.recording_callbacks:
                self.last_access = time.time()

                # stoping recording due user request, if required
                with self.record_ids_requested_to_stop_lock:
                    if self.record_ids_requested_to_stop:
                        _logger.debug("Stopped recording {} due to user request".format(
                            ', '.join(map(lambda r: "#{}".format(r), self.record_ids_requested_to_stop))
                        ))
                    self._clean_up_stopped_recording(self.record_ids_requested_to_stop)
                    self.record_ids_requested_to_stop.clear()

                record_ids_to_stop = []
                for record_id, (on_frame_callback, _) in self.recording_callbacks.items():
                    try:
                        callback_result = on_frame_callback(record_id, img)
                        if callback_result is not None and not callback_result:
                            _logger.debug("Stopped recording #{} due to callback result".format(record_id))
                            record_ids_to_stop.append(record_id)
                    except Exception:
                        record_ids_to_stop.append(record_id)
                        _logger.exception("Stopped recording #{} due to exception".format(record_id))

                self._clean_up_stopped_recording(record_ids_to_stop)
                
            # if there hasn't been any clients asking for frames in
            # the last INACTIVITY_TIME_SECONDS then stop the thread
            if time.time() - self.last_access > INACTIVITY_TIME_SECONDS:
                frames_iterator.close()
                _logger.debug('Stopping camera thread due to inactivity.')
                break
        self.thread = None

    @staticmethod
    def unlink(uri):
        # TODO: destroy threads (it will also stop recording)
        # TODO: use __del__ maybe?
        del cls.instances[uri]

    def frames(self):
        camera = cv2.VideoCapture(self.uri)
        if not camera.isOpened():
            # TODO: return picture
            _logger.error("Could not start camera {}".format(self.uri))
            return

        self.video_width = int(camera.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.video_height = int(camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.video_fps = int(camera.get(cv2.CAP_PROP_FPS))
                                
        while True:
            # read current frame
            _, img = camera.read()

            # encode as a jpeg image and return it
            frame = cv2.imencode('.jpg', img)[1].tobytes()
            yield frame, img

    def is_recording(self, record_id):
        if not record_id:
            raise InvalidRecordingId(record_id)

        return record_id in self.recording_callbacks

    # TODO: do we need on_stop_callback?
    def start_recording(self, record_id, on_start_callback, on_frame_callback, on_finish_callback):
        if not record_id:
            raise InvalidRecordingId(record_id)
        
        if record_id in self.recording_callbacks:
            raise RecordingIdAlreadyExists(record_id)

        try:
            on_start_callback(record_id, self.video_width, self.video_height, self.video_fps)
            self.recording_callbacks[record_id] = on_frame_callback, on_finish_callback
            _logger.debug("Started recording #{}...".format(record_id))
        except:
            _logger.exception("Failed to start recording #{}".format(record_id))
            

    def stop_recording(self, record_id):
        if not self.is_recording(record_id):
            return False

        with self.record_ids_requested_to_stop_lock:
            self.record_ids_requested_to_stop.append(record_id)

        # wait until callback is removed
        # bad, but not ugly
        # https://blog.miguelgrinberg.com/post/how-to-make-python-wait
        while self.recording_callbacks.get(record_id) is not None:
            time.sleep(1)

        return True

    def _clean_up_stopped_recording(self, record_ids):
        for record_id in record_ids:
            try:
                on_finish_callback = self.recording_callbacks[record_id][1]
                on_finish_callback(record_id)
            except Exception:
                _logger.exception("Error while executing on_finish_callback for #{}".format(record_id))

            try:
                del self.recording_callbacks[record_id]
            except KeyError:
                pass
