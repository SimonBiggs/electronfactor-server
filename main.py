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
from copy import copy

import numpy as np
import json

import tornado.escape
import tornado.ioloop
import tornado.web
import tornado.concurrent
import tornado.gen
from tornado.concurrent import Future
from multiprocessing import Process, Manager

import time

from electroninserts import (
    parameterise_insert_with_visual_alignment, create_transformed_mesh,
    calculate_width, calculate_length)
    

manager = Manager()
current_results_storage = {}
process_storage = {}
# future_storage = manager.dict()
  

def run_parameterisation(current_results, x, y, 
                         circle_callback=None,
                         visual_ellipse_callback=None,
                         complete_parameterisation_callback=None):
    (
        width, length, circle_centre, x_shift, y_shift, rotation_angle
    ) = parameterise_insert_with_visual_alignment(
        x, y, circle_callback=circle_callback, 
        visual_ellipse_callback=visual_ellipse_callback,
        complete_parameterisation_callback=complete_parameterisation_callback)

    current_results["width"] = width
    current_results["length"] = length
    current_results["circle_centre"] = circle_centre
    current_results["x_shift"] = x_shift
    current_results["y_shift"] = y_shift
    current_results["rotation_angle"] = rotation_angle
    current_results["complete"] = True
    
    # future_storage[key].set_result(current_results_storage[key])
   

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
        
        key = json.dumps({
            "x": x,
            "y": y
        })
        
        # print(current_results_storage)
        
        if key in current_results_storage:
        
            # current_result = yield future_storage[key]
            current_result = copy(current_results_storage[key])
            
            if "complete" in current_result:
                if current_result["complete"]:
                    del current_results_storage[key]
            
        else:
            current_results_storage[key] = manager.dict()
            current_results_storage[key]["width"] = None
            current_results_storage[key]["length"] = None
            current_results_storage[key]["circle_centre"] = None
            current_results_storage[key]["x_shift"] = 0
            current_results_storage[key]["y_shift"] = 0
            current_results_storage[key]["rotation_angle"] = -np.pi/4
            current_results_storage[key]["complete"] = False
            
            # future_storage[key] = Future()
                     
            
            def circle_callback(circle_centre, f, accept):
                if accept:
                    width = calculate_width(x, y, circle_centre)
                    length = calculate_length(x, y, width)
                    
                    current_results_storage[key]["circle_centre"] = circle_centre
                    current_results_storage[key]["width"] = width
                    current_results_storage[key]["length"] = length
                # future_storage[key].set_result(current_results_storage[key])
                
                
            def complete_parameterisation_callback(width, length, 
                                                   circle_centre):
                current_results_storage[key]["circle_centre"] = circle_centre
                current_results_storage[key]["width"] = width
                current_results_storage[key]["length"] = length
                
                
            def visual_ellipse_callback(visuals, f, accept):
                if accept:
                    x_shift, y_shift, rotation_angle = visuals
                    current_results_storage[key]["x_shift"] = x_shift
                    current_results_storage[key]["y_shift"] = y_shift
                    current_results_storage[key]["rotation_angle"] = rotation_angle
                    # future_storage[key].set_result(current_results_storage[key])
                
            
            process_storage[key] = Process(
                target=run_parameterisation,
                args=(
                    current_results_storage[key], x, y),
                kwargs={
                    'circle_callback': circle_callback,
                    'visual_ellipse_callback': visual_ellipse_callback,
                    'complete_parameterisation_callback': complete_parameterisation_callback})
            process_storage[key].start()
            
            current_result = copy(current_results_storage[key])
            
            
        circle = None
        ellipse = None
        
        width = current_result["width"]
        circle_centre = current_result["circle_centre"]
        
        length = current_result["length"] 
        x_shift = current_result["x_shift"]
        y_shift = current_result["y_shift"]
        rotation_angle = current_result["rotation_angle"]
        
        if (width is not(None)) and (circle_centre is not(None)):
            t = np.linspace(0, 2 * np.pi)
            circle = {
                "x": np.round(
                    width / 2 * np.sin(t) + circle_centre[0],
                    decimals=2
                ).tolist(),
                "y": np.round(
                    width / 2 * np.cos(t) + circle_centre[1],
                    decimals=2
                ).tolist()
            }
            
            width = np.round(width, decimals=2)
            
            if (length is not(None)):
                rotation_matrix = np.array([
                        [np.cos(rotation_angle), -np.sin(rotation_angle)],
                        [np.sin(rotation_angle), np.cos(rotation_angle)]
                    ])

                ellipse = np.array([
                        length / 2 * np.sin(t),
                        width / 2 * np.cos(t)
                    ]).T

                rotated_ellipse = ellipse @ rotation_matrix

                translated_ellipse = (
                    rotated_ellipse + np.array([y_shift, x_shift]))
                ellipse = {
                    "x": np.round(
                        translated_ellipse[:,1],
                        decimals=2
                    ).tolist(),
                    "y": np.round(
                        translated_ellipse[:,0],
                        decimals=2
                    ).tolist()
                }
                
                length = np.round(length, decimals=2)
        
        complete = current_result["complete"]

        respond = {
            'width': width,
            'length': length,
            'circle': circle,
            'ellipse': ellipse,
            'complete': complete
        }
        
        self.write(respond)


class Root(tornado.web.RequestHandler):
    """Documentation."""

    def set_default_headers(self):
        self.set_header("Access-Control-Allow-Origin", "*")
        self.set_header('Access-Control-Allow-Methods', 'GET')

    def get(self):
        """Documentation."""

        self.render("index.html")
        

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

        width_valid = np.invert(np.isnan(width))
        width = width[width_valid]
        length = length[width_valid]
        factor = factor[width_valid]
        
        length_valid = np.invert(np.isnan(length)) & (length >= width)
        width = width[length_valid]
        length = length[length_valid]
        factor = factor[length_valid]
        
        factor_valid = np.invert(np.isnan(factor))
        width = width[factor_valid]
        length = length[factor_valid]
        factor = factor[factor_valid]

        model_width, model_length, model_factor = create_transformed_mesh(
            width, length, factor)
            
        model_width_mesh, model_length_mesh = np.meshgrid(
            model_width, model_length)
            
        flat_model_width = np.ravel(model_width_mesh)
        flat_model_length = np.ravel(model_length_mesh)
        flat_model_factor = np.ravel(model_factor)
        
        valid_data = np.invert(np.isnan(flat_model_factor))
        
        final_model_width = flat_model_width[valid_data]
        final_model_length = flat_model_length[valid_data]
        final_model_factor = flat_model_factor[valid_data]

        respond = {
            'model_width': np.round(final_model_width, decimals=1).tolist(),
            'model_length': np.round(final_model_length, decimals=1).tolist(),
            'model_factor': np.round(final_model_factor, decimals=4).tolist()
        }

        self.write(respond)


class WakeUp(tornado.web.RequestHandler):
    """Dummy GET call to wake up the server."""
    
    def set_default_headers(self):
        self.set_header("Access-Control-Allow-Origin", "*")
        self.set_header('Access-Control-Allow-Methods', 'GET')
        
    def get(self):
        """Documentation."""

        self.write("I'm awake, I'm awake. ... can I have a coffee?")


def main():
    app = tornado.web.Application([
            ('/', Root),
            ('/parameterise', Parameterise),
            ('/model', Model),
            ('/wakeup', WakeUp)],
        template_path=os.path.join(os.path.dirname(__file__), "templates")
    )

    port = int(os.environ.get("PORT", 5000))

    app.listen(port)
    tornado.ioloop.IOLoop.current().start()


if __name__ == "__main__":
    main()
