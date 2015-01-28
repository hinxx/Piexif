import copy
import io
import os
import struct
import sys
import unittest

from PIL import Image
import piexif
from piexif import _common

ZerothIFD = piexif.ZerothIFD
ExifIFD = piexif.ExifIFD
GPSIFD = piexif.GPSIFD

print("piexif version: {0}".format(piexif.VERSION))


INPUT_FILE1 = os.path.join("tests", "images", "01.jpg")
INPUT_FILE2 = os.path.join("tests", "images", "02.jpg")
INPUT_FILE_LE1 = os.path.join("tests", "images", "L01.jpg")
NOEXIF_FILE = os.path.join("tests", "images", "noexif.jpg")
# JPEG without APP0 and APP1 segments
NOAPP01_FILE = os.path.join("tests", "images", "noapp01.jpg")
INPUT_FILE_TIF = os.path.join("tests", "images", "01.tif")


with open(INPUT_FILE1, "rb") as f:
    I1 = f.read()
with open(INPUT_FILE2, "rb") as f:
    I2 = f.read()


ZEROTH_DICT = {ZerothIFD.Software: u"PIL", # ascii
               ZerothIFD.Make: u"Make", # ascii
               ZerothIFD.Model: u"XXX-XXX", # ascii
               ZerothIFD.ResolutionUnit: 65535, # short
               ZerothIFD.BitsPerSample: (24, 24, 24), # short * 3
               ZerothIFD.JPEGInterchangeFormatLength: 4294967295, # long
               ZerothIFD.XResolution: (4294967295, 1), # rational
               ZerothIFD.BlackLevelDeltaH: ((1, 1), (1, 1), (1, 1)),  # srational
               }


EXIF_DICT = {ExifIFD.DateTimeOriginal: u"2099:09:29 10:10:10", # ascii
             ExifIFD.LensMake: u"LensMake", # ascii
             ExifIFD.OECF: b"\xaa\xaa\xaa\xaa\xaa\xaa",  # undefined
             ExifIFD.Sharpness: 65535, # short
             ExifIFD.ISOSpeed: 4294967295, # long
             ExifIFD.ExposureTime: (4294967295, 1), # rational
             ExifIFD.LensSpecification: ((1, 1), (1, 1), (1, 1), (1, 1)),
             ExifIFD.ExposureBiasValue: (2147483647, -2147483648), # srational
             }


GPS_DICT = {GPSIFD.GPSVersionID: (0, 0, 0, 1), # byte
            GPSIFD.GPSAltitudeRef: 1, # byte
            GPSIFD.GPSDateStamp: u"1999:99:99 99:99:99", # ascii
            GPSIFD.GPSDifferential: 65535, # short
            GPSIFD.GPSLatitude: (4294967295, 1), # rational
            }


def load_exif_by_PIL(f):
    i = Image.open(f)
    e = i._getexif()
    i.close()
    return e


def pack_byte(*args):
    return struct.pack("B" * len(args), *args)


