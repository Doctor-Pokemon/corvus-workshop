"""MapEdit for the EXTENSION maps (header ids >= 540, records in the extension overlay table, see map_header_extension.py): add scripts, messages and a level-script header to a map without disturbing the rest.
Same interface as map_edit.MapEdit (message, script, groups [bgs, actors, warps, triggers], save). Extra: set_level_script(script_id) makes the map run that script on every entry (level-script row type 2).
Usage: ExtEdit(rom, 575) ... edit.save()"""
import struct
import ndspy.narc
import map_header_extension as ext
from map_edit import MapEdit


class ExtEdit(MapEdit):
    def __init__(self, rom, map_id):
        self.rom = rom
        ovs = rom.loadArm9Overlays({ext.OV})
        self.ov = ovs[ext.OV]
        self.d = bytearray(self.ov.data)
        self.at = ext.table_address(rom) - self.ov.ramAddress + 24 * (map_id - ext.NATIVE_COUNT)
        self.scripts = ndspy.narc.NARC(rom.getFileByName('a/0/1/2'))
        self.texts = ndspy.narc.NARC(rom.getFileByName('a/0/2/7'))
        self.events = ndspy.narc.NARC(rom.getFileByName('a/0/3/2'))
        from opening import events_decode
        from prototype import decode_messages
        sid, tid = struct.unpack_from('<H', self.d, self.at + 6)[0], struct.unpack_from('<H', self.d, self.at + 10)[0]
        eid = struct.unpack_from('<H', self.d, self.at + 16)[0]
        self.bank = bytes(self.scripts.files[sid])
        self.key, self.rows = decode_messages(self.texts.files[tid])
        self.groups = events_decode(self.events.files[eid])

    def set_level_script(self, script_id):
        """Entry script of this map: one level-script row (type 2), terminator, padding (same layout warden_schedule.py uses)."""
        old = struct.unpack_from('<H', self.d, self.at + 8)[0]
        assert bytes(self.scripts.files[old])[:1] == b'\0', 'the map already has level scripts'
        self.scripts.files.append(b'\x02' + struct.pack('<I', script_id) + b'\0\0\0')
        struct.pack_into('<H', self.d, self.at + 8, len(self.scripts.files) - 1)

    def save(self):
        from opening import events_encode
        from prototype import encode_messages
        self.scripts.files.append(bytes(self.bank))
        self.texts.files.append(encode_messages(self.key, self.rows))
        self.events.files.append(events_encode(self.groups))
        struct.pack_into('<H', self.d, self.at + 6, len(self.scripts.files) - 1)
        struct.pack_into('<H', self.d, self.at + 10, len(self.texts.files) - 1)
        struct.pack_into('<H', self.d, self.at + 16, len(self.events.files) - 1)
        self.rom.setFileByName('a/0/1/2', self.scripts.save())
        self.rom.setFileByName('a/0/2/7', self.texts.save())
        self.rom.setFileByName('a/0/3/2', self.events.save())
        self.ov.data = self.d
        self.rom.files[self.ov.fileID] = self.ov.save(compress=False)
