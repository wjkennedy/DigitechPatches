# Digitech Patches

These are patches from my GNX3000 dumped with gdigi.

## 00000.g3kp

Not sure about the purpose of this one..

## bigbeams.g3kp

Big (Eyed) Beans vs. "The Beam"

## big.g3kp

"Embiggens the sound"

## hawkwend.g3kp

/s

## megalo.g3kp

"Emdeepens the sound"

## reverso.g3kp

Guess.

## spacedog.g3kp

Laika? Nyet.

## vacuumxl.g3kp

Get inside.


## Tools

A helper script `gnx3000.py` can list preset names and edit parameter values in bulk.

Example usages:

```bash
python gnx3000.py list
python gnx3000.py set-name MyPatch big.g3kp
python gnx3000.py set-param 2434 90 big.g3kp
python gnx3000.py upload "MIDI Output" big.g3kp --dry-run
```
