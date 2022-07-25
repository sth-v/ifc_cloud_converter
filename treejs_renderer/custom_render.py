from treejs_renderer.source import *
from fastapi.responses import HTMLResponse
from fastapi import templating
import shutil
import ifcopenshell
import ifcopenshell.geom

class CustomRender(ThreejsRenderer):
    def __init__(self, curdir, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.curdir = curdir
        self._dir = self.curdir + "/tmpinfo.json"
        self.data = None
        with open(self._dir, "rb") as f:
            self.data |= json.load(f)

    def generate_html_file(self):
        """ Generate the HTML file to be rendered by the web browser
        """
        global BODY_PART0
        # loop over shapes to generate html shapes stuff
        # the following line is a list that will help generating the string
        # using "".join()
        shape_string_list = []
        shape_string_list.append("loader = new THREE.BufferGeometryLoader();\n")
        shape_idx = 0
        for shape_hash in self._3js_shapes:
            # get properties for this shape
            export_edges, color, specular_color, shininess, transparency, line_color, line_width = self._3js_shapes[
                shape_hash]
            # creates a material for the shape
            shape_string_list.append('\t\t\t%s_phong_material = new THREE.MeshPhongMaterial({' % shape_hash)
            shape_string_list.append('color:%s,' % color_to_hex(color))
            shape_string_list.append('specular:%s,' % color_to_hex(specular_color))
            shape_string_list.append('shininess:%g,' % shininess)
            # force double side rendering, see issue #645
            shape_string_list.append('side: THREE.DoubleSide,')
            if transparency > 0.:
                shape_string_list.append('transparent: true, premultipliedAlpha: true, opacity:%g,' % transparency)
            # var line_material = new THREE.LineBasicMaterial({color: 0x000000, linewidth: 2});
            shape_string_list.append('});\n')
            # load json geometry files
            shape_string_list.append("\t\t\tloader.load('%s.json', function(geometry) {\n" % shape_hash)
            shape_string_list.append("\t\t\t\tmesh = new THREE.Mesh(geometry, %s_phong_material);\n" % shape_hash)
            # enable shadows for object
            shape_string_list.append("\t\t\t\tmesh.castShadow = true;\n")
            shape_string_list.append("\t\t\t\tmesh.receiveShadow = true;\n")
            # add mesh to scene
            shape_string_list.append("\t\t\t\tscene.add(mesh);\n")
            # last shape, we request for a fit_to_scene
            if shape_idx == len(self._3js_shapes) - 1:
                shape_string_list.append("\tfit_to_scene();});\n")
            else:
                shape_string_list.append("\t\t\t});\n\n")
            shape_idx += 1
        # Process edges
        edge_string_list = []
        for edge_hash in self._3js_edges:
            color, line_width = self._3js_edges[edge_hash]
            edge_string_list.append("\tloader.load('%s.json', function(geometry) {\n" % edge_hash)
            edge_string_list.append("\tline_material = new THREE.LineBasicMaterial({color: %s, linewidth: %s});\n" % (
                (color_to_hex(color), line_width)))
            edge_string_list.append("\tline = new THREE.Line(geometry, line_material);\n")
            # add mesh to scene
            edge_string_list.append("\tscene.add(line);\n")
            edge_string_list.append("\t});\n")
        # write the string for the shape
        htmltext = "<!DOCTYPE HTML>\n"
        htmltext += "<html lang='en'>"
        # header
        htmltext += HTMLHeader().get_str()
        # body
        BODY_PART0 = BODY_PART0.replace('@VERSION@', OCC_VERSION)
        htmltext += BODY_PART0
        htmltext += HTMLBody_Part1().get_str()
        htmltext += "".join(shape_string_list)
        htmltext += "".join(edge_string_list)
        # then write header part 2
        htmltext += BODY_PART2
        htmltext += "</html>\n"
        return htmltext

    def remove_temp(self):
        data = {}

        dir_ = self.curdir + "/tmpinfo.json"

        shutil.rmtree(data["temp"], ignore_errors=True)
        print(f'previous tmp dir {data["temp"]} removed')
        self.data['temp'] = self._path
        with open(dir_, "w") as f:
            json.dump(data, f, indent=3)
