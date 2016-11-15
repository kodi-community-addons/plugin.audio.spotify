'''
Created on 06/05/2011

@author: mikel
'''

#Why the hell "import spotify" does not work?
# import xbmc
import uuid
from spotify import image as _image, link, session, SampleType, track as _track
from spotify.utils.loaders import load_track, load_image
import threading, time, StringIO, cherrypy, re, struct
from audio import QueueItem, BufferStoppedError
import cherrypy
from cherrypy import wsgiserver
from cherrypy.process import servers
import weakref
from datetime import datetime
import string, random
from utils import DynamicCallback

#TODO: urllib 3.x compatibility
import urllib2
from utils import NullLogHandler





class HTTPProxyError(Exception):
    pass



def format_http_date(dt):
    """
    As seen on SO, compatible with py2.4+:
    http://stackoverflow.com/questions/225086/rfc-1123-date-representation-in-python
    """
    """Return a string representation of a date according to RFC 1123
    (HTTP/1.1).

    The supplied date must be in UTC.

    """
    weekday = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][dt.weekday()]
    month = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep",
             "Oct", "Nov", "Dec"][dt.month - 1]
    return "%s, %02d %s %04d %02d:%02d:%02d GMT" % (weekday, dt.day, month,
        dt.year, dt.hour, dt.minute, dt.second)



def create_base_token(length=30):
    """
    Creates a random token with an optional length.
    Original from SO:
    http://stackoverflow.com/a/9011133/28581
    """
    return uuid.uuid4().hex

    # Below technique *can result in non-ascii characters which trigger downstream exceptions -- Above approach avoids this potential
    # pool = string.letters + string.digits
    # return ''.join(random.choice(pool) for i in xrange(length))



def create_user_token(base_token, user_agent):
    # xbmc.log("%s --> %s" %('Spotify PROXY', 'creating token ..'), xbmc.LOGNOTICE)
    # xbmc.log("%s --> %s" %('Spotify PROXY', base_token), xbmc.LOGNOTICE)
    # xbmc.log("%s --> %s" %('Spotify PROXY', user_agent), xbmc.LOGNOTICE)
    return sha1sum(str.join('', [base_token, user_agent]))



def sha1sum(data):
    #SHA1 lib 2.4 compatibility
    try:
        from hashlib import sha1
        hash_obj = sha1()
    except:
        import sha
        hash_obj = sha.new()

    hash_obj.update(data)
    return hash_obj.hexdigest()



class ImageCallbacks(_image.ImageCallbacks):
    __checker = None


    def __init__(self, checker):
        self.__checker = checker


    def image_loaded(self, image):
        self.__checker.check_conditions()



class Image:
    __session = None
    __last_modified = None


    def __init__(self, session):
        self.__session = session
        self.__last_modified = format_http_date(datetime.utcnow())


    def _get_clean_image_id(self, image_str):
        #Strip the optional extension...
        r = re.compile('\.jpg$', re.IGNORECASE)
        return re.sub(r, '', image_str)


    @cherrypy.expose
    def default(self, image_id, **kwargs):
        method = cherrypy.request.method.upper()

        #Fail for other methods than get or head
        if method not in ("GET", "HEAD"):
            raise cherrypy.HTTPError(405)

        clean_image_id = self._get_clean_image_id(image_id)
        img_obj = _image.create(self.__session, clean_image_id)
        load_image(img_obj, 10)

        #Fail if image was not loaded or wrong format
        if not img_obj.is_loaded() or img_obj.format() != _image.ImageFormat.JPEG:
            raise cherrypy.HTTPError(500)

        else:
            cherrypy.response.headers["Content-Type"] = "image/jpeg"
            cherrypy.response.headers["Content-Length"] = len(img_obj.data())
            cherrypy.response.headers["Last-Modified"] = self.__last_modified

            if method == 'GET':
                return img_obj.data()



class TrackLoadCallback(session.SessionCallbacks):
    __checker = None


    def __init__(self, checker):
        self.__checker = checker


    def metadata_updated(self, session):
        self.__checker.check_conditions()



