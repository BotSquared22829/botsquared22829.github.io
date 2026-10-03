"""Read MP4 structural metadata without decoding or external dependencies."""
import struct,json,pathlib,sys
p=pathlib.Path(sys.argv[1]); b=p.read_bytes()
def boxes(start,end):
 while start+8<=end:
  size,kind=struct.unpack_from('>I4s',b,start); head=8
  if size==1: size=struct.unpack_from('>Q',b,start+8)[0]; head=16
  if size==0:size=end-start
  if size<head or start+size>end:break
  yield kind,start+head,start+size
  start+=size
result={'path':str(p),'bytes':len(b),'tracks':[],'top_level_atoms':[k.decode() for k,_,_ in boxes(0,len(b))]}
for k,a,z in boxes(0,len(b)):
 if k!=b'moov':continue
 for k2,a2,z2 in boxes(a,z):
  if k2==b'mvhd':
   ver=b[a2]; base=a2+(20 if ver else 12); scale=struct.unpack_from('>I',b,base)[0]; dur=struct.unpack_from('>Q' if ver else '>I',b,base+4)[0]; result['duration_seconds']=dur/scale
  if k2!=b'trak':continue
  track={}
  def scan(lo,hi):
   for t,x,y in boxes(lo,hi):
    if t in (b'mdia',b'minf',b'stbl'):scan(x,y)
    if t==b'hdlr':track['type']=b[x+8:x+12].decode()
    if t==b'tkhd':track['width']=struct.unpack_from('>I',b,y-8)[0]/65536;track['height']=struct.unpack_from('>I',b,y-4)[0]/65536
    if t==b'stsz':track['sample_count']=struct.unpack_from('>I',b,x+8)[0]
    if t==b'stss':track['sync_sample_count']=struct.unpack_from('>I',b,x+4)[0]
    if t==b'stsd':track['codec']=b[x+12:x+16].decode(errors='replace')
  scan(a2,z2);result['tracks'].append(track)
assert result.get('duration_seconds')==8,result
assert any(t.get('type')=='vide' and t.get('sample_count')==192 and t.get('width')==1280 and t.get('height')==720 for t in result['tracks']),result
if '--scroll' in sys.argv:
 assert result['top_level_atoms'].index('moov')<result['top_level_atoms'].index('mdat'),result
 for track in result['tracks']:
  if track.get('type')=='vide':
   # MP4 omits stss when every sample is a sync sample.
   assert track.get('sync_sample_count',track['sample_count'])==track['sample_count'],result
 result['scroll_encoding']='All frames independently seekable; metadata precedes media'
print(json.dumps(result,indent=2))
