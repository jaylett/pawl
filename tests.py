import unittest
import pawl

class ParseWeirdHandbrakeOutput(unittest.TestCase):
    def test_single_title(self):
        ts = pawl.parse_titles("""
+ title 7:
  + vts 3, ttn 1, cells 0->4 (453012 blocks)
  + duration: 00:26:15
  + size: 720x576, aspect: 1.33, 25.000 fps
  + autocrop: 2/2/8/10
  + chapters:
    + 1: cells 0->0, 115316 blocks, duration 00:06:41
    + 2: cells 1->1, 113769 blocks, duration 00:06:35
    + 3: cells 2->2, 103977 blocks, duration 00:06:01
    + 4: cells 3->3, 79300 blocks, duration 00:04:35
    + 5: cells 4->4, 40650 blocks, duration 00:02:22
  + audio tracks:
    + 1, English (AC3) (2.0 ch), 48000Hz, 192000bps
  + subtitle tracks:
    + 1, English (iso639-2: eng)
        """.split('\n'))
        
        self.assertEqual(len(ts), 1)
        t = ts[0]
        self.assertEqual(t.duration, "00:26:15")
        self.assertEqual(t.number, 7)
        self.assertEqual(len(t.audio), 1)
        self.assertEqual(t.audio[0].description, 'English (AC3) (2.0 ch)')
        self.assertEqual(t.audio[0].samplerate, '48000Hz')
        self.assertEqual(t.audio[0].bitrate, '192000bps')
        self.assertEqual(len(t.subtitle), 1)
        self.assertEqual(t.subtitle[0].description, 'English (iso639-2: eng)')
        self.assertEqual(t.subtitle[0].samplerate, None)
        self.assertEqual(t.subtitle[0].bitrate, None)

    def test_two_titles(self):
        ts = pawl.parse_titles("""
+ title 6:
  + vts 2, ttn 5, cells 0->24 (2162108 blocks)
  + duration: 01:36:44
  + size: 720x576, aspect: 1.33, 25.000 fps
  + autocrop: 0/0/12/10
  + chapters:
    + 1: cells 0->0, 107704 blocks, duration 00:04:50
    + 2: cells 1->1, 101927 blocks, duration 00:04:33
    + 3: cells 2->2, 169251 blocks, duration 00:07:33
    + 4: cells 3->3, 76586 blocks, duration 00:03:24
    + 5: cells 4->4, 58616 blocks, duration 00:02:37
    + 6: cells 5->5, 27793 blocks, duration 00:01:16
    + 7: cells 6->6, 112838 blocks, duration 00:05:03
    + 8: cells 7->7, 82342 blocks, duration 00:03:41
    + 9: cells 8->8, 113926 blocks, duration 00:05:05
    + 10: cells 9->9, 116138 blocks, duration 00:05:11
    + 11: cells 10->10, 93521 blocks, duration 00:04:10
    + 12: cells 11->11, 28562 blocks, duration 00:01:18
    + 13: cells 12->12, 97953 blocks, duration 00:04:23
    + 14: cells 13->13, 76661 blocks, duration 00:03:26
    + 15: cells 14->14, 192812 blocks, duration 00:08:37
    + 16: cells 15->15, 75855 blocks, duration 00:03:24
    + 17: cells 16->16, 74395 blocks, duration 00:03:20
    + 18: cells 17->17, 28260 blocks, duration 00:01:19
    + 19: cells 18->18, 89686 blocks, duration 00:04:00
    + 20: cells 19->19, 107409 blocks, duration 00:04:48
    + 21: cells 20->20, 106000 blocks, duration 00:04:44
    + 22: cells 21->21, 99920 blocks, duration 00:04:28
    + 23: cells 22->22, 95460 blocks, duration 00:04:16
    + 24: cells 23->23, 28488 blocks, duration 00:01:21
    + 25: cells 24->24, 5 blocks, duration 00:00:00
  + audio tracks:
    + 1, English (AC3) (2.0 ch), 48000Hz, 192000bps
    + 2, English (AC3) (2.0 ch), 48000Hz, 192000bps
    + 3, English (AC3) (2.0 ch), 48000Hz, 192000bps
  + subtitle tracks:
    + 1, English (iso639-2: eng)
    + 2, English (iso639-2: eng)
    + 3, English (iso639-2: eng)
+ title 7:
  + vts 3, ttn 1, cells 0->4 (453012 blocks)
  + duration: 00:26:15
  + size: 720x576, aspect: 1.33, 25.000 fps
  + autocrop: 2/2/8/10
  + chapters:
    + 1: cells 0->0, 115316 blocks, duration 00:06:41
    + 2: cells 1->1, 113769 blocks, duration 00:06:35
    + 3: cells 2->2, 103977 blocks, duration 00:06:01
    + 4: cells 3->3, 79300 blocks, duration 00:04:35
    + 5: cells 4->4, 40650 blocks, duration 00:02:22
  + audio tracks:
    + 1, English (AC3) (2.0 ch), 48000Hz, 192000bps
  + subtitle tracks:
    + 1, English (iso639-2: eng)
        """.split('\n'))

        self.assertEqual(len(ts), 2)
        t = ts[0]
        self.assertEqual(t.duration, "01:36:44")
        self.assertEqual(t.number, 6)
        self.assertEqual(len(t.audio), 3)
        for i in range(0, 3):
            self.assertEqual(t.audio[i].description, 'English (AC3) (2.0 ch)')
            self.assertEqual(t.audio[i].samplerate, '48000Hz')
            self.assertEqual(t.audio[i].bitrate, '192000bps')
        self.assertEqual(len(t.subtitle), 3)
        for i in range(0, 3):
            self.assertEqual(t.subtitle[i].description, 'English (iso639-2: eng)')
            self.assertEqual(t.subtitle[i].samplerate, None)
            self.assertEqual(t.subtitle[i].bitrate, None)
        t = ts[1]
        self.assertEqual(t.duration, "00:26:15")
        self.assertEqual(t.number, 7)
        self.assertEqual(len(t.audio), 1)
        self.assertEqual(t.audio[0].description, 'English (AC3) (2.0 ch)')
        self.assertEqual(t.audio[0].samplerate, '48000Hz')
        self.assertEqual(t.audio[0].bitrate, '192000bps')
        self.assertEqual(len(t.subtitle), 1)
        self.assertEqual(t.subtitle[0].description, 'English (iso639-2: eng)')
        self.assertEqual(t.subtitle[0].samplerate, None)
        self.assertEqual(t.subtitle[0].bitrate, None)

if __name__ == "__main__":
    unittest.main()
