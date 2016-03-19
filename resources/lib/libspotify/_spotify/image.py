import ctypes

#Import handy globals
from _spotify import LibSpotifyInterface, callback, bool_type


#Callbacks
image_loaded_cb = callback(None, ctypes.c_void_p, ctypes.c_void_p)



class ImageInterface(LibSpotifyInterface):
    def __init__(self):
        LibSpotifyInterface.__init__(self)


    def create(self, *args):
        return self._get_func(
            'sp_image_create',
            ctypes.c_void_p,
            ctypes.c_void_p, ctypes.c_char * 20
        )(*args)


    def create_from_link(self, *args):
        return self._get_func(
            'sp_image_create_from_link',
            ctypes.c_void_p,
            ctypes.c_void_p, ctypes.c_void_p
        )(*args)


    def add_load_callback(self, *args):
        return self._get_func(
            'sp_image_add_load_callback',
            ctypes.c_int,
            ctypes.c_void_p, image_loaded_cb, ctypes.c_void_p
        )(*args)


    def remove_load_callback(self, *args):
        return self._get_func(
            'sp_image_remove_load_callback',
            ctypes.c_int,
            ctypes.c_void_p, image_loaded_cb, ctypes.c_void_p
        )(*args)


    def is_loaded(self, *args):
        return self._get_func(
            'sp_image_is_loaded',
            bool_type,
            ctypes.c_void_p
        )(*args)


    def error(self, *args):
        return self._get_func(
            'sp_image_error',
            ctypes.c_int,
            ctypes.c_void_p
        )(*args)


    def format(self, *args):
        return self._get_func(
            'sp_image_format',
            ctypes.c_int,
            ctypes.c_void_p
        )(*args)


    def data(self, *args):
        return self._get_func(
            'sp_image_data',
            ctypes.c_void_p,
            ctypes.c_void_p, ctypes.POINTER(ctypes.c_size_t)
        )(*args)


    def image_id(self, *args):
        return self._get_func(
            'sp_image_image_id',
            ctypes.POINTER(ctypes.c_byte),
            ctypes.c_void_p
        )(*args)


    def add_ref(self, *args):
        return self._get_func(
            'sp_image_add_ref',
            ctypes.c_int,
            ctypes.c_void_p
        )(*args)


    def release(self, *args):
        return self._get_func(
            'sp_image_release',
            ctypes.c_int,
            ctypes.c_void_p
        )(*args)
