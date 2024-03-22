import bpy


class CurveTextImport(bpy.types.Operator):
    """Test importer that creates a text object from a .txt file"""

    bl_idname = "curve.text_import"
    bl_label = "Import a text file as text object"

    """
    This Operator supports import one .txt file at the time, we need the
    following filepath property that the file handler will use to set file path data.
    """
    filepath: bpy.props.StringProperty(subtype="FILE_PATH", options={"SKIP_SAVE"})

    @classmethod
    def poll(cls, context):
        return context.area and context.area.type == "VIEW_3D"

    def execute(self, context):
        """Calls to this Operator can set unfiltered filepaths, ensure the file extension is .txt."""
        if not self.filepath or not self.filepath.endswith(".txt"):
            return {"CANCELLED"}

        with open(self.filepath) as file:
            text_curve = bpy.data.curves.new(type="FONT", name="Text")
            text_curve.body = "".join(file.readlines())
            text_object = bpy.data.objects.new(name="Text", object_data=text_curve)
            bpy.context.scene.collection.objects.link(text_object)
        return {"FINISHED"}

    """
    By default the file handler invokes the operator with the filepath property set.
    In this example if this property is set the operator is executed, if not the
    file select window is invoked.
    This depends on setting ``options={'SKIP_SAVE'}`` to the property options to avoid
    to reuse filepath data between operator calls.
    """

    def invoke(self, context, event):
        if self.filepath:
            return self.execute(context)
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}


class CURVE_FH_text_import(bpy.types.FileHandler):
    bl_idname = "CURVE_FH_text_import"
    bl_label = "File handler for curve text object import"
    bl_import_operator = "curve.text_import"
    bl_file_extensions = ".txt"

    @classmethod
    def poll_drop(cls, context):
        return context.area and context.area.type == "VIEW_3D"


bpy.utils.register_class(CurveTextImport)
bpy.utils.register_class(CURVE_FH_text_import)
