''' Placeholder '''

import os
import sys
import datetime
from dataclasses import dataclass, field
import xml.etree.ElementTree as xml

# Import the Bankmeta and Audiobank
from utils.audiobank.Audiobank import Bankmeta, Audiobank

# Import the XML Tag enum
from utils.Enums import XMLTags

CURRENT_VERSION = '2025.05.24'

DATE = datetime.datetime.now().replace(microsecond=0).isoformat(' ')
DATE_FILENAME = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")

''' Classes '''
# @dataclass
# class XMLDataEntry:
#   enum_tag:  XMLTags
#   xml_tag:   str
#   audiobank: object = None
#   bankmeta:  object = None
#   xml_list:  list[dict] = field(default_factory=list)

#   def __post_init__(self):
#     self.parent_tag = self.enum_tag.value

#     filled_objects = [self.audiobank, self.bankmeta, self.xml_list]
#     if sum(1 for obj in filled_objects if obj is not None and obj != []) != 1:
#       raise ValueError("Exactly one audiobank object, bankmeta object, or XML dictionary list must be provided.")

#     self._populate_xml_list()

#   def _populate_xml_list(self):
#     if self.bankmeta:
#       self.xml_list = getattr(self.bankmeta, f'{self.parent_tag}_xml', [])
#     elif self.audiobank:
#       self.xml_list = getattr(self.audiobank, f'{self.parent_tag}_xml', [])

#   def get_address(self) -> str:
#     address_map = {
#       XMLTags.ABDRUMLIST: ("drumlist", "num_drum"),
#       XMLTags.ABSFXLIST:  ("sfxlist",  "num_sfx"),
#     }

#     if self.enum_tag in address_map:
#       list_attr, num_attr = address_map[self.enum_tag]
#       list_value = getattr(self.audiobank, list_attr, 0)
#       if list_value != 0 and getattr(self.audiobank, num_attr, 0) != 0:
#         return str(list_value)
#     return ''

@dataclass
class XMLDataEntry:
  enum_tag: XMLTags
  xml_tag: str
  xml_list: list[dict] = field(default_factory=list)
  audiobank: object = None  # audiobank is passed in during initialization

  def __post_init__(self):
    self.parent_tag = self.enum_tag.value

    self._populate_xml_list()

  def _populate_xml_list(self):
    if self.xml_list is None:
      self.xml_list = []

  def get_address(self) -> str:
    address_map = {
      XMLTags.ABDRUMLIST: ("drumlist_offset", "num_drums"),
      XMLTags.ABSFXLIST:  ("sfxlist_offset", "num_effects")
    }

    if self.enum_tag in address_map:
      list_attr, num_attr = address_map[self.enum_tag]
      list_value = getattr(self.audiobank, list_attr, 0)
      if list_value != 0 and getattr(self.audiobank.bankmeta, num_attr, 0) != 0:
        return str(list_value)
    return ''

''' Helper Functions '''
def read_binary(filename: str) -> bytearray:
  with open(filename, 'rb') as file:
    binary = bytearray(file.read())
  return binary

def get_nested_attr(obj, attr_chain):
  for attr in attr_chain.split('.'):
    obj = getattr(obj, attr)
  return obj

''' XML Writing Functions '''
# def dict_to_xml(tag: str, d: dict, parent: xml.Element = None) -> xml.Element:
#   element = xml.Element(tag)

#   for key, value in d.items():
#     # Create a comment if the key is "__comment__"
#     if key == "__comment__":
#       comment = xml.Comment(value)
#       element.append(comment)

#     # Recursion if the value is a dict
#     elif isinstance(value, dict):
#       dict_to_xml(key, value, element)

#     # Create multiple separate elements for each list entry
#     elif isinstance(value, list):
#       for item in value:
#         # The items should be dictionaries, so more recursion
#         child = dict_to_xml(key, item)
#         element.append(child)

#     else:
#       element.set(key, str(value) if value is not None else "")

#   # Add each separate item to the parent element
#   # e.g. prevents multiple <instruments> tags for each instrument <item> tag
#   if parent is not None:
#     parent.append(element)

#   return element

def dict_to_xml(tag: str, d, parent: xml.Element = None) -> xml.Element:
    """
    Convert a dictionary (or other data types) into XML elements.
    """
    # Ensure we're working with a dictionary or string for the current item
    if isinstance(d, dict):
      element = xml.Element(tag)

      for key, value in d.items():
        # Create a comment if the key is "__comment__"
        if key == "__comment__":
          element.append(xml.Comment(value))

        # Recursion if the value is a dict
        elif isinstance(value, dict):
          dict_to_xml(key, value, element)

        # Create multiple separate elements for each list entry
        elif isinstance(value, list):
          for item in value:
            # The items should be dictionaries, so more recursion
            if isinstance(item, dict):
              child = dict_to_xml(key, item)
              element.append(child)

        else:
          element.set(key, str(value) if value is not None else "")

    else:
      # If it's a string, just add it as the text content
      element = xml.Element(tag)
      element.text = str(d) if d is not None else ""

    # Add each separate item to the parent element
    # e.g. prevents multiple <instruments> tags for each instrument <item> tag
    if parent is not None:
      parent.append(element)

    return element

