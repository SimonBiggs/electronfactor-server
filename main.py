# Copyright (C) 2016 Simon Biggs
# This program is free software: you can redistribute it and/or
# modify it under the terms of the GNU Affero General Public
# License as published by the Free Software Foundation, either
# version 3 of the License, or (at your option) any later version.
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# Affero General Public License for more details.
# You should have received a copy of the GNU Affero General Public
# License along with this program. If not, see
# http://www.gnu.org/licenses/.

"""Electron insert REST API tornado server."""

import os

import numpy as np
import json

import tornado.escape
import tornado.ioloop
import tornado.web


from electroninserts import (
    parameterise_insert_with_visual_alignment, create_transformed_mesh)


class Root(tornado.web.RequestHandler):
    """Documentation."""

    def set_default_headers(self):
        self.set_header("Access-Control-Allow-Origin", "*")
        self.set_header('Access-Control-Allow-Methods', 'GET')

    def get(self):
        """Documentation."""

        self.render("index.html")


class Parameterise(tornado.web.RequestHandler):
    """REST API for parametering inserts."""
    

    def set_default_headers(self):
        self.set_header("Access-Control-Allow-Origin", "*")
        self.set_header('Access-Control-Allow-Methods', 'POST')
        

    def post(self):
        """REST API for parametering inserts."""
        
        received = json.loads(self.request.body.decode())
        x = received['x']
        y = received['y']

        (
            width, length, circle_centre, x_shift, y_shift, rotation_angle
        ) = parameterise_insert_with_visual_alignment(x, y)

        respond = {
            'width': np.round(width, decimals=2),
            'length': np.round(length, decimals=2),
            'circle_centre': np.round(circle_centre, decimals=2).tolist(),
            'x_shift': np.round(x_shift, decimals=2),
            'y_shift': np.round(y_shift, decimals=2),
            'rotation_angle': np.round(rotation_angle, decimals=4)
        }
        
        self.write(respond)
        

class Model(tornado.web.RequestHandler):
    """REST API for modelling inserts."""
    
    
    def set_default_headers(self):
        self.set_header("Access-Control-Allow-Origin", "*")
        self.set_header('Access-Control-Allow-Methods', 'POST')
        

    def post(self):
        """REST API for modelling inserts."""

        received = json.loads(self.request.body.decode())
        width = np.array(received['width']).astype(float)
        length = np.array(received['length']).astype(float)
        factor = np.array(received['factor']).astype(float)

        mesh_width, mesh_length, mesh_factor = create_transformed_mesh(
            width, length, factor)

        respond = {
            'mesh_width': np.round(mesh_width, decimals=1).tolist(),
            'mesh_length': np.round(mesh_length, decimals=1).tolist(),
            'mesh_factor': np.round(mesh_factor, decimals=4).tolist()
        }

        self.write(respond)


def main():
    app = tornado.web.Application([
            ('/', Root),
            ('/parameterise', Parameterise),
            ('/model', Model)],
        template_path=os.path.join(os.path.dirname(__file__), "templates")
    )

    port = int(os.environ.get("PORT", 5000))

    app.listen(port)
    tornado.ioloop.IOLoop.current().start()


if __name__ == "__main__":
    main()
