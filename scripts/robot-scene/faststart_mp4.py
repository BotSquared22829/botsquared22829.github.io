"""Move an MP4's metadata before its media payload for progressive web loading."""
import struct
from pathlib import Path

def boxes(data,start=0,end=None):
 end=len(data) if end is None else end
 while start<end:
  size,kind=struct.unpack_from('>I4s',data,start);header=8
  if size==1:size=struct.unpack_from('>Q',data,start+8)[0];header=16
  if size==0:size=end-start
  assert size>=header and start+size<=end
  yield kind,start,start+header,start+size
  start+=size

def faststart(path):
 path=Path(path);data=path.read_bytes();atoms=list(boxes(data))
 moov=next(a for a in atoms if a[0]==b'moov')
 mdat=next(a for a in atoms if a[0]==b'mdat')
 if moov[1]<mdat[1]:return
 assert atoms[0][0]==b'ftyp'
 insert=atoms[0][3];length=moov[3]-moov[1]
 metadata=bytearray(data[moov[1]:moov[3]])
 def patch(start,end):
  for kind,_,body,stop in boxes(metadata,start,end):
   if kind in (b'moov',b'trak',b'mdia',b'minf',b'stbl'):patch(body,stop)
   elif kind in (b'stco',b'co64'):
    count=struct.unpack_from('>I',metadata,body+4)[0]
    fmt,width=('>I',4) if kind==b'stco' else ('>Q',8)
    for i in range(count):
     pos=body+8+i*width;offset=struct.unpack_from(fmt,metadata,pos)[0]
     assert not moov[1]<=offset<moov[3]
     if insert<=offset<moov[1]:struct.pack_into(fmt,metadata,pos,offset+length)
 patch(0,len(metadata))
 result=data[:insert]+metadata+data[insert:moov[1]]+data[moov[3]:]
 assert len(result)==len(data)
 temp=path.with_suffix('.faststart.tmp');temp.write_bytes(result);temp.replace(path)

if __name__=='__main__':
 import sys
 faststart(sys.argv[1])
