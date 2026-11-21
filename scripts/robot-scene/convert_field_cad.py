"""Convert FIRST's official BIOBUZZ STEP assembly to a colored render GLB.

Run with a CadQuery 2.6 environment. Download the archive linked in SOURCE_URL
and extract field-cad-step.step into output/robot-scene/field-cad/ first.
Keep the full field at its source dimensions; crop only the render camera.
"""
import hashlib
import json
from pathlib import Path

import cadquery as cq
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.IFSelect import IFSelect_RetDone
from OCP.Message import Message_ProgressRange
from OCP.RWGltf import RWGltf_CafWriter
from OCP.STEPCAFControl import STEPCAFControl_Reader
from OCP.TCollection import TCollection_AsciiString, TCollection_ExtendedString
from OCP.TColStd import TColStd_IndexedDataMapOfStringString
from OCP.TDF import TDF_LabelSequence
from OCP.TDocStd import TDocStd_Document
from OCP.XCAFDoc import XCAFDoc_DocumentTool, XCAFDoc_ShapeTool

BASE = Path(__file__).resolve().parents[2]
OUT = BASE / 'output/robot-scene/field-cad'
SOURCE = OUT / 'field-cad-step.step'
SOURCE_URL = 'https://ftc-resources.firstinspires.org/ftc/field/field-cad-step'


def main():
    print('Reading official BIOBUZZ field STEP', flush=True)
    # Read XCAF directly: the official assembly legitimately repeats instance
    # names, which CadQuery's higher-level Assembly importer rejects.
    reader = STEPCAFControl_Reader()
    reader.SetColorMode(True)
    reader.SetNameMode(True)
    assert reader.ReadFile(str(SOURCE)) == IFSelect_RetDone
    document = TDocStd_Document(TCollection_ExtendedString('BinXCAF'))
    assert reader.Transfer(document)
    shape_tool = XCAFDoc_DocumentTool.ShapeTool_s(document.Main())
    roots = TDF_LabelSequence()
    shape_tool.GetFreeShapes(roots)
    shapes = [XCAFDoc_ShapeTool.GetShape_s(roots.Value(i)) for i in range(1, roots.Length() + 1)]
    bounds = cq.Compound.makeCompound([cq.Shape.cast(shape) for shape in shapes]).BoundingBox()
    dimensions = [bounds.xlen, bounds.ylen, bounds.zlen]
    print('STEP dimensions in mm:', dimensions, flush=True)
    assert max(dimensions) > 3600, 'The complete field must retain its physical dimensions'
    print('Tessellating field with 0.35 mm linear tolerance', flush=True)
    for shape in shapes:
        mesh = BRepMesh_IncrementalMesh(shape, .35, False, .25, False)
        assert mesh.IsDone()
    # This official STEP is already Y-up (tile thickness is along Y), as is
    # glTF. Preserve the axes; Blender's importer converts Y-up to Z-up.
    XCAFDoc_DocumentTool.SetLengthUnit_s(document, .001)
    writer = RWGltf_CafWriter(TCollection_AsciiString(str(OUT / 'biobuzz-field.glb')), True)
    writer.SetMergeFaces(True)
    assert writer.Perform(document, TColStd_IndexedDataMapOfStringString(), Message_ProgressRange())
    manifest = {
        'source_page': 'https://ftc-resources.firstinspires.org/ftc/field',
        'download_url': SOURCE_URL,
        'onshape_url': 'https://cad.onshape.com/documents/a355e772e3d24813de7852ee/w/f106353168f1f92100b81259/e/95d1e1e442b4138cccaf2d73',
        'version': 'v26-27.2 (2026-09-15)',
        'step_sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        'cadquery_version': cq.__version__,
        'imported_units': 'millimeters',
        'gltf_units': 'meters',
        'source_up_axis': 'Y',
        'source_bounds_mm': [[bounds.xmin, bounds.ymin, bounds.zmin], [bounds.xmax, bounds.ymax, bounds.zmax]],
        'source_dimensions_mm': dimensions,
        'mesh_tolerance_mm': .35,
        'glb_sha256': hashlib.sha256((OUT / 'biobuzz-field.glb').read_bytes()).hexdigest(),
    }
    (OUT / 'source.json').write_text(json.dumps(manifest, indent=2))
    print('Field conversion complete', flush=True)


if __name__ == '__main__':
    main()