def create_xml_bank(filename: str, bankmeta: object, audiobank: object) -> None:
  xml_root = xml.Element('bank')

  for key, value in bankmeta.attributes.items():
    xml_root.set(key, str(value))

  xml_tree = xml.ElementTree(xml_root)
  xml_comment = xml.Comment(f'\n      DATE CREATED: {DATE}\n\n      This bank was created from a binary bank file, because of this there may be errors or differences from the original bank!\n  ')

  xml_data = [
    XMLDataEntry(XMLTags.ABINDEXENTRY, 'struct', [bankmeta.to_dict()]),
    XMLDataEntry(XMLTags.ABHEADER,     'struct', [{"name": 'ABHeader'}])
  ]

  audiobank_xml_data = audiobank.to_xml()

  xml_data.extend([
    XMLDataEntry(XMLTags.ABBANK,       'struct', audiobank_xml_data['abbank']),
    XMLDataEntry(XMLTags.ABDRUMLIST,   'struct', audiobank_xml_data['abdrumlist'], audiobank),
    XMLDataEntry(XMLTags.ABSFXLIST,    'struct', audiobank_xml_data['absfxlist'], audiobank),
    XMLDataEntry(XMLTags.INSTRUMENTS,  'item',   audiobank_xml_data['instruments']),
    XMLDataEntry(XMLTags.DRUMS,        'item',   audiobank_xml_data['drums']),
    XMLDataEntry(XMLTags.ENVELOPES,    'item',   audiobank_xml_data['envelopes']),
    XMLDataEntry(XMLTags.SAMPLES,      'item',   audiobank_xml_data['samples']),
    XMLDataEntry(XMLTags.ALADPCMBOOKS, 'item',   audiobank_xml_data['aladpcmbooks']),
    XMLDataEntry(XMLTags.ALADPCMLOOPS, 'item',   audiobank_xml_data['aladpcmloops'])
  ])

  # xml_data = [
  #   XMLDataEntry(XMLTags.ABINDEXENTRY, 'struct', bankmeta),
  #   XMLDataEntry(XMLTags.ABHEADER,     'struct', [{"name": 'ABHeader'}]),
  #   XMLDataEntry(XMLTags.ABBANK,       'struct', audiobank),
  #   XMLDataEntry(XMLTags.ABDRUMLIST,   'struct', audiobank),
  #   XMLDataEntry(XMLTags.ABSFXLIST,    'struct', audiobank),
  #   XMLDataEntry(XMLTags.INSTRUMENTS,  'item',   audiobank),
  #   XMLDataEntry(XMLTags.DRUMS,        'item',   audiobank),
  #   XMLDataEntry(XMLTags.ENVELOPES,    'item',   audiobank),
  #   XMLDataEntry(XMLTags.SAMPLES,      'item',   audiobank),
  #   XMLDataEntry(XMLTags.ALADPCMBOOKS, 'item',   audiobank),
  #   XMLDataEntry(XMLTags.ALADPCMLOOPS, 'item',   audiobank)
  # ]

  for entry in xml_data:
    element = xml.Element(entry.parent_tag)

    address = entry.get_address()
    if address:
      element.set("address", address)

    if entry.xml_list:
      for item in entry.xml_list:
        dict_to_xml(entry.xml_tag, item, element)

    xml_root.append(element)

  with open(f'BANK_{filename}_{DATE_FILENAME}.xml', 'wb') as f:
    xml.indent(xml_tree)
    f.write(b'<?xml version="1.0" encoding="UTF-8"?>\n')
    f.write(xml.tostring(xml_comment) + b'\n')
    xml_tree.write(f, encoding='utf-8', xml_declaration=False)

''' BInary Writing Functions '''
def create_binary_bank(filename: str, bankmeta: object, audiobank: object) -> None:
  bankmeta_bytes = bankmeta.to_bytes()
  bank_bytes = audiobank.to_bytes()

  with open(f'{filename}_{DATE_FILENAME}.bankmeta', 'wb') as bankmeta:
    bankmeta.write(bankmeta_bytes)

  with open(f'{filename}_{DATE_FILENAME}.zbank', 'wb') as bank:
    bank.write(bank_bytes)

''' Main Function '''
def main() -> None:
  filename = os.path.basename(os.path.splitext(sys.argv[1])[0])

  # This is temporary until I add proper file checking
  ''' From binary zbank and bankmeta '''
  # bank_bin     = sys.argv[1]
  # bankmeta_bin = sys.argv[2]

  # bank_data     = read_binary(bank_bin)
  # bankmeta_data = read_binary(bankmeta_bin)

  # bankmeta  = Bankmeta.from_bytes(bankmeta_data)
  # audiobank = Audiobank.from_bytes(bankmeta, bank_data)

  # create_xml_bank(filename, bankmeta, audiobank)

  ''' From XML '''
  xml_file = sys.argv[1]
  tree = xml.parse(xml_file)

  bank_element = tree.getroot()

  bankmeta = Bankmeta.from_xml(bank_element)
  audiobank = Audiobank.from_xml(bankmeta, bank_element)

  create_binary_bank(filename, bankmeta, audiobank)

if __name__ == '__main__':
  main()
