# pawl: automatically rip TV episodes and special features from a DVD
# uses Handbrake. Suggest the 'Television' preset is a good one.
#
# If you don't like my layouts, hack away. If you want different filenames
# you're going to have to do some work.
#
# (c) James Aylett 2009

import optparse
import os
import subprocess
import sys

handbrake_cli = None
if os.environ.has_key('HANDBRAKE'):
    handbrake_cli = os.environ['HANDBRAKE']
else:
    locs = [ '/usr/bin/', '/usr/local/bin/', '/Users/jaylett', ]
    excs = [ 'HandBrakeCLI', ] # put whatever it is on linux etc. here
    for t in locs:
        for x in excs:
            handbrake_cli = os.path.join(t, x)
            if os.path.exists(handbrake_cli):
                break
            else:
                handbrake_cli = None
    if handbrake_cli == None:
        handbrake_cli = 'HandBrakeCLI' # assume it's on the path
        # note that this is the Mac OS X name

rip_features = False
ignore_episodes = False
ignore_specials = False

script = []

# can't be bothered to figure out how to call out to HandBrakeCLI on Mac OS
# so it doesn't hang instead of exit after ripping
weird = True

def mkdir_p(path):
    bits = []
    while path!='' and path!='/':
        (path, last) = os.path.split(path)
        bits.insert(0, last)
    path = '/'
    for bit in bits:
        path = os.path.join(path, bit)
        if not os.path.exists(path):
            os.mkdir(path)
        elif not os.path.isdir(path):
            raise RuntimeError((u'Path %s already exists as non-dir.' % path).encode('utf-8'))

def drive_handbrake(device, preset, options, test=False, simple=False):
    args = [handbrake_cli, '-i', device, '-Z', preset] + list(options)
    if test:
        print " ".join(map(lambda x: '"%s"' % x, args))
        return []
    if weird and not simple:
        script.append(" ".join(map(lambda x: '"%s"' % x, args)))
        return []
    p = subprocess.Popen(
        args,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT
    )
    p.wait()
    if p.returncode!=0:
        print "Erk."
        print p.stdout.read()
        return None
    else:
        #r = p.stdout.read()
        #print r
        #return r.split('\n')
        return p.stdout.readlines()

class Unicodish:
    def __str__(self):
        return self.__unicode__().encode('utf-8')
        
class Title(Unicodish):
    def __init__(self, track_number):
        self.number = track_number
        self.audio = []
        self.subtitle = []

    def get_duration(self):
        # figures it out in seconds
        bits = self.duration.split(':')
        bits.reverse()
        secs = 0
        mult = 1
        for bit in bits:
            secs += mult * int(bit)
            mult = mult * 60
        return secs
        
    def get_audio_tracks_parameter(self):
        return ','.join(
            map(
                lambda x: str(x),
                range(1, len(self.audio)+1)
            )
        )
        
    def __unicode__(self):
        return u"Title (%s/%i), %i audio tracks, %i subtitle tracks" % (self.duration, self.get_duration(), len(self.audio), len(self.subtitle),)

class Track(Unicodish):
    def __init__(self, *bits):
        self.description = bits[0].strip()
        if len(bits)>1:
            self.samplerate = bits[1].strip()
        else:
            self.samplerate = None
        if len(bits)>2:
            self.bitrate = bits[2].strip()
        else:
            self.bitrate = None

    def __unicode__(self):
        return u"Track (%s)" % (self.description,)

