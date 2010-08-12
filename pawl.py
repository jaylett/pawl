# pawl: automatically rip TV episodes and special features from a DVD,
# using Handbrake. Also caters for films (Handbrake's -L doesn't
# always work, and you don't get control over adudio & subtitle tracks).
#
# If you don't like my layouts, hack away. If you want different filenames
# you're going to have to do some work.
#
# (c) James Aylett 2009, 2010

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

ignore_features = False
ignore_episodes = False
ignore_specials = False

script = []

# can't be bothered to figure out how to call out to HandBrakeCLI on Mac OS
# so it doesn't hang instead of exit after ripping
#weird = True
weird = False

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
    #print "Running %s" % (args,)
    p = subprocess.Popen(
        args,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT
    )
    outdata = p.communicate()[0]
    if p.returncode!=0:
        print "Erk."
        print outdata
        return None
    else:
        return outdata.split('\n')

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
        
    def get_subtitle_tracks_parameter(self):
        return ','.join(
            map(
                lambda x: str(x),
                range(1, len(self.subtitle)+1)
            )
        )
        
    def __unicode__(self):
        return u"Title %i (%s/%i), %i audio, %i subtitle" % (self.number, self.duration, self.get_duration(), len(self.audio), len(self.subtitle),)

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

def rip_title(device, preset, title, directory, prefix, epnumber=None):
    if epnumber==None:
        out_filename = "%s.mkv" % (prefix,)
    else:
        out_filename = "%s%2.2i.mkv" % (prefix, epnumber,)
    if not weird:
        print u"Ripping %s as %s" % (title, out_filename)
    out_filename = os.path.join(directory, out_filename)
    if os.path.isfile(out_filename):
        print (u"WILL NOT OVERWRITE PREVIOUS RIP: %s" % out_filename).encode('utf-8')
        return
    out = drive_handbrake(
        device, preset,
        [
            '-t', str(title.number),
            '-o', out_filename,
            '-a', title.get_audio_tracks_parameter(),
#            '--crop', '2:2:2:2', # really somewhat arbitrary attempt...
            '-s', title.get_subtitle_tracks_parameter(),
        ],
    )
    #if not weird:
    #    print ''.join(out)

def brute_episode_finder(titles, min_length, max_length):
    df = max_length - min_length
    def within_bounds(title):
        d = title.get_duration()
        res = d <= max_length and d >= min_length
        #print d, title.number, res
        return res

    return (
        filter(within_bounds, titles),
        filter(lambda t: t.get_duration() < min_length, titles),
        filter(lambda t: t.get_duration() > max_length, titles),
    )

def feature_episode_finder(titles, min_length, max_length):
    # we just want features & special features

    return (
        [],
        filter(lambda t: t.get_duration() < min_length, titles),
        filter(lambda t: t.get_duration() >= min_length, titles),
    )

def smart_episode_finder(titles, min_length, max_length):
    # let's try to find the episodes on this disk
    start = 0
    expected_duration = None
    while start<len(titles):
        if titles[start].get_duration() > min_length and titles[start].get_duration() < max_length:
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

    specials = titles[:start] + titles[end:]

    return (
        titles[start:end],
        filter(lambda t: t.get_duration() <= max_length, specials),
        filter(lambda t: t.get_duration() > max_length, specials),
    )

