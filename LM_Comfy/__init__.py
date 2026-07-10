# LM_Comfy — Blender add-on
# Adds an "LM_Comfy" tab in the View3D sidebar (N) with a one-click
# "Import Latest GLB" button that pulls the newest .glb from the ComfyUI output.
# (Rebranded from the original "Trellis" startup script.)

import bpy
import os
import mathutils
from bpy.props import StringProperty, BoolProperty

bl_info = {
    "name": "LM_Comfy",
    "author": "Ben Veasey",
    "version": (1, 0, 0),
    "blender": (4, 2, 0),
    "location": "View3D > Sidebar (N) > LM_Comfy",
    "description": "One-click import of the latest .glb from the ComfyUI output folder",
    "category": "Import-Export",
}

DEFAULT_DIR = ""  # set your ComfyUI output folder in the panel
IMPORT_COLLECTION = "LM_Comfy_Imports"


def _latest_glb(folder):
    if not folder or not os.path.isdir(folder):
        return None
    files = [os.path.join(folder, f) for f in os.listdir(folder)
             if f.lower().endswith(".glb")]
    return max(files, key=os.path.getmtime) if files else None


class LM_COMFY_OT_import_latest(bpy.types.Operator):
    bl_idname = "lm_comfy.import_latest_glb"
    bl_label = "Import Latest LM_Comfy GLB"
    bl_description = "Import the most recent .glb from the ComfyUI output folder into the LM_Comfy_Imports collection"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        scn = context.scene
        folder = scn.lm_comfy_glb_dir or DEFAULT_DIR
        path = _latest_glb(folder)
        if not path:
            self.report({'ERROR'}, f"No .glb found in {folder}")
            return {'CANCELLED'}

        coll = bpy.data.collections.get(IMPORT_COLLECTION)
        if coll is None:
            coll = bpy.data.collections.new(IMPORT_COLLECTION)
            context.scene.collection.children.link(coll)
        lc = context.view_layer.layer_collection.children.get(IMPORT_COLLECTION)
        if lc:
            context.view_layer.active_layer_collection = lc

        before = {o.name for o in bpy.data.objects}
        bpy.ops.import_scene.gltf(filepath=path)
        new_objs = [o for o in bpy.data.objects if o.name not in before]

        roots = [o for o in new_objs if (o.parent is None or o.parent.name in before)]
        roots = roots or new_objs

        if scn.lm_comfy_place_at_cursor and roots:
            med = sum((o.matrix_world.translation for o in roots),
                      mathutils.Vector()) / len(roots)
            offset = context.scene.cursor.location - med
            for o in roots:
                o.location = o.location + offset

        bpy.ops.object.select_all(action='DESELECT')
        for o in new_objs:
            o.select_set(True)
        if new_objs:
            context.view_layer.objects.active = new_objs[0]

        self.report({'INFO'}, f"Imported {os.path.basename(path)} ({len(new_objs)} objects)")
        return {'FINISHED'}


class LM_COMFY_PT_panel(bpy.types.Panel):
    bl_label = "LM_Comfy Import"
    bl_idname = "LM_COMFY_PT_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Comfy"

    def draw(self, context):
        layout = self.layout
        scn = context.scene
        folder = scn.lm_comfy_glb_dir or DEFAULT_DIR
        latest = _latest_glb(folder)

        col = layout.column(align=True)
        col.scale_y = 1.25
        col.enabled = latest is not None
        col.operator("lm_comfy.import_latest_glb", text="Import Latest GLB", icon='IMPORT')

        if latest:
            layout.label(text="Latest: " + os.path.basename(latest), icon='FILE_3D')
        elif not folder:
            layout.label(text="Set the ComfyUI output folder below", icon='INFO')
        else:
            layout.label(text="No .glb in the folder yet", icon='INFO')

        header, body = layout.panel("lm_comfy_settings", default_closed=False)
        header.label(text="Settings", icon='PREFERENCES')
        if body is None:
            return
        body.prop(scn, "lm_comfy_glb_dir", text="Folder")
        body.prop(scn, "lm_comfy_place_at_cursor", toggle=True, icon='PIVOT_CURSOR')


_classes = (LM_COMFY_OT_import_latest, LM_COMFY_PT_panel)


def register():
    if not hasattr(bpy.types.Scene, "lm_comfy_glb_dir"):
        bpy.types.Scene.lm_comfy_glb_dir = StringProperty(
            name="GLB Folder", subtype='DIR_PATH', default=DEFAULT_DIR)
    if not hasattr(bpy.types.Scene, "lm_comfy_place_at_cursor"):
        bpy.types.Scene.lm_comfy_place_at_cursor = BoolProperty(
            name="Place at 3D Cursor", default=True)
    for c in _classes:
        try:
            bpy.utils.register_class(c)
        except Exception:
            pass


def unregister():
    for c in reversed(_classes):
        try:
            bpy.utils.unregister_class(c)
        except Exception:
            pass
    for prop in ("lm_comfy_glb_dir", "lm_comfy_place_at_cursor"):
        if hasattr(bpy.types.Scene, prop):
            delattr(bpy.types.Scene, prop)


if __name__ == "__main__":
    register()
