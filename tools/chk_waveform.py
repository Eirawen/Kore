import bpy
bpy.ops.wm.open_mainfile(filepath=r'\\wsl.localhost\Ubuntu\home\khaled\Kore\water_rigged.blend')
a=bpy.data.actions['waveform']
try:
    fcs=list(a.fcurves); src='action.fcurves'
except Exception:
    fcs=[fc for l in a.layers for st in l.strips for cb in st.channelbags for fc in cb.fcurves]; src='layers'
print('source:',src,'total fcurves:',len(fcs))
paths={}
for fc in fcs: paths[fc.data_path.split('"')[0]]=paths.get(fc.data_path.split('"')[0],0)+1
for k,v in sorted(paths.items(), key=lambda x:-x[1])[:8]: print('  %-40s %d'%(k,v))
sc=[fc for fc in fcs if fc.data_path=='scale']
print('SCALE fcurves:',len(sc))
for fc in sc:
    vals=[round(kp.co[1],3) for kp in fc.keyframe_points]
    print('  axis',fc.array_index,'keys',len(vals),'range',min(vals),'->',max(vals))
lo=[fc for fc in fcs if fc.data_path=='location']
print('LOCATION fcurves:',len(lo))
for fc in lo:
    vals=[round(kp.co[1],3) for kp in fc.keyframe_points]
    print('  axis',fc.array_index,'min',min(vals),'max',max(vals))