def process_disk(device, directory, prefix, episode_offset=0, feature_offset=0, min_ep_length=None, max_ep_length=None, test=False, episode_finder=smart_episode_finder, feature=False, remove_duplicates=None):
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

    # bulk up the lengths to have them in seconds
    min_ep_length *= 60
    max_ep_length *= 60

    if test:
        for title in titles:
            print title

    if remove_duplicates==None:
        remove_duplicates = lambda x: x
    (episodes, specials, features,) = map(remove_duplicates, episode_finder(titles, min_ep_length, max_ep_length))

    if test:
        if not ignore_episodes:
            print "Episodes are %s" % (
                ', '.join(map(lambda t: str(t.number), episodes)),
            )
        if not ignore_specials:
            print "Specials are %s" % (
                ', '.join(map(lambda t: str(t.number), specials)),
            )
        if not ignore_features:
            print "Features are %s" % (
                ', '.join(map(lambda t: str(t.number), features)),
            )
        return

    # Rip episodes as 1x01 etc.; special features as 1x00 - 01 etc.
    # If it's a feature disk, rip special features as <name> - Special 01 etc
    # and features as <name> - 01 etc.; if only one feature and it's a
    # feature disk, rip feature as <name> alone.

    # In "normal" (TV & Doctor Who) rips:
    # Don't include anything over the max episode length, as this is typically
    # the individual episodes shown together as one title.
    #   ignore_features skips things longer than a single episode
    #      generally, these are "all episodes as one title"
    #   ignore_episodes skips detected episodes (for ripping features from
    #      my earlier attempts when I ignored them)
    if not ignore_specials:
        for title in specials:
            #print "Ripping %i as special feature" % (i, )
            if feature:
                rip_title(device, preset, title, directory, "%s - Special " % prefix, 1+feature_offset)
            else:
                rip_title(device, preset, title, directory, "%s00 - " % prefix, 1+feature_offset)
            feature_offset += 1
    if not ignore_episodes:
        for title in episodes:
            #print "Ripping %i as episode" % (i, )
            rip_title(device, preset, title, directory, prefix, 1+episode_offset)
            episode_offset += 1
    if not ignore_features:
        # if there's only one, and there weren't any previously found,
        # just rip without a feature number; otherwise, we're ripping
        # variants across multiple disks, so start treating them properly
        # rather than just stomping over the top of them.
        if feature and len(features)==1 and episode_offset==0:
            #print "Ripping %i as feature" % (i, )
            rip_title(device, preset, features[0], directory, prefix)
        else:
            for title in features:
                #print "Ripping %i as feature" % (i, )
                if feature:
                    rip_title(device, preset, title, directory, "%s - " % prefix, 1+episode_offset)
                    episode_offset += 1
                else:
                    rip_title(device, preset, title, directory, "%00 - " % prefix, 1+feature_offset)
                    feature_offset += 1

    if weird:
        print ' && '.join(script) # fixme: and execute it, ideally...

