# Register Tool Set
This is the tool set for embeded software development when dealing with registers.

# Installation
The python version should be high enough. Mine is `> 3.11`. You can try with your own version.
The libraries should be installed to make it work: `pip3 install -r requirements.txt`.

# Usage
`python3 reg.py --help`

An example can be: `python3 reg.py r 0x786789 -f '30,[27:18]=0x87,7:8=0x3' -f 3:2=3 -f 0 -s`