class ExifTests(unittest.TestCase):
    def test_merge_segments(self):
        # Remove APP0, when both APP0 and APP1 exists.
        with open(INPUT_FILE1, "rb") as f:
            original = f.read()
        segments = _common.split_into_segments(original)
        new_data = _common.merge_segments(segments)
        segments = _common.split_into_segments(new_data)
        self.assertFalse([1][0:2] == b"\xff\xe0"
                        and segments[2][0:2] == b"\xff\xe1")
        self.assertEqual(segments[1][0:2], b"\xff\xe1")
        o = io.BytesIO(new_data)
        without_app0 = o.getvalue()
        Image.open(o).close()

        exif = _common.get_app1(segments)

        # Remove APP1, when second 'merged_segments' arguments is None
        # and no APP0.
        segments = _common.split_into_segments(without_app0)
        new_data = _common.merge_segments(segments, None)
        segments = _common.split_into_segments(new_data)
        self.assertNotEqual(segments[1][0:2], b"\xff\xe0")
        self.assertNotEqual(segments[1][0:2], b"\xff\xe1")
        self.assertNotEqual(segments[2][0:2], b"\xff\xe1")
        o = io.BytesIO(new_data)
        Image.open(o).close()

        # Insert exif to jpeg that has APP0 and APP1.
        o = io.BytesIO()
        i = Image.new("RGBA", (8, 8))
        i.save(o, format="jpeg", exif=exif)
        o.seek(0)
        segments = _common.split_into_segments(o.getvalue())
        new_data = _common.merge_segments(segments, exif)
        segments = _common.split_into_segments(new_data)
        self.assertFalse(segments[1][0:2] == b"\xff\xe0"
                         and segments[2][0:2] == b"\xff\xe1")
        self.assertEqual(segments[1], exif)
        o = io.BytesIO(new_data)
        Image.open(o).close()

        # Insert exif to jpeg that doesn't have APP0 and APP1.
        with open(NOAPP01_FILE, "rb") as f:
            original = f.read()
        segments = _common.split_into_segments(original)
        new_data = _common.merge_segments(segments, exif)
        segments = _common.split_into_segments(new_data)
        self.assertEqual(segments[1][0:2], b"\xff\xe1")
        o = io.BytesIO(new_data)
        Image.open(o).close()

        # Remove APP1, when second 'merged_segments' arguments is None
        # and APP1 exists.
        with open(INPUT_FILE1, "rb") as f:
            original = f.read()
        segments = _common.split_into_segments(original)
        new_data = _common.merge_segments(segments, None)
        segments = _common.split_into_segments(new_data)
        self.assertNotEqual(segments[1][0:2], b"\xff\xe1")
        self.assertNotEqual(segments[2][0:2], b"\xff\xe1")
        o = io.BytesIO(new_data)
        Image.open(o).close()

    def test_no_exif_load(self):
        z, e, g = piexif.load(NOEXIF_FILE)
        self.assertDictEqual(z, {})
        self.assertDictEqual(e, {})
        self.assertDictEqual(g, {})

    def test_no_exif_dump(self):
        o = io.BytesIO()
        exif_bytes = piexif.dump({}, {}, {})
        i = Image.new("RGBA", (8, 8))
        i.save(o, format="jpeg", exif=exif_bytes)
        o.seek(0)
        exif = load_exif_by_PIL(o)
        self.assertDictEqual({},  exif)

    def test_transplant(self):
        piexif.transplant(INPUT_FILE1, INPUT_FILE2, "transplant.jpg")
        i = Image.open("transplant.jpg")
        i.close()
        exif_src = piexif.load(INPUT_FILE1)
        img_src = piexif.load(INPUT_FILE2)
        generated = piexif.load("transplant.jpg")
        self.assertEqual(exif_src, generated)
        self.assertNotEqual(img_src, generated)

        piexif.transplant(INPUT_FILE1, "transplant.jpg")
        self.assertEqual(piexif.load(INPUT_FILE1), piexif.load("transplant.jpg"))

        with  self.assertRaises(ValueError):
            piexif.transplant(NOEXIF_FILE, INPUT_FILE2, "foo.jpg")

    def test_transplant2(self):
        """'transplant' on memory.
        """
        o = io.BytesIO()
        piexif.transplant(I1, I2, o)
        self.assertEqual(piexif.load(I1), piexif.load(o.getvalue()))
        i = Image.open(o).close()

    def test_remove(self):
        piexif.remove(INPUT_FILE1, "remove.jpg")
        exif = piexif.load("remove.jpg")[0]
        self.assertEqual(exif, {})
        exif = load_exif_by_PIL("remove.jpg")
        piexif.remove("remove.jpg")

    def test_remove2(self):
        """'remove' on memory.
        """
        o = io.BytesIO()
        with  self.assertRaises(ValueError):
            piexif.remove(I1)
        piexif.remove(I1, o)
        exif = piexif.load(o.getvalue())
        self.assertEqual(exif, ({}, {}, {}))
        exif = load_exif_by_PIL(o)

    def test_load(self):
        zeroth_dict, exif_dict, gps_dict = piexif.load(INPUT_FILE1)
        e = load_exif_by_PIL(INPUT_FILE1)
        if 34853 in zeroth_dict:
            zeroth_dict.pop(34853)
        if 34853 in e:
            gps = e.pop(34853)
        for key in sorted(zeroth_dict):
            if key in e:
                self.assertEqual(zeroth_dict[key], e[key])
        for key in sorted(exif_dict):
            if key in e:
                self.assertEqual(exif_dict[key], e[key])
        for key in sorted(gps_dict):
            if key in gps:
                if ((type(gps_dict[key]) == tuple) and
                    (type(gps_dict[key]) != type(gps[key]))):
                    self.assertEqual(pack_byte(*gps_dict[key]), gps[key])
                elif ((type(gps_dict[key]) == int) and
                      (type(gps_dict[key]) != type(gps[key]))):
                    self.assertEqual(struct.pack("B", gps_dict[key]), gps[key])
                else:
                    self.assertEqual(gps_dict[key], gps[key])

    def test_load2(self):
        """'load' on memory.
        """
        zeroth_dict, exif_dict, gps_dict = piexif.load(I1)
        e = load_exif_by_PIL(INPUT_FILE1)
        if 34853 in zeroth_dict:
            zeroth_dict.pop(34853)
        if 34853 in e:
            gps = e.pop(34853)
        for key in sorted(zeroth_dict):
            if key in e:
                self.assertEqual(zeroth_dict[key], e[key])
        for key in sorted(exif_dict):
            if key in e:
                self.assertEqual(exif_dict[key], e[key])
        for key in sorted(gps_dict):
            if key in gps:
                if ((type(gps_dict[key]) == tuple) and
                    (type(gps_dict[key]) != type(gps[key]))):
                    self.assertEqual(pack_byte(*gps_dict[key]), gps[key])
                elif ((type(gps_dict[key]) == int) and
                      (type(gps_dict[key]) != type(gps[key]))):
                    self.assertEqual(struct.pack("B", gps_dict[key]), gps[key])
                else:
                    self.assertEqual(gps_dict[key], gps[key])

    def test_load_le(self):
        """load test of little endian exif
        """
        zeroth_dict, exif_dict, gps_dict = piexif.load(INPUT_FILE_LE1)
        exif_dict.pop(41728) # value type is UNDEFINED but PIL returns int
        e = load_exif_by_PIL(INPUT_FILE_LE1)
        if 34853 in zeroth_dict:
            zeroth_dict.pop(34853)
        if 34853 in e:
            gps = e.pop(34853)
        for key in sorted(zeroth_dict):
            if key in e:
                self.assertEqual(zeroth_dict[key], e[key])
        for key in sorted(exif_dict):
            if key in e:
                self.assertEqual(exif_dict[key], e[key])
        for key in sorted(gps_dict):
            if key in gps:
                if ((type(gps_dict[key]) == tuple) and
                    (type(gps_dict[key]) != type(gps[key]))):
                    self.assertEqual(pack_byte(*gps_dict[key]), gps[key])
                elif ((type(gps_dict[key]) == int) and
                      (type(gps_dict[key]) != type(gps[key]))):
                    self.assertEqual(struct.pack("B", gps_dict[key]), gps[key])
                else:
                    self.assertEqual(gps_dict[key], gps[key])

    def test_dump(self):
        exif_bytes = piexif.dump(ZEROTH_DICT, EXIF_DICT, GPS_DICT)
        im = Image.new("RGBA", (8, 8))

        o = io.BytesIO()
        im.save(o, format="jpeg", exif=exif_bytes)
        im.close()
        o.seek(0)
        exif = load_exif_by_PIL(o)

    def test_insert(self):
        exif_bytes = piexif.dump(ZEROTH_DICT, EXIF_DICT, GPS_DICT)
        piexif.insert(exif_bytes, INPUT_FILE1, "insert.jpg")
        exif = load_exif_by_PIL("insert.jpg")

        piexif.insert(exif_bytes, NOEXIF_FILE, "insert.jpg")

        with self.assertRaises(ValueError):
            piexif.insert(b"dummy", io.BytesIO())

        piexif.insert(exif_bytes, "insert.jpg")

    def test_insert2(self):
        """'insert' on memory.
        """
        exif_bytes = piexif.dump(ZEROTH_DICT, EXIF_DICT, GPS_DICT)
        o = io.BytesIO()
        piexif.insert(exif_bytes, I1, o)
        self.assertEqual(o.getvalue()[0:2], b"\xff\xd8")
        exif = load_exif_by_PIL(o)

    def test_dump_and_load(self):
        exif_bytes = piexif.dump(ZEROTH_DICT, EXIF_DICT, GPS_DICT)
        im = Image.new("RGBA", (8, 8))

        o = io.BytesIO()
        im.save(o, format="jpeg", exif=exif_bytes)
        im.close()
        o.seek(0)
        zeroth_ifd, exif_ifd, gps_ifd = piexif.load(o.getvalue())
        zeroth_ifd.pop(ZerothIFD.ExifTag) # pointer to exif IFD
        zeroth_ifd.pop(ZerothIFD.GPSTag) # pointer to GPS IFD
        self.assertDictEqual(ZEROTH_DICT, zeroth_ifd)
        self.assertDictEqual(EXIF_DICT, exif_ifd)
        self.assertDictEqual(GPS_DICT, gps_ifd)

    def test_load_tif(self):
        zeroth_ifd, exif_ifd, gps_ifd = piexif.load(INPUT_FILE_TIF)
        exif_bytes = piexif.dump(zeroth_ifd, exif_ifd, gps_ifd)

        im = Image.new("RGBA", (8, 8))
        o = io.BytesIO()
        im.save(o, format="jpeg", exif=exif_bytes)
        im.close()
        o.seek(0)
        zeroth_ifd2, exif_ifd2, gps_ifd2 = piexif.load(o.getvalue())
        self.assertDictEqual(zeroth_ifd, zeroth_ifd2)
        self.assertDictEqual(exif_ifd, exif_ifd2)
        self.assertDictEqual(gps_ifd, gps_ifd2)


def suite():
    suite = unittest.TestSuite()
    suite.addTests(unittest.makeSuite(ExifTests))
    return suite


if __name__ == '__main__':
    unittest.main()