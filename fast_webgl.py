import json

import flask.helpers


import ifcopenshell
import ifcopenshell.geom
from OCC.Display.WebGl.threejs_renderer import ThreejsRenderer
from OCC.Display.WebGl.flask_server import RenderConfig, RenderWraper, THREEJS_RELEASE, OCC_VERSION
from flask import Flask, send_from_directory
from flask.templating import render_template
import os
from OCC.Core import TopoDS
import numpy as np
import shutil

app = Flask(__name__)


render_cfg=RenderConfig(
    bg_gradient_color1='#161E39',
    bg_gradient_color2='#263650',
)
my_ren = ThreejsRenderer()





def openall(dir_path, settings):
    lst=[]
    for file in os.scandir("data"):

        f = ifcopenshell.open(dir_path)
        print(f'\nOPEN: {file.name}\n\n')
        lst.extend(list(ifcopenshell.geom.iterate(file_or_filename=f, settings=settings)))
    return lst


if __name__ == "__main__":

    """PythonOCC Demo Page"""
    my_ren._3js_shapes = {}
    my_ren._3js_edges = {}
    my_ren._3js_vertex = {}
    settings = ifcopenshell.geom.settings(USE_PYTHON_OPENCASCADE=True)
    print(my_ren._path)

    for file in os.scandir("data"):

        f = ifcopenshell.open(file.path)
        print(f'\nOPEN: {file.name}\n\n')

        for item in ifcopenshell.geom.iterate(file_or_filename=f, settings=settings):
            a,r,g,b = tuple(item.styles)[0]

            print(item.styles)
            try:
                my_ren.DisplayShape(item.geometry, color=(r,g,b))
                print("ok")
            except:
                print("bad")




    my_ren.render(addr='0.0.0.0', server_port=8183)
    """  
    @app.route('/')
    @app.route('/index')
    async def index():
     

        settings = ifcopenshell.geom.settings(USE_PYTHON_OPENCASCADE=True)
        print(my_ren._path)
        for file in os.scandir("data"):

            f = ifcopenshell.open(file.path)
            print(f'\nOPEN: {file.name}\n\n')
            col = tuple(np.round(np.random.random(3), 2))
            for item in ifcopenshell.geom.iterate(file_or_filename=f, settings=settings):

                my_ren.DisplayShape(item.geometry, color=col, export_edges=False)

            return my_ren.generate_html_file()
    #app.run(host='0.0.0.0', port=8181, debug=True)"""
