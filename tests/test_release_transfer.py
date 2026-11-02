import hashlib
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import release_transfer as transfer


class ReleaseTransferTests(unittest.TestCase):
    def test_manifest_rejects_foreign_repository_and_paths(self):
        data={'repository':transfer.REPO,'tag':transfer.TAG,'files':[dict(name=name,sha256=digest,bytes=1,chunks=[dict(name=f'transfer-v0.3.0-{digest[:12]}-0000.part',bytes=1,sha256='0'*64)]) for name,digest in transfer.ALLOWED.items()]}
        transfer.validate(data)
        data['repository']='someone/another-project'
        with self.assertRaises(ValueError): transfer.validate(data)
        data['repository']=transfer.REPO
        data['files'][0]['chunks'][0]['name']='../escape'
        with self.assertRaises(ValueError): transfer.validate(data)

    def test_join_detects_corruption_and_keeps_existing_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); incoming=root/'incoming'; incoming.mkdir(); out=root/'out'; out.mkdir()
            content=b'authorized payload'
            expected=hashlib.sha256(content).hexdigest()
            chunk=incoming/'part'; chunk.write_bytes(content)
            item=dict(name='installer',sha256=expected,chunks=[dict(name='part',bytes=len(content),sha256=expected)])
            transfer.join(item,incoming,out)
            self.assertEqual((out/'installer').read_bytes(),content)
            chunk.write_bytes(b'x'*len(content))
            with self.assertRaises(ValueError): transfer.join(item,incoming,out)
            self.assertEqual((out/'installer').read_bytes(),content)
            self.assertFalse((out/'installer.partial').exists())
            chunk.write_bytes(content); (out/'installer').write_bytes(b'user file')
            with self.assertRaises(FileExistsError): transfer.join(item,incoming,out)
            self.assertEqual((out/'installer').read_bytes(),b'user file')


if __name__=='__main__': unittest.main()
