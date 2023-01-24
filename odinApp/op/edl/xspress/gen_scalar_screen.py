
import argparse
HEADER = '''
4 0 1
beginScreenProperties
major 4
minor 0
release 1
x 792
y 199
w 2000
h 1200
font "arial-medium-r-12.0"
ctlFont "arial-medium-r-12.0"
btnFont "arial-medium-r-12.0"
fgColor index 14
bgColor index 3
textColor index 14
ctlFgColor1 index 25
ctlFgColor2 index 25
ctlBgColor1 index 3
ctlBgColor2 index 3
topShadowColor index 1
botShadowColor index 11
title "Xspress Scalars"
showGrid
snapToGrid
gridSize 5
endScreenProperties

# (Embedded Window)
object activePipClass
beginObjectProperties
major 4
minor 1
release 0
x 25
y 20
w 1705
h 25
fgColor index 14
bgColor index 3
topShadowColor index 1
botShadowColor index 11
displaySource "menu"
filePv "LOC\\\\dummy=i:0"
sizeOfs 5
numDsps 1
displayFileName {
  0 "XspressChannelScalarsHeader_embed"
}
noScroll
endObjectProperties

'''

CHAN = '''
# (Embedded Window)
object activePipClass
beginObjectProperties
major 4
minor 1
release 0
x 25
y {}
w 1705
h 25
fgColor index 14
bgColor index 3
topShadowColor index 1
botShadowColor index 11
displaySource "menu"
filePv "LOC\\\\dummy=i:0"
sizeOfs 5
numDsps 1
displayFileName {{
  0 "XspressChannelScalars_embed"
}}
symbols {{
  0 "CHAN={}"
}}
noScroll
endObjectProperties

'''

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'file', metavar='str', type=str, help='edl file to write')
    parser.add_argument( 'chan', metavar='int', type=int, help='number of chans to generate')

    args = parser.parse_args()
    print(args.file)
    print(args.chan)
    y = 45
    chan = 1
    with open(args.file, 'w') as f:
        f.write(HEADER)
        for i in range(args.chan):
            f.write(CHAN.format(y, chan))
            chan += 1
            y += 25

