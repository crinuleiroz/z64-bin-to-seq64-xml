'''
### Sample Module

This module defines the `Sample` class, which represents the structure of an individual
sample in an Ocarina of Time and Majora's Mask instrument bank.

Classes:
    `Sample`:
        Represents a single sample structure.

Functionality:
    - Parse a sample from a binary format ('from_bytes').
    - Export sample data back to binary format ('to_bytes').
    - Convert the sample structure into a nested dictionary format ('to_dict') for XML serialization.
    - Validate internal consistency of data during parsing.

Dependencies:
    `struct`:
        For byte-level unpacking and packing.

    `AdpcmLoop`:
        Represents a single ADPCM loopbook structure in the instrument bank.

    `AdpcmBook`:
        Represents a single ADPCM codebook structure in the instrument bank.

    `Helpers`:
        For alignment, padding, and low-level binary operations.

    `Enums`:
        `AudioSampleCodec`:
            Enum defining supported codec types.

        `AudioStorageMedium`:
            Enum defining supported storage mediums.

Intended Usage:
    This module is designed to support the reconstruction and deconstruction of instrument bank sample data
    from Ocarina of Time and Majora's Mask into SEQ64-compatible XML and binary. Used in conjunction with
    'Audiobank' and 'Bankmeta' for full instrument bank conversion.
'''

# Import child structures
from .Loopbook import AdpcmLoop
from .Codebook import AdpcmBook

# Import helper functions
from ...Helpers import *

# Import the audio sample enums
from ...Enums import AudioSampleCodec, AudioStorageMedium

class Sample: # struct size = 0x10
  ''' Represents a sample structure in an instrument bank '''
  def __init__(self):
    self.offset = 0
    self.index  = -1

    # Bitfield
    self.bits = 0

    # Unpacked bitfield
    self.unk_0        = 0
    self.codec        = 0
    self.medium       = 0
    self.is_cached    = 0
    self.is_relocated = 0
    self.size         = 0

    self.table_offset    = 0
    self.loopbook_offset = 0
    self.codebook_offset = 0

    # Child ADPCM structures
    self.loopbook = None
    self.codebook = None

  @classmethod
  def from_bytes(cls, sample_offset: int, bank_data: bytes, sample_registry: dict, loopbook_registry: dict, codebook_registry: dict):
    if sample_offset in sample_registry:
      return sample_registry[sample_offset]

    self = cls()
    self.offset = sample_offset

    (
      self.bits,
      self.table_offset,
      self.loopbook_offset,
      self.codebook_offset
    ) = struct.unpack('>4I', bank_data[sample_offset:sample_offset + 0x10])

    self.unk_0        = (self.bits >> 31) & 0b1
    self.codec        = (self.bits >> 28) & 0b111
    self.medium       = (self.bits >> 26) & 0b11
    self.is_cached    = (self.bits >> 25) & 1
    self.is_relocated = (self.bits >> 24) & 1
    self.size         = (self.bits >> 0) & 0b111111111111111111111111

    assert self.codebook_offset != 0
    assert self.loopbook_offset != 0
    assert AudioSampleCodec(self.codec) in (AudioSampleCodec.CODEC_ADPCM, AudioSampleCodec.CODEC_SMALL_ADPCM)
    assert AudioStorageMedium(self.medium) == AudioStorageMedium.MEDIUM_RAM
    assert not self.is_relocated

    self.loopbook = AdpcmLoop.from_bytes(self.loopbook_offset, bank_data, loopbook_registry)
    self.codebook = AdpcmBook.from_bytes(self.codebook_offset, bank_data, codebook_registry)

    sample_registry[sample_offset] = self
    self.index = len(sample_registry) - 1
    return self

  def to_dict(self) -> dict:
    return {
      "address": str(self.offset), "name": f"Sample [{self.index}]",
      "struct": {"name": "ABSample",
        # Leave this comment formatted as-is, it adds a nice prettified comment to each sample item explaining the bitfield
        "__comment__": f"""
            Below are the bitfield values for each bit they represent.
            Each of these values takes up a specific amount of the 32 bits representing the u32 value.
             1 Bit(s): Unk_0       (Bit(s) 1):    {self.unk_0}
             3 Bit(s): Codec       (Bit(s) 2-4):  {AudioSampleCodec(self.codec).name} ({self.codec})
             2 Bit(s): Medium      (Bit(s) 5-6):  {AudioStorageMedium(self.medium).name} ({self.medium})
             1 Bit(s): Cached      (Bit(s) 7):    {bool(self.is_cached)} ({self.is_cached})
             1 Bit(s): Relocated   (Bit(s) 8):    {bool(self.is_relocated)} ({self.is_relocated})
            24 Bit(s): Binary size (Bit(s) 9-32): {self.size}
        """,
        "field": [
          {"name": "Bitfield", "datatype": "uint32", "ispointer": "0", "isarray": "0", "meaning": "None", "value": str(self.bits)},
          {"name": "Audiotable Address", "datatype": "uint32", "ispointer": "0", "ptrto": "ATSample", "isarray": "0", "meaning": "Sample Address (in Sample Table)", "value": str(self.table_offset)},
          {"name": "Loop Pointer", "datatype": "uint32", "ispointer": "1", "ptrto": "ALADPCMLoop", "isarray": "0", "meaning": "Ptr ALADPCMLoop", "value": str(self.loopbook_offset), "index": str(self.loopbook.index)},
          {"name": "Book Pointer", "datatype": "uint32", "ispointer": "1", "ptrto": "ALADPCMBook", "isarray": "0", "meaning": "Ptr ALADPCMBook", "value": str(self.codebook_offset), "index": str(self.codebook.index)}
        ]
      }
    }

  @classmethod
  def from_dict(cls, data: dict, loopbook_registry: dict, codebook_registry: dict):
    self = cls()

    self.unk_0        = data['unk_0']
    self.codec        = data['codec']
    self.medium       = data['medium']
    self.is_cached    = data['is_cached']
    self.is_relocated = data['is_relocated']
    self.size         = data['size']
    self.table_offset = data['sample_pointer']

    self.loopbook = loopbook_registry[data['loop']]
    self.codebook = codebook_registry[data['book']]

    return self

  def to_bytes(self) -> bytes:
    bits  = 0
    bits |= (self.unk_0 & 0b1) << 31
    bits |= (self.codec & 0b111) << 28
    bits |= (self.medium & 0b11) << 26
    bits |= (self.is_cached & 1) << 25
    bits |= (self.is_relocated & 1) << 24
    bits |= (self.size & 0b111111111111111111111111)

    return struct.pack(
      '>4I',
      bits,
      self.table_offset,
      self.loopbook_offset,
      self.codebook_offset
    )

if __name__ == '__main__':
  pass