class Track:
    __session = None
    __audio_buffer = None
    __is_playing = None
    __base_token = None
    __allowed_ips = None
    __allow_ranges = None


    def __init__(self, session, audio_buffer, base_token, allowed_ips, on_stream_ended, allow_ranges=True):
        self.__session = session
        self.__audio_buffer = audio_buffer
        self.__base_token = base_token
        self.__allowed_ips = allowed_ips
        self.__is_playing = False
        self.__cb_stream_ended = on_stream_ended
        self.__allow_ranges = allow_ranges


    def _get_track_object(self, track_str):

        #Strip the optional extension...
        r = re.compile('\.wav$', re.IGNORECASE)
        track_id = re.sub(r, '', track_str)

        #Try to parse as a track
        link_obj = link.create_from_string("spotify:track:%s" % track_id)
        if link_obj is not None:
            track_obj = link_obj.as_track()
            load_track(self.__session, track_obj)
            return track_obj

        #Try to parse as a local track
        link_obj = link.create_from_string("spotify:local:%s" % track_id)
        if link_obj is not None:
            track_obj = link_obj.as_track()
            load_track(self.__session, track_obj)
            return track_obj

        #Fail if we reach this point
        raise cherrypy.HTTPError(404)


    def _write_wave_header(self, numsamples, channels, samplerate, bitspersample):
        file = StringIO.StringIO()

        #Generate format chunk
        format_chunk_spec = "<4sLHHLLHH"
        format_chunk = struct.pack(
            format_chunk_spec,
            "fmt ", #Chunk id
            16, #Size of this chunk (excluding chunk id and this field)
            1, #Audio format, 1 for PCM
            channels, #Number of channels
            samplerate, #Samplerate, 44100, 48000, etc.
            samplerate * channels * (bitspersample / 8), #Byterate
            channels * (bitspersample / 8), #Blockalign
            bitspersample, #16 bits for two byte samples, etc.
        )

        #Generate data chunk
        data_chunk_spec = "<4sL"
        datasize = numsamples * channels * (bitspersample / 8)
        data_chunk = struct.pack(
            data_chunk_spec,
            "data", #Chunk id
            int(datasize), #Chunk size (excluding chunk id and this field)
        )

        sum_items = [
            #"WAVE" string following size field
            4,

            #"fmt " + chunk size field + chunk size
            struct.calcsize(format_chunk_spec),

            #Size of data chunk spec + data size
            struct.calcsize(data_chunk_spec) + datasize
        ]

        #Generate main header
        all_cunks_size = int(sum(sum_items))
        main_header_spec = "<4sL4s"
        main_header = struct.pack(
            main_header_spec,
            "RIFF",
            all_cunks_size,
            "WAVE"
        )

        #Write all the contents in
        file.write(main_header)
        file.write(format_chunk)
        file.write(data_chunk)

        return file.getvalue(), all_cunks_size + 8


    def _get_sample_width(self, sample_type):
        if sample_type == SampleType.Int16NativeEndian:
            return 16

        else:
            return -1


    def _get_total_samples(self, frame, track):
        return frame.sample_rate * track.duration() / 1000


    def _generate_file_header(self, frame, num_samples):
        #Build the whole header
        return self._write_wave_header(
            num_samples, frame.num_channels, frame.sample_rate,
            self._get_sample_width(frame.sample_type)
        )


    def _write_file_content(self, buf, filesize, wave_header=None, max_buffer_size=65535):

        #Initialize some loop vars
        output_buffer = StringIO.StringIO()
        bytes_written = 0
        has_frames = True
        frame_num = 0

        #Write wave header
        if wave_header is not None:
            output_buffer.write(wave_header)
            bytes_written = output_buffer.tell()
            yield wave_header
            output_buffer.truncate(0)

        #Loop there's something to output
        while has_frames:

            try:
                frame, has_frames = buf.get_frame_wait(frame_num)

                #Check if this frame fits in the estimated calculation
                if bytes_written + len(frame.data) < filesize:
                    output_buffer.write(frame.data)
                    bytes_written += len(frame.data)

                #Does not fit, we need to truncate the frame data
                else:
                    truncate_size = filesize - bytes_written
                    output_buffer.write(frame.data[:truncate_size])
                    bytes_written = filesize
                    has_frames = False

                #Update counters
                frame_num += 1

            except BufferStoppedError:

                #Handle gracefully a buffer cancellation
                has_frames = False

            finally:

                #Check if the current buffer needs to be flushed
                if not has_frames or output_buffer.tell() > max_buffer_size:
                    yield output_buffer.getvalue()
                    output_buffer.truncate(0)

        #Add some silence padding until the end is reached (if needed)
        while bytes_written < filesize:

            #The buffer size fits into the file size
            if bytes_written + max_buffer_size < filesize:
                yield '\0' * max_buffer_size
                bytes_written += max_buffer_size

            #Does not fit, just generate the remaining bytes
            else:
                yield '\0' * (filesize - bytes_written)
                bytes_written = filesize

        #Notify that the stream ended
        self.__cb_stream_ended()


    def _check_request(self):
        method = cherrypy.request.method.upper()
        headers = cherrypy.request.headers

        #Fail for other methods than get or head
        if method not in ("GET", "HEAD"):
            raise cherrypy.HTTPError(405)

        #Error if no token or user agent are provided
        if 'User-Agent' not in headers or 'x-csrf-token' not in headers:
            raise cherrypy.HTTPError(403)

        #Error if the requester is not allowed
        if headers['Remote-Addr'] not in self.__allowed_ips:
            raise cherrypy.HTTPError(403)

        #Check that the supplied token is correct
        user_token = headers['x-csrf-token']
        user_agent = headers['User-Agent']
        correct_token = create_user_token(self.__base_token, user_agent)
        if user_token != correct_token:
            raise cherrypy.HTTPError(403)

        #we do not accept range requests
        if headers.get('Range','') and headers.get('Range','') != "bytes=0-":
            raise cherrypy.HTTPError(416)

        return method


    def _write_http_headers(self, filesize):
        cherrypy.response.headers['Content-Type'] = 'audio/x-wav'
        cherrypy.response.headers['Content-Length'] = filesize
        cherrypy.response.headers['Accept-Ranges'] = 'none'


    def _create_dummy_frame(self):
        """
        Create a dummy frame with default format.
        """
        return QueueItem(
            '',
            1,
            SampleType.Int16NativeEndian,
            44100,
            2,
            1.0 / 44100,
        )


    def _check_track(self, track):
        """
        Check if the track is playable or not.
        """
        ta = track.get_availability(self.__session)
        if ta != _track.TrackAvailability.Available:
            raise cherrypy.HTTPError(403)


    @cherrypy.expose
    def default(self, track_id, **kwargs):
        #Check sanity of the request
        self._check_request()

        #Get the object represented by the id
        track_obj = self._get_track_object(track_id)

        #Check if it's playable, to avoid opening a useless buffer
        self._check_track(track_obj)

        #Get the first frame of the track
        if cherrypy.request.method.upper() == 'GET':
            buf = self.__audio_buffer.open(self.__session, track_obj)
            frame = buf.get_frame_wait(0)[0]

        #Or just create a fake one
        else:
            frame = self._create_dummy_frame()

        #Calculate the total number of samples in the track
        num_samples = self._get_total_samples(frame, track_obj)

        #Calculate file size, and obtain the header
        file_header, filesize = self._generate_file_header(frame, num_samples)

        self._write_http_headers(filesize)

        #If method was GET, write the file content
        if cherrypy.request.method.upper() == 'GET':
            return self._write_file_content(buf, filesize, file_header)

    default._cp_config = {'response.stream': True}