if __name__ == '__main__':
    parser = optparse.OptionParser()
    parser.add_option('-D', '--doctor-who', dest='doctorwho', help='Rip to Doctor Who layout', default=False, action='store_true')
    parser.add_option('-b', '--bludgeon', dest='bludgeon', help='Bludgeon into submission: rip everything episode-length as an episode', default=False, action='store_true')
    parser.add_option('-d', '--device', dest='device', help='Set device', default='/dev/disk2', action='store')
    parser.add_option('-p', '--preset', dest='preset', help='Override default preset', default='Television', action='store')
    parser.add_option('-t', '--test', dest='test', help="Test, don't actually do anything", default=False, action='store_true')
    parser.add_option('-f', '--feature', dest='feature', help="Rip to Feature layout", default=False, action='store_true')
    parser.add_option('-F', '--include-features', dest='features', help="Rip feature-length episodes", default=None, action='store_true')
    parser.add_option('-E', '--skip-episodes', dest='episodes', help="Don't rip normal episodes", default=True, action='store_false')
    parser.add_option('-S', '--skip-special-features', dest='specials', help="Don't rip special features", default=True, action='store_false')
    parser.add_option('-m', '--min-ep-length', dest='min_ep_length', help='Minimum episode length (mins, overrides automatic)', default=None, action='store', type='int')
    parser.add_option('-M', '--max-ep-length', dest='max_ep_length', help='Maximum episode length (mins, overrides automatic)', default=None, action='store', type='int')
    parser.add_option('-l', '--expected-ep-length', dest='ep_length', help='Expected episode length (mins)', default=None, action='store', type='int')
    parser.add_option('-e', '--expected-episodes', dest='num_episodes', help='Expected number of episodes', default=None, action='store', type='int')
    parser.add_option('-r', '--remove-duplicates', dest='dedupe', help="Don't rip suspected duplicates", default=False, action='store_true')
    (options, args) = parser.parse_args()

    ignore_episodes = not options.episodes
    ignore_specials = not options.specials

    if options.feature:
        # for feature layout, episodes don't exist
        ignore_episodes = True

    # if no explicit value for ignore_features, default is dependent
    # on whether we're ripping to feature layout
    if options.features==None:
        ignore_features = not options.feature
    else:
        ignore_features = not options.features

    if options.ep_length==None:
        if options.doctorwho:
            # doesn't work for the brief Colin Baker period of 45
            # minute episodes
            ep_length = 30 # ie "half hour"
        elif options.feature:
            ep_length = 90 # used to differentiate between (main) features and special features
        else:
            # default to hour shows, so -l 30 for half hour
            ep_length = 60 # ie "hour"
    else:
        ep_length = options.ep_length

    options.min_ep_length = options.min_ep_length or (2 * ep_length / 3)
    options.max_ep_length = options.max_ep_length or ep_length

    if options.feature:
        if len(args)<1:
            print "Takes at least one argument:\n\t<film title>\n"
            sys.exit(1)
    elif len(args)<2:
        print "Takes at least two arguments:\n\t<series> <season>\n  or\t<number> <title> (for Doctor Who)\n"
        sys.exit(1)

    preset = options.preset
    if options.doctorwho:
        # Doctor Who: give number of story and name as two args
        num = args[0]
        name = args[1]
        directory = os.path.join('/Volumes/TV#1/Media/Doctor Who/Classic/', "%s - %s" % (num, name,))
    elif options.feature:
        # Feature; just a name
        num = None
        name = args[0]
        directory = os.path.join('/Volumes/2T/Media/Features/', name)
    else:
        # TV: give name of series and season as two args, first episode number
        # as optional third (else try to ponder from directory), first
        # feature number as optional fourth (else try to ponder from directory)
        series = args[0]
        season = int(args[1])
        directory = os.path.join('/Volumes/TV#1/Media/TV Shows/', series, 'Season %i' % season)
        num = season

    if len(args)>2:
        episode_offset = int(args[2]) - 1
    elif os.path.isdir(directory):
        # PONDER
        episode_offset = 0
        for file in os.listdir(directory):
            try:
                if options.feature:
                    if u' - Special ' in file:
                        # don't count these, they don't collide
                        # (well, except in extremely unusual
                        # circumstances)
                        continue
                    # episode offset used for the actual features, in case
                    # there are multiple versions or something (eg:
                    # Blade Runner Ultimate Edition) across multiple
                    # disks.
                    #
                    # Format here is just <name> 01, etc.
                    # (or just <name> if there's only one, in which case
                    # subsequent ones should start at 02).
                    file = file.split('.')[0]
                    bits = file.split(' ')
                    if len(bits)==1:
                        # existing single feature; set next number to 2
                        # so future single-feature disk rips fall in line
                        episode_offset = 1
                    else:
                        if episode_offset < int(bits[-1]):
                            episode_offset = int(bits[-1])
                else:
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
        feature_offset = int(args[3]) - 1
    elif os.path.isdir(directory):
        # PONDER
        feature_offset = 0
        for file in os.listdir(directory):
            try:
                file = file.split('.')[0]
                if options.feature:
                    bits = file.split(' Special ')
                else:
                    bits = file.split('x')
                if len(bits)>1:
                    # Syntax: <n>x00 - 01 etc.; <name> - Special 01 etc.
                    if options.feature:
                        if feature_offset < int(bits[1]):
                            feature_offset = int(bits[1])
                    else:
                        ep_bits = bits[1].split('-')
                        if ep_bits[0].strip() == '00':
                            if feature_offset < int(ep_bits[-1]):
                                feature_offset = int(ep_bits[-1])
            except:
                pass
    else:
        feature_offset = 0

    if options.test or not weird:
        # If we aren't weird (which should be never, but I'm keeping support
        # until I'm certain), then stdout is ours to play with (if weird,
        # we use it to display the HandbrakeCLI commands to invoke).
        #
        # So use that freedom to give an idea of what's going on.
        if options.test:
            msgstart = u'Would rip'
        else:
            msgstart = u'Ripping'
        if options.feature:
            print (u"%s to %s..." % (msgstart, directory,)).encode('utf-8')
        else:
            print (u"%s to %s as %sx..." % (msgstart, directory, num,)).encode('utf-8')

        if not ignore_episodes:
            print (u"  Episodes from %i" % (episode_offset+1,)).encode('utf-8')
        if not ignore_specials:
            print (u"  Special features from %i" % (feature_offset+1,)).encode('utf-8')
        if not ignore_features:
            if options.feature:
                print (u"  Features from %i" % (episode_offset+1, )).encode('utf-8')
            else:
                print (u"  %s feature length episodes." % (msgstart, )).encode('utf-8')
        if options.bludgeon:
            print (u"  Bludgeoning: will rip all titles within episode length %i-%i." % (options.min_ep_length, options.max_ep_length,)).encode('utf-8')

    if options.bludgeon:
        episode_finder = brute_episode_finder
    elif options.feature:
        episode_finder = feature_episode_finder
    else:
        episode_finder = smart_episode_finder

    if options.feature:
        prefix = name
    else:
        prefix = "%sx" % num

    if not options.test:
        if not os.path.exists(directory):
            mkdir_p(directory)
        elif not os.path.isdir(directory):
            print (u"%s is not a directory." % directory).encode('utf-8')

    if options.dedupe:
        remove_duplicates = None
    else:
        remove_duplicates = None

    process_disk(
        options.device,
        directory,
        prefix,
        episode_offset,
        feature_offset,
        options.min_ep_length,
        options.max_ep_length,
        test=True,
        episode_finder = episode_finder,
        feature=options.feature,
        remove_duplicates=remove_duplicates,
    )
    if not options.test:
        process_disk(
            options.device,
            directory,
            prefix,
            episode_offset,
            feature_offset,
            options.min_ep_length,
            options.max_ep_length,
            episode_finder = episode_finder,
            feature=options.feature,
            remove_duplicates=remove_duplicates,
            )
