#====================== BEGIN GPL LICENSE BLOCK ======================
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
#======================= END GPL LICENSE BLOCK ========================

# <pep8 compliant>
bl_info = {
    "name": "Image Cropper",
    "author": "Dalai Felinto",
    "version": (0, 9),
    "blender": (2, 7, 7),
    "location": "View 3D Tools",
    "description": "",
    "warning": "",
    "wiki_url": "",
    "tracker_url": "",
    "category": "3D View"}


import bpy

from mathutils import (
        Vector,
        )

from bgl import *

TODO = False

class VIEW3D_OT_ImageCrop(bpy.types.Operator):
    """"""
    bl_idname = "view3d.image_crop"
    bl_label = "Image Crop"

    _handle_draw = None
    _vertices = [None, None]
    _is_drag = False
    _is_snap = False
    _image = None
    _quad = [None, None, None, None]

    @classmethod
    def poll(cls, context):
        ob = context.object
        return ob and ob.type == 'MESH' and ob.mode == 'OBJECT'

    @classmethod
    def _handle_add(cls):
        cls._handle_draw = bpy.types.SpaceView3D.draw_handler_add(
            cls._draw_callback_px, tuple(), 'WINDOW', 'POST_PIXEL')

    @classmethod
    def _handle_remove(cls):
        if cls._handle_draw is not None:
            bpy.types.SpaceView3D.draw_handler_remove(cls._handle_draw, 'WINDOW')

        cls._handle_draw = None

    @classmethod
    def _click(cls, vertex, report):
        if cls._is_drag:
            cls._vertices[1] = vertex
            cls._crop()
            cls._reset()
            return {'FINISHED'}

        else:
            cls._vertices[0] = vertex
            cls._vertices[1] = vertex
            cls._is_drag = True
            return {'RUNNING_MODAL'}

    @classmethod
    def _move(cls, vertex):
        if cls._is_drag:
            cls._vertices[1] = vertex
        else:
            cls._vertices[0] = vertex

    @classmethod
    def _crop(cls):
        TODO # crop image
        print("Cropping ...")

    def modal(self, context, event):
        vertex = VIEW3D_OT_ImageCrop._getVertex(event)

        if context.area: # not available if other window-type is fullscreen
            context.area.tag_redraw()

        if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
            return VIEW3D_OT_ImageCrop._click(vertex, self.report)

        elif event.type == 'MOUSEMOVE':
            VIEW3D_OT_ImageCrop._move(vertex)
            return {'RUNNING_MODAL'}

        elif event.type in {'RIGHTMOUSE', 'ESC'}:
            self.cancel(context)
            return {'CANCELLED'}

        return {'RUNNING_MODAL'}

    def cancel(self, context):
        VIEW3D_OT_ImageCrop._reset()

    @classmethod
    def _reset(cls):
        cls._handle_remove()
        cls._handle_draw = None
        cls._vertices = [None, None]
        cls._quad = [None, None, None, None]
        cls._is_drag = False
        cls._is_snap = False

    def invoke(self, context, event):
        if context.area.type == 'VIEW_3D':

            # return error
            err_message = VIEW3D_OT_ImageCrop._init(context, event)
            if err_message:
                self.report({'ERROR'}, err_message)
                return {'CANCELLED'}

            if context.area:
                context.area.tag_redraw()

            context.window_manager.modal_handler_add(self)
            return {'RUNNING_MODAL'}

        else:
            self.report({'WARNING'}, "View3D not found, cannot run operator")
            return {'CANCELLED'}

    @classmethod
    def _init(cls, context, event):
        cls._reset()
        cls._handle_add()
        modelview_matrix, projection_matrix, viewport = cls._getMatrices(context)
        cls._setupQuad(context.object, modelview_matrix, projection_matrix, viewport)
        cls._vertices[0] = cls._getVertex(event)
        return None

    @staticmethod
    def _getMatrices(context):
        region = context.region
        view3d = context.region_data

        modelview_matrix = view3d.view_matrix
        projection_matrix = view3d.perspective_matrix
        viewport = 0, 0, region.width, region.height

        # convert them to buffer
        modelview_matrix_buf = Buffer(GL_DOUBLE, [4, 4])
        projection_matrix_buf = Buffer(GL_DOUBLE, [4, 4])
        viewport_buf = Buffer(GL_INT, 4)

        for i in range(4):
            viewport_buf[i] = viewport[i]

            for j in range(4):
                modelview_matrix_buf[i][j] = modelview_matrix[i][j]
                projection_matrix_buf[i][j] = projection_matrix[i][j]

        return modelview_matrix_buf, projection_matrix_buf, viewport_buf

    @classmethod
    def _setupQuad(cls, ob, modelview_matrix, projection_matrix, viewport):
        mesh = ob.data
        matrix_world = ob.matrix_world
        verts = [matrix_world * vert.co for vert in mesh.vertices]

        gl_buffer = (
                Buffer(GL_DOUBLE, 1, [0.0]),
                Buffer(GL_DOUBLE, 1, [0.0]),
                Buffer(GL_DOUBLE, 1, [1.0]),
                )

        quad = []
        for v in verts:
            gluProject(v.x, v.y, v.z, modelview_matrix, projection_matrix, viewport, gl_buffer[0], gl_buffer[1], gl_buffer[2])
            quad.append((gl_buffer[0][0], gl_buffer[1][0]))

        quad = cls._sortVertices(quad)
        cls._quad = []
        for v in quad:
            cls._quad.append(Vector(v))

    @staticmethod
    def _sortVertices(points):
        """
        Computes the convex hull of a set of 2D points. 
        Input: an iterable sequence of (x, y) pairs representing the points.
        Output: a list of vertices of the convex hull in counter-clockwise order,
          starting from the vertex with the lexicographically smallest coordinates.
        Implements Andrew's monotone chain algorithm. O(n log n) complexity.
        http://en.wikibooks.org/wiki/Algorithm_Implementation/Geometry/Convex_hull/Monotone_chain#Python
        """
        # Convert x and y to an interable list of tuples

        # Sort the points lexicographically (tuples are compared lexicographically).
        # Remove duplicates to detect the case we have just one unique point.
        points = sorted(set(points))

        # Boring case: no points or a single point, possibly repeated multiple times.
        if len(points) <= 1:
            return points

        # 2D cross product of OA and OB vectors, i.e. z-component of their 3D cross product.
        # Returns a positive value, if OAB makes a counter-clockwise turn,
        # negative for clockwise turn, and zero if the points are collinear.
        def cross(o, a, b):
            return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

        # Build lower hull
        lower = []
        for p in points:
            while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
                lower.pop()
            lower.append(p)

        # Build upper hull
        upper = []
        for p in reversed(points):
            while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
                upper.pop()
            upper.append(p)

        # Concatenation of the lower and upper hulls gives the convex hull.
        # Last point of each list is omitted because it is repeated at the beginning of the other list.
        chull = lower[:-1] + upper[:-1]
        return chull

    @classmethod
    def _getVertex(cls, event):
        SNAP_DISTANCE = 500

        vertex = Vector((event.mouse_region_x, event.mouse_region_y))

        if event.alt:
            cls._is_snap = False
            return cls._fitInQuad(vertex)

        for v in cls._quad:
            if (v - vertex).length_squared < SNAP_DISTANCE:
                cls._is_snap = True
                return v

        cls._is_snap = False
        return cls._fitInQuad(vertex)

    @classmethod
    def _fitInQuad(cls, vertex):
        # crop
        x = vertex[0]
        x = min(cls._quad[1].x, x)
        x = max(cls._quad[0].x, x)

        y = vertex[1]
        y = min(cls._quad[3].y, y)
        y = max(cls._quad[0].y, y)

        return x, y

    @classmethod
    def _draw_callback_px(cls):
        if cls._is_drag:
            return cls._draw_drag()

        else:
            return cls._draw_initial()

    @classmethod
    def _draw_drag(cls):
        glEnable(GL_BLEND)
        glColor4f(0.0, 0.0, 0.0, 0.5)
        glLineWidth(2)

        ax = int(cls._vertices[0][0])
        ay = int(cls._vertices[0][1])
        bx = int(cls._vertices[1][0])
        by = int(cls._vertices[1][1])

        glBegin(GL_LINE_STRIP)
        glVertex2i(ax, ay)
        glVertex2i(bx, ay)
        glVertex2i(bx, by)
        glVertex2i(ax, by)
        glVertex2i(ax, ay)
        glEnd()

        # restore opengl defaults
        glLineWidth(1)
        glDisable(GL_BLEND)
        glColor4f(0.0, 0.0, 0.0, 1.0)

        # sorted selection
        selection = cls._sortVertices(((ax, ay), (bx, ay), (bx, by), (ax, by)))

        if len(selection) != 4:
            return

        # draw quad
        glEnable(GL_BLEND)
        glColor4f(1.0, 0.0, 0.0, 0.5)

        glBegin(GL_QUADS)
        # A: o0, i0, i3, o3
        glVertex2i(int(cls._quad[0][0]), int(cls._quad[0][1]))
        glVertex2i(int(selection[0][0]), int(selection[0][1]))
        glVertex2i(int(selection[3][0]), int(selection[3][1]))
        glVertex2i(int(cls._quad[3][0]), int(cls._quad[3][1]))
        # B: o1, i1, i0, o0
        glVertex2i(int(cls._quad[1][0]), int(cls._quad[1][1]))
        glVertex2i(int(selection[1][0]), int(selection[1][1]))
        glVertex2i(int(selection[0][0]), int(selection[0][1]))
        glVertex2i(int(cls._quad[0][0]), int(cls._quad[0][1]))
        # C: o2, i2, i1, o1
        glVertex2i(int(cls._quad[2][0]), int(cls._quad[2][1]))
        glVertex2i(int(selection[2][0]), int(selection[2][1]))
        glVertex2i(int(selection[1][0]), int(selection[1][1]))
        glVertex2i(int(cls._quad[1][0]), int(cls._quad[1][1]))
        # D: o3, i3, i2, o2
        glVertex2i(int(cls._quad[3][0]), int(cls._quad[3][1]))
        glVertex2i(int(selection[3][0]), int(selection[3][1]))
        glVertex2i(int(selection[2][0]), int(selection[2][1]))
        glVertex2i(int(cls._quad[2][0]), int(cls._quad[2][1]))
        glEnd()

        # restore opengl defaults
        glDisable(GL_BLEND)
        glColor4f(0.0, 0.0, 0.0, 1.0)

        if cls._is_snap:
            cls._draw_snap(cls._vertices[1])

    @classmethod
    def _draw_initial(cls):

        glEnable(GL_BLEND)

        glColor4f(0.0, 0.0, 0.0, 0.5)

        y = int(cls._vertices[0][1])
        x = int(cls._vertices[0][0])

        glBegin(GL_LINES)

        # horizontal line
        glVertex2i(int(cls._quad[0].x), y)
        glVertex2i(int(cls._quad[2].x), y)

        # vertical line
        glVertex2i(x, int(cls._quad[1].y))
        glVertex2i(x, int(cls._quad[3].y))

        glEnd()

        # restore opengl defaults
        glDisable(GL_BLEND)
        glColor4f(0.0, 0.0, 0.0, 1.0)

        if cls._is_snap:
            cls._draw_snap(cls._vertices[0])

    @staticmethod
    def _draw_snap(vertex):

        glEnable(GL_BLEND)

        glColor4f(1.0, 0.5, 0.0, 0.5)
        glPointSize(10)

        glBegin(GL_POINTS)
        glVertex2i(int(vertex[0]), int(vertex[1]))
        glEnd()

        # restore opengl defaults
        glPointSize(1)
        glDisable(GL_BLEND)
        glColor4f(0.0, 0.0, 0.0, 1.0)


def register():
    bpy.utils.register_class(VIEW3D_OT_ImageCrop)


def unregister():
    bpy.utils.unregister_class(VIEW3D_OT_ImageCrop)


if __name__ == "__main__":
    register()
