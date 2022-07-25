import copy
import itertools
import json
import os
import sys
import uuid

from OCC.Display.WebGl.threejs_renderer import spinning_cursor

from tools.cli import progressbar
from OCC.Core.Tesselator import ShapeTesselator
from OCC.Extend.TopologyUtils import is_edge, discretize_edge, discretize_wire, is_wire

data_scheme = {"metadata": {"version": None,
                            "tags": [],
                            },
               "uuid": None,
               "type": None,
               "data": {"attributes": {"position": {"itemSize": None,
                                                    "type": None,
                                                    "array": None}
                                       }
                        },
               "children": {}
               }


def tesselation(shape, export_edges=False, mesh_quality=0.5):
    tess = ShapeTesselator(shape)
    tess.Compute(compute_edges=export_edges,
                 mesh_quality=mesh_quality,
                 parallel=True)

    # update spinning cursor
    sys.stdout.write("\r%s mesh shape, %i triangles     " % (next(spinning_cursor()),

                                                             tess.ObjGetTriangleCount()))
    sys.stdout.flush()
    return tess


def export_edge_data_to_json(edge_hash, point_set, scheme=None):
    if scheme is None:
        scheme = data_scheme
    sch = copy.deepcopy(scheme)
    """ Export a set of points to a LineSegment buffergeometry
    """
    # first build the array of point coordinates
    # edges are built as follows:
    # points_coordinates  =[P0x, P0y, P0z, P1x, P1y, P1z, P2x, P2y, etc.]
    points_coordinates = []
    for point in point_set:
        for coord in point:
            points_coordinates.append(coord)
    # then build the dictionnary exported to json
    edges_data = {"metadata": {
        "generator": "MmodelIfc",
    },
        "uuid": edge_hash,
        "type": "BufferGeometry",
        "data": {"attributes": {"position": {"itemSize": 3,
                                             "type": "Float32Array",
                                             "array": points_coordinates}
                                }
                 },
    }

    sch |= edges_data

    return sch


def shaper(tess, export_edges, color=None, specular_color=None, shininess=None,
           transparency=None, line_color=None,
           line_width=None, scheme=None):
    if scheme is None:
        scheme = data_scheme
    sch = copy.deepcopy(scheme)
    shape_uuid = uuid.uuid4().hex

    shape_hash = "shp%s" % shape_uuid
    # tesselate

    # and also to JSON
    shape_dict = json.loads(tess.ExportShapeToThreejsJSONString(shape_uuid))
    shape_dict["metadata"]["generator"] = "MmodelIfc"

    shape_dict["children"] = {"edges": []}
    # draw edges if necessary
    if export_edges:
        # export each edge to a single json
        # get number of edges
        nbr_edges = tess.ObjGetEdgeCount()
        for i_edge in range(nbr_edges):
            # after that, the file can be appended
            str_to_write = ''
            edge_point_set = []
            nbr_vertices = tess.ObjEdgeGetVertexCount(i_edge)
            for i_vert in range(nbr_vertices):
                edge_point_set.append(tess.GetEdgeVertex(i_edge, i_vert))
            # write to file
            edge_hash = "edg%s" % uuid.uuid4().hex
            shape_dict["children"]["edges"].append(
                export_edge_data_to_json(edge_hash, edge_point_set, scheme=scheme))
    sch |= shape_dict
    return sch


def topo_converter(
        shape,
        *args,
        export_edges=False,
        color=(0.65, 0.65, 0.7),
        specular_color=(0.2, 0.2, 0.2),
        shininess=0.9,
        transparency=0.,
        line_color=(0, 0., 0.),
        line_width=1.,
        mesh_quality=1.,
        deflection=0.1,

        scheme=None,
        **kwargs
):
    # if the shape is an edge or a wire, use the related functions
    if scheme is None:
        scheme = data_scheme
    obj_hash = "edg%s" % uuid.uuid4().hex

    if is_edge(shape):
        print("discretize an edge")
        pnts = discretize_edge(shape, deflection, *args, **kwargs)
        data = export_edge_data_to_json(obj_hash, pnts, scheme=scheme)

    elif is_wire(shape):
        print("discretize a wire")
        pnts = discretize_wire(shape)

        data = export_edge_data_to_json(obj_hash, pnts, scheme=scheme)

    else:

        data = shaper(tesselation(shape, export_edges, mesh_quality),
                      export_edges,
                      color,
                      specular_color,
                      shininess,
                      transparency,
                      line_color,
                      line_width,

                      scheme=scheme)

    # store this edge hash

    return data


def normal_spaces(key):
    for symb in "_#%$^:;,.":
        key.replace(symb, " ")
    i = 0
    nk = ""
    while i < len(key):
        if key[i] == " ":
            if nk[-1] == " ":
                pass
            else:
                nk += key[i]
        else:
            nk += key[i]
        i += 1
    if nk[0] == " ":
        nk = nk[1:]
    if nk[-1] == " ":
        nk = nk[:len(nk) - 1]

    return nk