def parse_titles(lines):
    # title {
    #   duration, size, aspect, fps, autocrop,
    #   chapters [] { startcell, endcell, blocks, duration }
    #   audio tracks [] { language, type, samplerate, bitrate },
    #   subtitle tracks [] { language, type },
    # }

    current_title = None
    titles = []

    TITLE = '+ title '
    DURATION = '  + duration: '
    AUDIOTRACKS = '  + audio tracks:'
    SUBTITLETRACKS = '  + subtitle tracks:'
    OTHER = '  + '
    NESTED = '    + '
    
    tracks = None

    for line in lines:
        line = line.rstrip()
        if line.startswith(TITLE):
            remains = line[len(TITLE):]
            if remains.endswith(':'):
                remains = remains[:-1]
            number = int(remains)
            current_title = Title(number)
            titles.append(current_title)
            tracks = None
        elif line.startswith(DURATION):
            v = line[len(DURATION):].strip()
            current_title.duration = v
        elif line.startswith(AUDIOTRACKS):
            tracks = 'audio'
        elif line.startswith(SUBTITLETRACKS):
            tracks = 'subtitle'
        elif line.startswith(OTHER):
            pass
        elif line.startswith(NESTED):
            if tracks==None:
                continue

            remaining = line[len(NESTED):]
            # strip leading "<n>,"
            off = remaining.find(',')
            if off!=-1 and remaining[:off].isdigit():
                r = int(remaining[:off])
                if tracks=='audio':
                    s = len(current_title.audio)
                elif tracks=='subtitle':
                    s = len(current_title.subtitle)
                else:
                    s = -1 # something's wrong
                if r-1!=s:
                    print "Eek. Mismatch of counter and internal build (%i vs %i)" % (r-1, s,)
                remaining = remaining[off+1:].strip()
                
                bits = remaining.split(',')
                t = Track(*bits)
                
                if tracks=='audio':
                    current_title.audio.append(t)
                elif tracks=='subtitle':
                    current_title.subtitle.append(t)
            else:
                print "Weird unexpected line: %s" % line
                
    return titles

def rip_title(device, preset, title, directory, prefix, epnumber):
    if not weird:
        print u"Ripping %s" % title
    out = drive_handbrake(
        device, preset,
        [
            '-t', str(title.number),
            '-o', os.path.join(directory, "%s%2.2i.mkv" % (prefix, epnumber,)),
            '-a', title.get_audio_tracks_parameter(),
#            '--crop', '2:2:2:2', # really somewhat arbitrary attempt...
#            '-s', title.get_audio_tracks_parameter(),
        ],
    )
    if not weird:
        print ''.join(out)

def process_disk(device, directory, prefix, episode_offset=0, feature_offset=0, min_ep_length=None, max_ep_length=None):
    if min_ep_length==None:
        min_ep_length = 15
    if max_ep_length==None:
        max_ep_length = 60
    #print "Processing, min = %i, max = %i" % (min_ep_length, max_ep_length, )
    out = drive_handbrake(device, preset, [ '-t', '0'], simple=True) # simple => no dance around processes from python
    if out==None:
        return
    #print out
    titles = parse_titles(out)
    #for title in titles:
    #    print title
        
    # let's try to find the episodes on this disk
    # it will probably be the first title under 1 hour and over 15 minutes
    # that also gives us our expected episode length; we then pull until
    # we get a title of significantly different length.
    start = 0
    expected_duration = None
    while start<len(titles):
        if titles[start].get_duration() > min_ep_length*60 and titles[start].get_duration() < max_ep_length*60:
            expected_duration = titles[start].get_duration()
            break
        start += 1

    if expected_duration:
        DELTA = expected_duration / 5.0
        #print "expected is %i, delta is %i" % (expected_duration, DELTA, )

        end = start+1
        while end<len(titles):
            if abs(titles[end].get_duration() - expected_duration) > DELTA:
                break
            end += 1
    else:
        start = 0
        end = 0

    #print "Episodes are [%i:%i] out of %i" % (start, end, len(titles), )

    # Rip episodes as 1x01 etc.; special features as 1x00 etc.
    # Don't include anything over an hour long at all, as this is typically
    # the individual episodes shown together as one title.
    #   rip_features forces > 60 minute titles to be ripped
    #      generally, these are "all episodes as one title"
    #   ignore_episodes skips detected episodes (for ripping features from
    #      my earlier attempts when I ignored them)
    if start > 0 and not ignore_specials:
        for i in range(0, start):
            if titles[i].get_duration() < 60*60 or rip_features:
                #print "Ripping %i as special feature" % (i, )
                rip_title(device, preset, titles[i], directory, "%s00 - " % prefix, i+1+feature_offset)
    if not ignore_episodes:
        for i in range(start, end):
            #print "Ripping %i as episode" % (i, )
            rip_title(device, preset, titles[i], directory, prefix, i-start+1+episode_offset)
    if end < len(titles) and not ignore_specials:
        for i in range(end, len(titles)):
            if titles[i].get_duration() < 60*60 or rip_features:
                #print "Ripping %i as special feature" % (i, )
                rip_title(device, preset, titles[i], directory, "%s00 - " % prefix, i-end+start+1+feature_offset)

    if weird:
        print ' && '.join(script) # fixme: and execute it, ideally...

