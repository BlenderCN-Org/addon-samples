import bpy
from bgl import *

class VIEW3D_OT_OffScreenDraw(bpy.types.Operator):
    """"""
    bl_idname = "view3d.offscreen_draw"
    bl_label = "Offscreen Draw"

    _handle_calc = None
    _handle_draw = None
    is_enabled = False

    @classmethod
    def poll(cls, context):
        return context.area.type == 'VIEW_3D'

    @staticmethod
    def handle_add(self, context):
        VIEW3D_OT_OffScreenDraw._handle_draw = bpy.types.SpaceView3D.draw_handler_add(
            self.draw_callback_px, (context, ), 'WINDOW', 'POST_PIXEL')

    @staticmethod
    def handle_remove():
        if VIEW3D_OT_OffScreenDraw._handle_draw is not None:
            bpy.types.SpaceView3D.draw_handler_remove(VIEW3D_OT_OffScreenDraw._handle_draw, 'WINDOW')

        VIEW3D_OT_OffScreenDraw._handle_draw = None

    def modal(self, context, event):
        if context.area:
            context.area.tag_redraw()

        return {'PASS_THROUGH'}

    def invoke(self, context, event):
        if VIEW3D_OT_OffScreenDraw.is_enabled:
            VIEW3D_OT_OffScreenDraw.handle_remove()
            VIEW3D_OT_OffScreenDraw.is_enabled = False

            if context.area:
                context.area.tag_redraw()

            return {'FINISHED'}

        else:
            if not self.init(context):
                self.report({'ERROR'}, "Error initializing offscreen buffer. More details in the console")
                return {'CANCELLED'}

            VIEW3D_OT_OffScreenDraw.handle_add(self, context)
            VIEW3D_OT_OffScreenDraw.is_enabled = True

            if context.area:
                context.area.tag_redraw()

            context.window_manager.modal_handler_add(self)
            return {'RUNNING_MODAL'}

    def init(self, context):
        import gpu
        scene = context.scene
        aspect_ratio = scene.render.resolution_x / scene.render.resolution_y

        try:
            self._offscreen = gpu.offscreen.new(512, int(512 / aspect_ratio), 0)
            self._texture = self._offscreen.color_texture

        except Exception as E:
            print(E)
            return False

        if not self._offscreen:
            return False

        return True

    def draw_callback_px(self, context):
        scene = context.scene
        aspect_ratio = scene.render.resolution_x / scene.render.resolution_y

        self._update_offscreen(context, self._offscreen)
        self._opengl_draw(context, self._texture, aspect_ratio, 0.2)

    def _update_offscreen(self, context, offscreen):
        scene = context.scene
        camera = scene.camera

        modelview_matrix = camera.matrix_world.inverted()
        projection_matrix = camera.calc_matrix_camera()

        offscreen.draw_view3d(
                scene,
                context.space_data,
                context.region,
                projection_matrix,
                modelview_matrix)

    def _opengl_draw(self, context, texture, aspect_ratio, scale):
        """
        OpenGL code to draw a rectangle in the viewport
        """
        glDisable(GL_DEPTH_TEST)

        # view setup
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()

        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()

        glOrtho(-1, 1, -1, 1, -15, 15)
        gluLookAt(0.0, 0.0, 1.0, 0.0,0.0,0.0, 0.0,1.0,0.0)

        act_tex = Buffer(GL_INT, 1)
        glGetIntegerv(GL_TEXTURE_2D, act_tex)

        viewport = Buffer(GL_INT, 4)
        glGetIntegerv(GL_VIEWPORT, viewport)

        width = int(scale * viewport[2])
        height = int(width / aspect_ratio)

        glViewport(viewport[0], viewport[1], width, height)
        glScissor(viewport[0], viewport[1], width, height)

        # draw routine
        glEnable(GL_TEXTURE_2D)
        glActiveTexture(GL_TEXTURE0)

        glBindTexture(GL_TEXTURE_2D, texture)

        texco = [(1, 1), (0, 1), (0, 0), (1,0)]
        verco = [(1.0, 1.0), (-1.0, 1.0), (-1.0, -1.0), (1.0, -1.0)]

        glPolygonMode(GL_FRONT_AND_BACK , GL_FILL)

        glColor4f(1.0, 1.0, 1.0, 1.0)

        glBegin(GL_QUADS)
        for i in range(4):
            glTexCoord3f(texco[i][0], texco[i][1], 0.0)
            glVertex2f(verco[i][0], verco[i][1])
        glEnd()

        # restoring settings
        glBindTexture(GL_TEXTURE_2D, act_tex[0])

        glDisable(GL_TEXTURE_2D)

        # reset view
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()

        glMatrixMode(GL_MODELVIEW)
        glPopMatrix()

        glViewport(viewport[0], viewport[1], viewport[2], viewport[3])
        glScissor(viewport[0], viewport[1], viewport[2], viewport[3])


def register():
    bpy.utils.register_class(VIEW3D_OT_OffScreenDraw)


def unregister():
    bpy.utils.unregister_class(VIEW3D_OT_OffScreenDraw)


if __name__ == "__main__":
    register()