class Root:
    __session = None

    image = None
    track = None


    def __init__(self, session, audio_buffer, base_token, allowed_ips, on_stream_ended, allow_ranges=True):
        self.__session = session
        self.image = Image(session)
        self.track = Track(
            session, audio_buffer, base_token, allowed_ips, on_stream_ended, allow_ranges
        )


    def cleanup(self):
        self.__session = None
        self.image = None
        self.track = None



class ProxyRunner(threading.Thread):
    __server = None
    __audio_buffer = None
    __base_token = None
    __allowed_ips = None
    __cb_stream_ended = None
    __root = None


    def _find_free_port(self, host, port_list):
        for port in port_list:
            try:
                servers.check_port(host, port, .1)
                return port
            except:
                pass

        list_str = ','.join([str(item) for item in port_list])
        raise HTTPProxyError("Cannot find a free port. Tried: %s" % list_str)


    def __init__(self, session, audio_buffer, host='localhost', try_ports=range(8090,8100), allowed_ips=['127.0.0.1'], allow_ranges=True):
        port = self._find_free_port(host, try_ports)
        self.__audio_buffer = audio_buffer
        sess_ref = weakref.proxy(session)
        self.__base_token = create_base_token()
        self.__allowed_ips = allowed_ips
        self.__cb_stream_ended = DynamicCallback()
        self.__root = Root(
            sess_ref, audio_buffer, self.__base_token, self.__allowed_ips,
            self.__cb_stream_ended, allow_ranges
        )
        app = cherrypy.tree.mount(self.__root, '/')

        #Don't log to the screen by default
        log = cherrypy.log
        log.access_file = ''
        log.error_file = ''
        log.screen = False
        log.access_log.addHandler(NullLogHandler())
        log.error_log.addHandler(NullLogHandler())

        self.__server = wsgiserver.CherryPyWSGIServer((host, port), app)
        threading.Thread.__init__(self)


    def set_stream_end_callback(self, callback):
        self.__cb_stream_ended.set_callback(callback)


    def clear_stream_end_callback(self):
        self.__cb_stream_ended.clear_callback();


    def run(self):
        self.__server.start()


    def get_port(self):
        return self.__server.bind_addr[1]


    def get_host(self):
        return self.__server.bind_addr[0]


    def get_user_token(self, user_agent):
        return create_user_token(self.__base_token, user_agent)


    def ready_wait(self):
        while not self.__server.ready:
            time.sleep(.1)


    def stop(self):
        self.__audio_buffer.stop()
        self.__server.stop()
        self.join(10)
        self.__root.cleanup()