if __name__ == '__main__':
    parser = optparse.OptionParser()
    parser.add_option('-D', '--doctor-who', dest='doctorwho', help='Rip to Doctor Who layout', default=False, action='store_true')
    parser.add_option('-d', '--device', dest='device', help='Set device', default='/dev/disk2', action='store')
    parser.add_option('-p', '--preset', dest='preset', help='Override default preset', default='Television', action='store')
    parser.add_option('-t', '--test', dest='test', help="Test, don't actually do anything", default=False, action='store_true')
    parser.add_option('-F', '--include-features', dest='features', help="Rip feature-length episodes (requires ripping special features)", default=False, action='store_true')
    parser.add_option('-E', '--skip-episodes', dest='episodes', help="Don't rip normal episodes", default=True, action='store_false')
    parser.add_option('-S', '--skip-special-features', dest='specials', help="Don't rip special features", default=True, action='store_false')
    parser.add_option('-m', '--min-ep-length', dest='min_ep_length', help='Minimum episode length (mins, overrides automatic)', default=None, action='store', type='int')
    parser.add_option('-M', '--max-ep-length', dest='max_ep_length', help='Maximum episode length (mins, overrides automatic)', default=None, action='store', type='int')
    parser.add_option('-l', '--expected-ep-length', dest='ep_length', help='Expected episode length (mins)', default=None, action='store', type='int')
    parser.add_option('-e', '--expected-episodes', dest='num_episodes', help='Expected number of episodes', default=None, action='store', type='int')
    (options, args) = parser.parse_args()

    rip_features = options.features
    ignore_episodes = not options.episodes
    ignore_specials = not options.specials

    if options.ep_length==None:
        if options.doctorwho:
            # doesn't work for the brief Colin Baker period of 45
            # minute episodes
            ep_length = 30 # ie "half hour"
        else:
            # default to hour shows, so -l 30 for half hour
            ep_length = 60 # ie "hour"
    else:
        ep_length = options.ep_length

    options.min_ep_length = options.min_ep_length or (2 * ep_length / 3)
    options.max_ep_length = options.max_ep_length or ep_length

    preset = options.preset
    if options.doctorwho:
        # Doctor Who: give number of story and name as two args
        num = args[0]
        name = args[1]
        directory = os.path.join('/media/All/Doctor Who/Classic/', "%s - %s" % (num, name,))
    else:
        # TV: give name of series and season as two args, first episode number
        # as optional third (else try to ponder from directory), first
        # feature number as optional fourth (else try to ponder from directory)
        series = args[0]
        season = int(args[1])
        directory = os.path.join('/media/All/TV Shows/', series, 'Season %i' % season)
        num = season

    if len(args)>2:
        episode_offset = int(args[2])
    elif os.path.isdir(directory):
        # PONDER
        episode_offset = 0
        for file in os.listdir(directory):
            try:
                file = file.split('.')[0]
                bits = file.split('x')
                if len(bits)>1:
                    ep_bits = bits[1].split('-')
                    if ep_bits[0].strip()!='00':
                        if episode_offset < int(ep_bits[-1]):
                            episode_offset = int(ep_bits[-1])
            except:
                pass
    else:
        episode_offset = 0
    if len(args)>3:
        feature_offset = int(args[3])
    elif os.path.isdir(directory):
        # PONDER
        feature_offset = 0
        for file in os.listdir(directory):
            try:
                file = file.split('.')[0]
                bits = file.split('x')
                if len(bits)>1:
                    # Syntax: <n>x00 - 01 etc.
                    ep_bits = bits[1].split('-')
                    if ep_bits[0].strip() == '00':
                        if feature_offset < int(ep_bits[-1]):
                            feature_offset = int(ep_bits[-1])
            except:
                pass
    else:
        feature_offset = 0

    if options.test:
        print (u"Ripping to %s as %sx..." % (directory, num,)).encode('utf-8')
        if not ignore_episodes:
            print (u"  Episodes from %i" % (episode_offset+1,)).encode('utf-8')
        if not ignore_specials:
            print (u"  Special features from %i" % (feature_offset+1,)).encode('utf-8')
        if rip_features:
            print "  Ripping feature length episodes."
    else:
        if not os.path.exists(directory):
            mkdir_p(directory)
        elif not os.path.isdir(directory):
            print (u"%s is not a directory." % directory).encode('utf-8')
        process_disk(
            options.device,
            directory,
            "%sx" % num,
            episode_offset,
            feature_offset,
            options.min_ep_length,
            options.max_ep_length,
            )
