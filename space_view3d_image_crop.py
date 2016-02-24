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

class VIEW3D_OT_ImageCrop(bpy.types.Operator):
    """"""
    bl_idname = "view3d.image_crop"
    bl_label = "Image Crop"

    _handle_draw = None
    _vertices = [None, None]

    @classmethod
    def poll(cls, context):
        return True

    @classmethod
    def _handle_add(cls):
        cls._handle_draw = bpy.types.SpaceView3D.draw_handler_add(
            cls._draw_callback_px, tuple(), 'WINDOW', 'POST_PIXEL')

    @classmethod
    def _handle_remove(cls):
        if cls._handle_draw is not None:
            bpy.types.SpaceView3D.draw_handler_remove(cls._handle_draw, 'WINDOW')

        cls._handle_draw = None

    def _click(self, context, event):
        # manage clicks
        return

    def modal(self, context, event):
        if not context.area or not context.region or event.type == 'NONE':
            context.area.tag_redraw()
            return {'PASS_THROUGH'}

        elif event.type == 'LEFTMOUSE':
            self._click(context, event)
            return {'RUNNING_MODAL'}

        elif event.type in {'RIGHTMOUSE', 'ESC'}:
            self.cancel(context)
            return {'CANCELLED'}

        if context.area: # not available if other window-type is fullscreen
            context.area.tag_redraw()

        return {'RUNNING_MODAL'}

    def cancel(self, context):
        VIEW3D_OT_ImageCrop.reset()

    @classmethod
    def reset(cls):
        cls._handle_remove()
        cls._handle_draw = None
        cls._vertices = [None, None]

    def invoke(self, context, event):
        VIEW3D_OT_ImageCrop.reset()

        if context.area.type == 'VIEW_3D':
            self.perspective = context.region_data.perspective_matrix

            VIEW3D_OT_ImageCrop._handle_add()

            if context.area:
                context.area.tag_redraw()

            context.window_manager.modal_handler_add(self)
            return {'RUNNING_MODAL'}

        else:
            self.report({'WARNING'}, "View3D not found, cannot run operator")
            return {'CANCELLED'}

    @classmethod
    def _draw_callback_px(cls):
        return
        # if no vertices:
        # draw a snap vertice

        # if one vertice:
        # * draw 2nd snap vertice
        # * draw hash pattern on top of image


def register():
    bpy.utils.register_class(VIEW3D_OT_ImageCrop)


def unregister():
    bpy.utils.unregister_class(VIEW3D_OT_ImageCrop)


if __name__ == "__main__":
    register()
